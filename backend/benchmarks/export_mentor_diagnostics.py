"""Read saved mentor rejection details without running a model or changing memory."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

from backend.app.database import DATABASE_PATH


def pick(source, names):
    return {name: source[name] for name in names if name in source}


def decision(source):
    if not isinstance(source, dict):
        return None
    action = source.get('next_action')
    return {'evidence_ids': source.get('evidence_ids', []),
            'next_action': pick(action, ('kind', 'code', 'columns', 'focus_column', 'evidence_ids'))
            if isinstance(action, dict) else None}


def summarize(state):
    validation = state.get('last_validation') or {}
    report = pick(state, ('schema_version', 'focus_column', 'response_language',
                          'current_evidence_ids', 'available_columns', 'definition_availability',
                          'pending_evidence_refresh'))
    report['observations'] = [pick(item, (
        'id', 'cell_id', 'section_title', 'code', 'fields', 'success', 'analysis_contract',
        'input_rows', 'dataset_kind', 'input_data_version', 'version_verified',
        'stale_scope', 'executed_at',
    )) for item in state.get('observations', [])]
    report['proposals'] = [pick(item, ('kind', 'code', 'focus_column', 'columns',
                                     'evidence_ids', 'status')) for item in state.get('proposals', [])]
    report['last_validation'] = pick(validation, (
        'accepted', 'status', 'origin', 'policy', 'errors', 'previous_attempt_errors',
        'attempts', 'provider_calls', 'rendering_contract', 'model_factual_prose_published',
        'validation_kind', 'refresh_action',
    ))
    report['last_validation']['model_attempts'] = [
        {**pick(item, ('attempt', 'errors', 'evidence_binding')),
         'raw_plan': decision(item.get('raw_plan')),
         'compiled_proposal': decision(item.get('proposal'))}
        for item in validation.get('model_attempts', [])
    ]
    flow = state.get('workflow') or {}
    if flow:
        report['workflow'] = pick(flow, ('schema_version', 'focus_column', 'question', 'phase', 'status'))
        report['workflow']['active_step'] = pick(flow.get('active_step') or {}, (
            'id', 'kind', 'status', 'code', 'cell_id', 'signature', 'expected_version',
            'completion_evidence_id', 'help_requests', 'assistance_level', 'blocker',
        ))
        report['workflow']['step_history'] = [pick(item, ('id', 'kind', 'status', 'completion_evidence_id'))
                                               for item in flow.get('step_history', [])]
        report['workflow']['finding_ids'] = [item['id'] for item in flow.get('findings', [])]
    # Local decisions have no model attempt, so retain their actual selected code too.
    for key in ('local_plan', 'local_proposal', 'supported_proposal'):
        if key in validation:
            report['last_validation'][key] = decision(validation[key])
    return report


def read_diagnostics(database_path: Path, *, focus=None):
    path = database_path.resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as connection:
        connection.execute('PRAGMA query_only = ON')
        try:
            rows = connection.execute(
                'SELECT workspace_id, notebook_id, state_json FROM mentor_research_memory '
                'ORDER BY workspace_id, notebook_id'
            ).fetchall()
        except sqlite3.OperationalError as exc:
            if 'no such table' not in str(exc):
                raise
            rows = []
    records = []
    for workspace_id, notebook_id, serialized in rows:
        state = json.loads(serialized)
        if focus and str(state.get('focus_column', '')).casefold() != focus.casefold():
            continue
        records.append({'workspace_id': workspace_id, 'notebook_id': notebook_id,
                        **summarize(state)})
    return {
        'mode': 'saved_mentor_diagnostics', 'provider_calls': 0,
        'memory_modified': False, 'records': records,
        'scope': 'Last saved validation per matching notebook, not a replay or a new acceptance test.',
        'omitted': ['chat history', 'preview rows', 'raw output text', 'runtime credentials',
                    'provider response bodies', 'model factual prose'],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=DATABASE_PATH)
    parser.add_argument('--focus', help='Only notebooks with this active target column')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        report = read_diagnostics(args.database, focus=args.focus)
    except (OSError, sqlite3.Error, ValueError) as exc:
        parser.exit(1, f'Diagnostics could not be read: {type(exc).__name__}: {exc}\n')
    if not report['records']:
        parser.exit(1, 'No saved notebook mentor record matches. No model was called.\n')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    output = args.output or Path('backend/benchmarks/results/mentor-diagnostics') / stamp / 'report.json'
    if output.resolve() == args.database.resolve():
        parser.exit(1, 'The report must not overwrite the database.\n')
    output.parent.mkdir(parents=True, exist_ok=True)
    # A new path preserves previous reports and prevents accidental overwrites.
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    for record in report['records']:
        validation = record['last_validation']
        print(f"{record['focus_column']}: accepted={validation.get('accepted')}; "
              f"errors={validation.get('errors', [])}")
    print(f'REPORT: {output.resolve()}')
    print('Saved records only. No AI request or notebook execution.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
