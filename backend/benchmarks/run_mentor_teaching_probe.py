"""Two bounded live teaching calls on invented data, then a local code check.

No user project is touched. Mechanical passage does not prove novice learning.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

from dotenv import load_dotenv

import pandas as pd

from backend.app import database
from backend.app.mentor_relationship_service import build_relationship_map
from backend.app.mentor_research_service import generate_research_reply
from backend.app.mentor_research_store import load_research_state
from backend.benchmarks.run_mentor_connected_followup import recorded_cell


def synthetic_context(*, public=False, shared=False):
    frame = pd.DataFrame({
        'delivery_days': [None if i % 4 == 0 else i % 8 for i in range(1000)],
        'shipment_status': ['pending' if i % 4 == 0 else 'delivered' for i in range(1000)],
    })
    cell = recorded_cell('count', "df['delivery_days'].isna().sum()", 250,
                         'delivery_days', 'teaching-synthetic-v1', 1000)
    return {'workspace_id': 'synthetic-teaching-only', 'ui_context': {'language': 'tr'},
        'mentor_setup': {'experience_level': 'beginner', **({'notebook_teaching_context': 'question_and_code'} if shared else {})},
        'teaching_data_policy': {'usage_context': 'personal', 'data_sensitivity': 'public' if public else None},
        'dataset_profile_summary': {'columns': list(frame.columns)},
        'local_relationship_map': build_relationship_map(frame, input_version='teaching-synthetic-v1'),
        'artifacts': {'selected_notebook': {'notebook_id': 'n1', 'dataset_kind': 'working',
            'configured_development_rows': 1000, 'current_input_version': 'teaching-synthetic-v1',
            'latest_cell': cell, 'recent_cells': [cell]}}}


def run_probe(*, public=False, shared=False):
    context = synthetic_context(public=public, shared=shared)
    generate_research_reply(context,
        'delivery_days sayımını yaptım. Kaynak açıklaması elimde yok. Sonraki tek adımı söyle.', [], allow_provider=False)
    before = load_research_state(context['workspace_id'], 'n1')
    task = deepcopy(before['workflow']['active_step'])
    turns, history = [], []
    for index, message in enumerate((
        'Önce neyi seçmeliyim? Kodu verme.',
        'Tam anlamadım. Ben yalnız eksikleri saydım, satır seçmedim. Daha basit anlat; kodu verme.',
        'Kodu göster.',
    )):
        reply = generate_research_reply(context, message, history, allow_provider=index < 2)
        after = load_research_state(context['workspace_id'], 'n1')
        trace = after['last_validation']
        turns.append({'message': message, 'reply': reply, 'diagnostics': trace,
            'same_pending_task': after['workflow']['active_step']['id'] == task['id']
                and after['workflow']['active_step']['status'] == 'awaiting_execution'
                and after['proposals'] == before['proposals']})
        history += [{'role': 'user', 'content': message}, {'role': 'assistant', 'content': reply}]
        if index < 2 and not trace.get('teaching_accepted'):
            break
    passed = (len(turns) == 3 and all(x['same_pending_task'] for x in turns)
              and all(x['diagnostics'].get('teaching_accepted') for x in turns[:2]))
    if passed:
        passed = all('```' not in x['reply'] for x in turns[:2]) and '```python\n' + task['code'] + '\n```' in turns[2]['reply']
    return {'synthetic_data_only': True, 'turns': turns, 'mechanical_checks_passed': passed,
        'novice_usability_accepted': False, 'project_completion_proven': False, 'human_review_required': True,
        'review_questions': [
            'Does it distinguish counting missing cells from selecting rows?',
            'Does the second explanation address the difficulty differently?',
            'Is the first action small enough to attempt without knowing the full expression?',
            'Are normalized values described as proportions rather than raw counts?',
            'Does it avoid inventing results or claiming the learner already filtered rows?']}



DIALOGUE_CASES = {
    'orders': ('duration', 'fulfillment_state'),
    'sensors': ('reading', 'sensor_mode'),
    'service': ('resolution_time', 'ticket_state'),
}


def dialogue_context(case):
    """Invented inputs with exceptions; a correlation must not become a rule."""
    target, helper = DIALOGUE_CASES[case]
    frame = pd.DataFrame({target: [None if i % 4 == 0 else i % 8 for i in range(1000)],
        helper: ['open' if i % 4 == 0 and i % 40 != 0 else 'closed' for i in range(1000)]})
    context = synthetic_context(public=True)
    context.update(workspace_id='synthetic-dialogue-' + case,
        task_brief='Investigate incomplete records, check exceptions and document a justified decision.',
        mentor_setup={'experience_level': 'beginner', 'approach': 'guided', 'learning_focus': ['python', 'quality'], 'notebook_teaching_context': 'question_code_and_summaries'},
        ui_context={'language': 'tr', 'active_workspace_stage': 'prepare',
            'active_prepare_stage': 'workbench', 'workbench_view': 'notebook'})
    context['dataset_profile_summary']['columns'] = list(frame.columns)
    context['local_relationship_map'] = build_relationship_map(frame, input_version='dialogue-v1')
    count = recorded_cell('count', f'df[{target!r}].isna().sum()', int(frame[target].isna().sum()), target, 'dialogue-v1', 1000)
    context['artifacts']['selected_notebook'].update(current_input_version='dialogue-v1', latest_cell=count, recent_cells=[count])
    return context, frame, target, helper


def run_dialogue_suite(case, *, delay=45, checkpoint=None):
    """Freeze learner turns and receipts, not model answers. At most six calls.

    This is an API conversation probe, not an autonomous novice UI test. Model
    code is never executed. Only a known normalized distribution is computed
    directly from the synthetic frame to provide a fixed execution receipt.
    Persist after every turn; interruption retains completed observations.
    """
    import time
    context, frame, target, helper = dialogue_context(case)
    notebook = context['artifacts']['selected_notebook']
    generate_research_reply(context, f'{target} eksiklerini saydım. Kaynak açıklamam yok. Sonraki adım?', [], allow_provider=False)
    state = load_research_state(context['workspace_id'], 'n1')
    initial = deepcopy(state['workflow']['active_step'])
    if not initial or initial['kind'] != 'inspect':
        raise ValueError('The frozen dialogue requires a pending inspection')
    history, turns = [], []
    report = {'case': case, 'synthetic_data_only': True, 'fixed_learner_scenario': True,
        'ui_tested': False, 'novice_usability_accepted': False, 'project_completion_proven': False,
        'human_review_required': True, 'status': 'running', 'turns': turns,
        'review_questions': [
            'Does each answer address the current question rather than recap the distribution task?',
            'Does mask help explain keeping True rows and excluding False rows without claiming execution?',
            'Does the tutor change explanation when the learner remains confused?',
            'Does it acknowledge partial/failed attempts without inventing correctness or error causes?',
            'After execution, does it use actual evidence and retain exceptions as unresolved?',
            'Are source definitions and treatment decisions kept separate from statistical patterns?']}
    deadline = 0.0
    def pace():
        nonlocal deadline
        remaining = max(0, deadline - time.monotonic())
        if remaining:
            print(f'Provider pacing: {remaining:.0f}s', flush=True)
        while time.monotonic() < deadline:
            time.sleep(min(0.5, deadline - time.monotonic()))
        deadline = time.monotonic() + max(0, delay)
    def persist():
        if checkpoint:
            checkpoint(report)
    questions = [
        ('count_vs_filter', 'Eksikleri saymak ile eksik satırları seçmek arasındaki farkı anlamadım. Kodu vermeden tek küçük adımı anlat.'),
        ('mask', 'Bu True/False işaretlerini satır seçmek için nasıl kullanacağım? Yalnızca bunu açıkla, kod verme.'),
        ('partial', 'Koşulu yazdım; bu satırları seçtiğim anlamına geliyor mu? Eksik kalan kısmı kod vermeden anlat.'),
        ('error', 'Son denemem hata verdi. Nerede takıldığımı anlayabiliyor musun? Bilmiyorsan hata nedenini uydurma.'),
        ('evidence', 'Yeni çalıştırdığım kontrol neyi gösteriyor? Önce sonucu açıkla, yeni işlem yaptığımı varsayma.'),
        ('definition_unavailable', 'Kaynak tanımını bilmiyorum. Bu bulgudan kesin kural çıkarabilir miyiz? Kısa açıkla, kod verme.'),
    ]
    try:
        for index, (name, message) in enumerate(questions):
            if name == 'partial':
                cell = recorded_cell('condition', f'df[{target!r}].isna()', str(frame[target].isna()), target, 'dialogue-v1', 1000)
                notebook.update(latest_cell=cell, recent_cells=[cell] + notebook['recent_cells'])
            if name == 'error':
                cell = recorded_cell('failed', f'df[{target!r}].isna(', 'SyntaxError', target, 'dialogue-v1', 1000)
                cell['last_execution']['success'] = False
                notebook.update(latest_cell=cell, recent_cells=[cell] + notebook['recent_cells'])
            if name == 'evidence':
                from backend.app.mentor_observation_contract import expression_contract
                contract = expression_contract(initial['code'])
                if (contract.get('operation') != 'distribution' or
                    contract.get('row_predicate') != {'op': 'missing', 'column': target} or
                    contract.get('measured_columns') != [helper] or not contract.get('options', {}).get('normalize')):
                    raise ValueError('Pending inspection is outside the frozen synthetic receipt contract')
                result = frame.loc[frame[target].isna(), helper].value_counts(normalize=True, dropna=False)
                cell = recorded_cell('distribution', initial['code'], result, target, 'dialogue-v1', 1000)
                notebook.update(latest_cell=cell, recent_cells=[cell] + notebook['recent_cells'])
                # Reconcile the actual receipt and let the existing local planner
                # register the complementary comparison, without provider use.
                generate_research_reply(context, 'Kontrolü çalıştırdım; sonraki adım?', history, allow_provider=False)
            reply = generate_research_reply(context, message, history, max_attempts=1, request_pacer=pace)
            state = load_research_state(context['workspace_id'], 'n1')
            trace = deepcopy(state['last_validation'])
            journal = state.get('teaching_journal') or []
            rejected = state.get('last_rejected_teaching') or {}
            candidate = ((state.get('last_teaching_attempt') or {}).get('provider_candidate') if trace.get('teaching_accepted') and journal
                else rejected.get('candidate') if rejected.get('reason') == trace.get('reason') else None)
            turns.append({'case': name, 'message': message, 'displayed_reply': reply,
                'provider_candidate': candidate, 'diagnostics': trace,
                'pending_task': {k: (state.get('workflow', {}).get('active_step') or {}).get(k)
                                 for k in ('id', 'kind', 'status')},
                'provider_calls': trace.get('provider_calls', len(trace.get('model_attempts') or []))})
            history += [{'role': 'user', 'content': message}, {'role': 'assistant', 'content': reply}]
            persist()
            if not trace.get('teaching_accepted'):
                break
        checks = {
            'six_turns_completed': len(turns) == 6,
            'responses_protocol_valid': all(x['diagnostics'].get('teaching_accepted') for x in turns),
            'initial_task_retained_before_receipt': all(x['pending_task'].get('id') == initial['id']
                and x['pending_task'].get('status') == 'awaiting_execution' for x in turns[:4]),
            'task_advanced_after_receipt': len(turns) >= 5 and turns[4]['pending_task'].get('id') != initial['id'],
            'result_question_uses_evidence': len(turns) >= 5 and turns[4]['diagnostics'].get('conversation_kind') == 'evidence',
            'no_unrequested_code': all('```' not in x['displayed_reply'] for x in turns),
            'bounded_provider_calls': sum(x['provider_calls'] for x in turns) <= 6,
        }
        report['protocol_checks'] = checks
        report['protocol_checks_passed'] = all(checks.values())
        report['status'] = ('completed_requires_human_review' if report['protocol_checks_passed']
                            else 'completed_with_protocol_failures')
    except KeyboardInterrupt:
        report['status'] = 'interrupted'
        persist()
        raise
    except Exception:
        report['status'] = 'blocked'
        persist()
        raise
    persist()
    return report

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', required=True, help='Allow configured provider calls: two in the short probe, at most six in the dialogue suite.')
    parser.add_argument('--dialogue-suite', action='store_true', help='Frozen six-turn synthetic conversation; at most six provider calls.')
    parser.add_argument('--case', choices=tuple(DIALOGUE_CASES), default='orders')
    parser.add_argument('--delay', type=float, default=45, help='Minimum seconds between requests in dialogue suite.')
    parser.add_argument('--public-synthetic', action='store_true')
    parser.add_argument('--question-and-code', action='store_true', help='Exercise explicit scoped sharing on an unclassified personal project.')
    parser.add_argument('--output-dir', type=Path, default=Path('backend/benchmarks/results/teaching-probe'))
    args = parser.parse_args(argv)
    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)
    folder = args.output_dir / datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True, exist_ok=False)
    previous = database.DATABASE_PATH
    try:
        database.DATABASE_PATH = folder / 'isolated.sqlite'
        database.init_db()
        path = folder / 'report.json'
        def checkpoint(report):
            path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        report = (run_dialogue_suite(args.case, delay=args.delay, checkpoint=checkpoint) if args.dialogue_suite
                  else run_probe(public=args.public_synthetic, shared=args.question_and_code))
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    finally:
        database.DATABASE_PATH = previous
    print('REPORT:', path.resolve())
    for turn in report['turns']:
        print('LEARNER:', turn['message'])
        print('MENTOR:', turn.get('displayed_reply', turn.get('reply')))
        print('TEACHING:', turn['diagnostics'].get('teaching_accepted'), turn['diagnostics'].get('reason', ''))
    print('Mechanical checks:', report.get('mechanical_checks_passed', 'Human review required'))
    print('Novice learning and project completion are unproven. Human review required.')
    return 0 if report.get('mechanical_checks_passed') or report.get('status') == 'completed_requires_human_review' else 1


if __name__ == '__main__':
    raise SystemExit(main())
