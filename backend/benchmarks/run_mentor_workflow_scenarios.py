"""Scripted system checks from an empty notebook to a documented deferral.

The driver only executes code that the mentor actually displays after an
explicit code request. This does not measure human learning or live AI quality.
No model output is stubbed: these scenarios must use provider-disabled local
production paths. Execution is a small AST-contract interpreter, never eval.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from backend.app import database
from backend.app.mentor_observation_contract import expression_contract
from backend.app.mentor_research_service import generate_research_reply
from backend.app.mentor_research_store import load_research_state
from backend.benchmarks.run_mentor_connected_followup import recorded_cell


CASES = [('temperature', 'offline'), ('delivery_days', 'returned'), ('response_seconds', 'closed')]


def execute_displayed(frame, reply, target):
    marker = '```python\n'
    if marker not in reply or reply.count(marker) != 1:
        raise ValueError('The learner was not shown exactly one Python example')
    code = reply.split(marker, 1)[1].split('```', 1)[0].strip()
    contract = expression_contract(code)
    if contract.get('supported') is False or len(frame) > 10000:
        raise ValueError('Unsupported displayed expression')
    columns = contract.get('measured_columns')
    where = contract['row_predicate']
    if (contract['operation'] == 'missing_count' and columns == [target]
            and where == {'op': 'all_current_df'}):
        return code, int(frame[target].isna().sum())
    if where != {'op': 'missing', 'column': target}:
        raise ValueError('Only the known missing-target inspection is interpreted')
    selected = frame.loc[frame[target].isna()]
    if contract['operation'] == 'preview_head' and contract['options'].get('limit') == 5:
        if columns is not None:
            selected = selected[columns]
        return code, selected.head(5).copy()
    if (contract['operation'] == 'distribution' and columns and len(columns) == 1
            and contract['options'] == {'dropna': False}):
        return code, selected[columns[0]].value_counts(dropna=False)
    raise ValueError('Displayed expression is outside the scenario interpreter')


def run_scenario(target, helper):
    frame = pd.DataFrame({**{f'feature_{i}': range(1000) for i in range(29)},
                          target: [None if i % 2 == 0 else i for i in range(1000)],
                          helper: [i % 3 == 0 for i in range(1000)]})
    original = frame.copy(deep=True)
    version = target + '-synthetic-v1'
    notebook = {'notebook_id': 'n1', 'dataset_kind': 'working', 'configured_development_rows': len(frame),
                'current_input_version': version, 'latest_cell': None, 'recent_cells': [],
                'available_columns': list(frame.columns)}
    context = {'workspace_id': 'workflow-' + target, 'task_brief': 'Investigate missingness before treating it.',
               'learner_skills': [{'skill_name': 'null_analysis', 'status': 'new'}],
               'ui_context': {'language': 'tr'}, 'dataset_profile_summary': {'columns': list(frame.columns)},
               'artifacts': {'selected_notebook': notebook}}
    turns, history = [], []
    checks = {'no_duplicate_pending_step': True, 'help_preserves_step': True,
              'code_requires_explicit_request': True, 'new_output_completes_step': True}

    def ask(message):
        reply = generate_research_reply(context, message, history, allow_provider=False)
        state = load_research_state(context['workspace_id'], 'n1')
        turns.append({'message': message, 'reply': reply, 'validation': state.get('last_validation'),
                      'workflow': state.get('workflow')})
        history.extend([{'role': 'user', 'content': message}, {'role': 'assistant', 'content': reply}])
        return reply, state

    _, state = ask(f'{target} eksikliğini incelemek istiyorum. Kaynak açıklaması elimde yok. Kodu verme.')
    for number in range(3):
        if not state.get('last_validation', {}).get('accepted'):
            raise ValueError('Production path could not assign the scenario step')
        step = state['workflow']['active_step']
        step_id = step['id']
        pending_count = len([p for p in state.get('proposals', []) if p.get('status') == 'proposed'])
        for message in ('Tamam şimdi ne yapacağız, nereden araştırmaya başlayacağız?',
                        'Anlamadım, beraber ilerleyelim. Kodu gösterme.'):
            reply, helped = ask(message)
            checks['help_preserves_step'] &= helped['workflow']['active_step']['id'] == step_id
            checks['code_requires_explicit_request'] &= '```' not in reply
            checks['no_duplicate_pending_step'] &= len([p for p in helped['proposals'] if p['status'] == 'proposed']) == pending_count == 1
        shown, _ = ask('Şimdi kodu göster.')
        code, result = execute_displayed(frame, shown, target)
        cell = recorded_cell(f'learner-{number}', code, result, target, version, len(frame))
        notebook['latest_cell'] = cell
        notebook['recent_cells'].insert(0, cell)
        next_message = 'Çıktıyı aldım. Sonraki tek adım ne?' if number < 2 else 'Son dağılım sonucunu açıkla. Yeni görev verme.'
        _, state = ask(next_message)
        previous = state['workflow']['step_history'] + [state['workflow']['active_step']]
        checks['new_output_completes_step'] &= any(p['id'] == step_id and p['status'] == 'observed' for p in previous)
    _, state = ask('Şimdilik değişiklik yapmadan bulguyu kaydet.')
    checks['documented_deferral'] = state['workflow']['status'] == 'documented_deferred'
    checks['finding_is_not_full_source_proof'] = all(not f['full_source_verified'] for f in state['workflow']['findings'])
    checks['data_unchanged'] = frame.equals(original)
    return {'target': target, 'columns': len(frame.columns), 'checks': checks,
            'passed': all(checks.values()), 'turns': turns}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('backend/benchmarks/results/workflow-scenarios'))
    args = parser.parse_args(argv)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    folder = args.output_dir / stamp
    folder.mkdir(parents=True, exist_ok=False)
    previous = database.DATABASE_PATH
    report = {'mode': 'scripted_system_check', 'provider_calls': 0, 'live_model_quality_tested': False,
              'beginner_usability_tested': False, 'learning_benefit_proven': False,
              'full_project_completion_proven': False, 'results': []}
    try:
        database.DATABASE_PATH = folder / 'isolated.sqlite'
        database.init_db()
        for target, helper in CASES:
            try:
                result = run_scenario(target, helper)
            except Exception as exc:
                result = {'target': target, 'passed': False, 'blocker': f'{type(exc).__name__}: {exc}'}
            report['results'].append(result)
            print(f"{target}: {'passed' if result['passed'] else 'blocked'}")
    finally:
        database.DATABASE_PATH = previous
    path = folder / 'report.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'REPORT: {path.resolve()}')
    print('Scripted system checks only; this is not novice or live-model acceptance.')
    return 0 if all(x['passed'] for x in report['results']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
