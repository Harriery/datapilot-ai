"""Run connected local Mentor steps on synthetic frames, with provider disabled.

Proposals actually feed subsequent recorded outputs. Only the bounded inspection
contract below is interpreted; no eval, generated Python execution, real project
data, UI simulation, live model quality or project completion is involved.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from backend.app import database
from backend.app.mentor_observation_contract import expression_contract
from backend.app.mentor_research_service import generate_research_reply
from backend.app.mentor_research_store import load_research_state
from backend.benchmarks.run_mentor_research_acceptance import CASES


def execute_inspection(frame: pd.DataFrame, code: str, target: str):
    """Interpret exactly two allowed read-only shapes on <=10k synthetic rows."""
    contract = expression_contract(code)
    if (len(frame) > 10000 or contract.get('supported') is False
            or contract.get('row_predicate') != {'op': 'missing', 'column': target}):
        raise ValueError('Probe only executes a missing-target inspection on a bounded synthetic frame')
    columns = contract.get('measured_columns')
    if columns is not None and (not columns or set(columns) - set(frame.columns)):
        raise ValueError('Inspection has unknown columns')
    selected = frame.loc[frame[target].isna()]
    if contract['operation'] == 'preview_head' and contract['options'].get('limit') == 5:
        return (selected if columns is None else selected[columns]).head(5).copy()
    if (contract['operation'] == 'distribution' and columns is not None and len(columns) == 1
            and contract['options'] == {'dropna': False}):
        return selected[columns[0]].value_counts(dropna=False)
    raise ValueError('Inspection shape is outside the connected probe contract')


def recorded_cell(cell_id: str, code: str, result, target: str, version: str, rows: int):
    execution = {'success': True, 'output': str(result), 'input_row_count': rows,
                 'input_total_row_count': rows, 'input_data_version': version,
                 'dataset_kind': 'working', 'executed_at': f'synthetic-{cell_id}'}
    if isinstance(result, pd.DataFrame):
        execution['preview_rows'] = json.loads(result.to_json(orient='records'))
    return {'cell_id': cell_id, 'section_title': target, 'code': code, 'last_execution': execution}


def run_case(case: str) -> dict:
    target, helper, measure, reason = CASES[case]
    frame = pd.DataFrame({target: [None if i % 2 == 0 else i for i in range(10000)],
                          helper: [i % 3 == 0 for i in range(10000)],
                          measure: [i % 41 - 20 for i in range(10000)],
                          reason: ['A' if i % 3 == 0 else None for i in range(10000)]})
    original = frame.copy(deep=True)
    version = 'connected-' + case + '-v1'
    count = int(frame[target].isna().sum())
    cells = [recorded_cell('count', f'df[{target!r}].isna().sum()', count, target, version, len(frame))]
    history, turns = [], []
    checks = {'all_turns_accepted': True, 'focus_preserved': True, 'latest_output_addressed': True,
              'preview_is_missing_target_only': False, 'distribution_matches_reference': False,
              'no_task_on_review_only': False, 'frame_unchanged': True}
    messages = [f'{target} sayımını yaptım. Veri sözlüğüm yok. Kod vermeden sonraki tek adımı söyle.',
                'Örneklerin sonucunu gördün mü? Ne anlıyoruz? Kod vermeden sonraki tek adımı söyle.',
                'Son dağılım sonucunu açıkla. Yeni görev verme.']
    for step, message in enumerate(messages):
        notebook = {'notebook_id': 'n1', 'dataset_kind': 'working', 'configured_development_rows': len(frame),
                    'current_input_version': version, 'latest_cell': cells[-1],
                    'recent_cells': list(reversed(cells)), 'available_columns': list(frame.columns)}
        context = {'workspace_id': 'connected-local-' + case,
                   'dataset_profile_summary': {'columns': list(frame.columns)},
                   'ui_context': {'language': 'tr'}, 'artifacts': {'selected_notebook': notebook}}
        reply = generate_research_reply(context, message, history, allow_provider=False)
        state = load_research_state(context['workspace_id'], 'n1')
        validation = state.get('last_validation') or {}
        proposal = validation.get('local_proposal') or {}
        action = proposal.get('next_action')
        turn = {'message': message, 'evidence_snapshot': notebook, 'reply': reply, 'validation': validation,
                'proposal_executed': False}
        turns.append(turn)
        checks['all_turns_accepted'] &= validation.get('accepted') is True
        checks['focus_preserved'] &= state.get('focus_column') == target
        checks['latest_output_addressed'] &= (state.get('current_evidence_ids') or [None])[0] in (validation.get('local_plan') or {}).get('evidence_ids', [])
        if validation.get('accepted') is not True:
            break
        if step < 2:
            if not action or action.get('kind') != 'inspect':
                checks['all_turns_accepted'] = False
                break
            # Execute the actual proposal through the narrow contract, not a
            # prewritten replacement or arbitrary Python interpreter.
            try:
                result = execute_inspection(frame, action['code'], target)
            except (ValueError, KeyError, TypeError) as exc:
                turn['execution_error'] = str(exc)
                checks['all_turns_accepted'] = False
                break
            turn['proposal_executed'] = True
            if step == 0:
                checks['preview_is_missing_target_only'] = isinstance(result, pd.DataFrame) and len(result) == min(5, count) and bool(result[target].isna().all())
            else:
                expected = frame.loc[frame[target].isna(), helper].value_counts(dropna=False)
                checks['distribution_matches_reference'] = isinstance(result, pd.Series) and result.equals(expected) and int(result.sum()) == count
            cells.append(recorded_cell('step-' + str(step), action['code'], result, target, version, len(frame)))
        else:
            checks['no_task_on_review_only'] = action is None
        history.extend([{'role': 'user', 'content': message}, {'role': 'assistant', 'content': reply}])
    checks['frame_unchanged'] = frame.equals(original)
    return {'case': case, 'mode': 'connected_local_production', 'input_rows': len(frame),
            'provider_calls': 0, 'live_model_quality_tested': False, 'beginner_usability_tested': False,
            'project_completion_proven': False, 'human_review_required': True,
            'checks': checks, 'passed': len(turns) == 3 and all(checks.values()), 'turns': turns}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['all', *CASES], default='all')
    parser.add_argument('--output-dir', type=Path, default=Path('backend/benchmarks/results/connected-followup'))
    args = parser.parse_args(argv)
    folder = args.output_dir / datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True, exist_ok=False)
    previous = database.DATABASE_PATH
    try:
        database.DATABASE_PATH = folder / 'isolated.sqlite'
        database.init_db()
        results = [run_case(case) for case in CASES if args.case in ('all', case)]
    finally:
        database.DATABASE_PATH = previous
    report = {'mode': 'connected_local_production', 'results': results, 'passed': all(x['passed'] for x in results)}
    path = folder / 'report.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    for result in results:
        print(result['case'] + ': ' + ('passed' if result['passed'] else 'blocked'))
    print('No provider calls. Synthetic data only; this is not a novice UI or live-model acceptance test.')
    print('REPORT:', path.resolve())
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
