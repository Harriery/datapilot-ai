"""Cross-domain context/fact delivery tests, not model-quality acceptance.

Controlled responses exercise the actual boundary and compiler. All inputs are
invented; no recorded user conversation or provider key is required.
"""
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.app import mentor_adaptive_teaching_service as teaching
from backend.app.mentor_investigation_service import task_key
from backend.app.mentor_research_service import generate_research_reply
from backend.benchmarks.run_mentor_teaching_probe import (
    comparison_snapshot, isolated_comparison_memory,
)


def request(case='orders', scenario='evidence'):
    context, state, question, _ = comparison_snapshot(case, scenario)
    step = state['workflow']['active_step']
    payload = teaching.build_teaching_request(context, state, step, question)
    from backend.app.mentor_investigation_service import investigation_view
    payload.update(aggregate_summaries_shared=True,
                   investigation_context=investigation_view(context, state, include_results=True))
    return context, state, step, payload


def answer(step, **changes):
    return teaching.TeachingExplanation(task_id=step['id'], approach='break_down',
        explanation=changes.pop('explanation', 'Bu gözlem tek başına eksikliğin nedenini açıklamaz.'),
        first_action=None, why=None, **changes)


def runtime():
    return patch.object(teaching, 'get_ai_runtime',
        return_value=SimpleNamespace(provider='groq', model='controlled', client=object()))


@pytest.mark.parametrize('case', ['orders', 'sensors', 'service'])
def test_failed_expression_is_available_for_learning_but_never_completes_task(case):
    context, state, step, payload = request(case, 'error')
    before = deepcopy(step)
    view = teaching.teaching_provider_view(payload)
    attempt = view['latest_attempt']
    assert 'isna' in attempt['source'] and attempt['source'].rstrip().endswith('(')
    assert attempt['diagnostic']['origin'] == 'local_parser'
    assert attempt['diagnostic']['type'] == 'SyntaxError'
    assert not attempt['success'] and not attempt['verified_result']
    assert attempt['recorded_error_type'] == 'SyntaxError'
    # The model receives descriptions, not the internal task wire schema.
    serialized = json.dumps(view)
    for key in ('row_predicate', 'measured_columns', 'task_contract', 'analysis_contract'):
        assert key not in serialized
    assert view['pending_step']['purpose'] == 'compare proportions'
    assert len(view['investigation_context']['verified_checks']) == 1
    with runtime(), patch.object(teaching, 'guarded_responses_parse',
        return_value=SimpleNamespace(output_parsed=answer(step,
            conversation_kind='attempt', explanation='Son ifadede açılan parantez kapanmamış; kapanışı kontrol et.'), status='completed')) as call:
        delivered, trace = teaching.explain_pending_task(context, state, step, 'Neden hata verdi?', allow_provider=True)
    assert delivered and trace['provider_calls'] == 1 and call.call_count == 1
    assert step == before and step['status'] == 'awaiting_execution'


def test_code_projection_redacts_literals_comments_and_raw_traceback():
    _, state, _, _ = request('sensors', 'error')
    item = next(x for x in state['observations'] if x['id'] == state['current_evidence_ids'][0])
    item.update(code="df['reading'].fillna('private-value') # private-comment\nother = 12345",
                output='Traceback: C:/private/path\nValueError: private-row-value')
    attempt = teaching.learner_attempt(state)
    wire = json.dumps(attempt)
    assert 'reading' in wire and 'fillna' in wire and attempt['redacted']
    for secret in ('private-value', 'private-comment', '12345', 'private/path', 'private-row-value'):
        assert secret not in wire
    assert attempt['recorded_error_type'] == 'ValueError'
    assert attempt['diagnostic'] is None


@pytest.mark.parametrize('code', ["df['reading'", "df['reading'].isna(\n'private", '"""private', 'f"private-{value}"'])
def test_unterminated_strings_never_leak_as_partial_source(code):
    _, state, _, _ = request('sensors', 'error')
    item = next(x for x in state['observations'] if x['id'] == state['current_evidence_ids'][0])
    item['code'] = code
    assert 'private' not in json.dumps(teaching.learner_attempt(state))


def test_truncated_source_is_not_misdiagnosed_as_a_real_syntax_error():
    _, state, _, _ = request('sensors', 'error')
    item = next(x for x in state['observations'] if x['id'] == state['current_evidence_ids'][0])
    item['code_truncated'] = True
    view = teaching.learner_attempt(state)
    assert view['source'] is None and view['diagnostic'] is None and not view['source_complete']


@pytest.mark.parametrize('case', ['orders', 'sensors', 'service'])
@pytest.mark.parametrize('kind', ['concept', 'evidence'])
def test_scoped_numeric_facts_render_regardless_of_conversation_label(case, kind):
    _, _, step, payload = request(case)
    fact = teaching.teaching_result_facts(payload)[0]
    candidate = answer(step, conversation_kind=kind, evidence_ids=[fact['evidence_id']],
        explanation=fact['marker'] + ' Bu dağılım eksikliğin nedenini tek başına kanıtlamaz.')
    delivered, trace = teaching.compile_teaching_delivery(candidate, payload, [])
    assert delivered and trace['provider_contract_accepted']
    assert trace['rendered_result_ids'] == [fact['evidence_id']]
    assert fact['text'] in delivered.explanation and '[[result:' not in delivered.explanation
    assert '1000' in delivered.explanation and 'Tam kaynak doğrulanmadı' in delivered.explanation
    assert step['status'] == 'awaiting_execution'
    exact = answer(step, evidence_ids=[fact['evidence_id']], explanation=fact['text'])
    assert teaching.compile_teaching_delivery(exact, payload, [])[0]


@pytest.mark.parametrize('mutation', ['wrong_label', 'wrong_number', 'wrong_group', 'wrong_measure'])
def test_matching_values_cannot_be_transferred_to_other_labels_groups_or_measures(mutation):
    _, _, step, payload = request('service')
    fact = teaching.teaching_result_facts(payload)[0]
    changed = fact['text']
    if mutation == 'wrong_label':
        changed = changed.replace('closed:', 'open:')
    elif mutation == 'wrong_number':
        changed = changed.replace('81.41%', '99.99%')
    elif mutation == 'wrong_group':
        changed = changed.replace('eksik', 'dolu')
    else:
        changed = changed.replace('ticket_state oranları', 'resolution_time ortalaması')
    assert changed != fact['text']
    delivered, trace = teaching.compile_teaching_delivery(answer(step,
        evidence_ids=[fact['evidence_id']], explanation=changed), payload, [])
    assert delivered is None and not trace['provider_contract_accepted']


@pytest.mark.parametrize('change', ['no_consent', 'uncited', 'unknown', 'stale', 'truncated', 'failed'])
def test_unavailable_results_never_authorize_numeric_fact_delivery(change):
    context, state, step, payload = request('orders')
    fact = teaching.teaching_result_facts(payload)[0]
    refs = [fact['evidence_id']]
    if change == 'no_consent':
        payload['aggregate_summaries_shared'] = False
    elif change == 'uncited':
        refs = []
    elif change == 'unknown':
        fact = {**fact, 'marker': '[[result:unknown]]'}
    else:
        item = next(x for x in state['observations'] if x['id'] == fact['evidence_id'])
        if change == 'stale': item['stale_scope'] = True
        elif change == 'failed': item['success'] = False
        else: item['analysis_contract']['output_truncated'] = True
        from backend.app.mentor_investigation_service import investigation_view
        payload['investigation_context'] = investigation_view(context, state, include_results=True)
    delivered, trace = teaching.compile_teaching_delivery(answer(step,
        evidence_ids=refs, explanation=fact['marker']), payload, [])
    assert delivered is None and not trace['provider_contract_accepted']


def test_revoking_summary_consent_drops_previous_fact_lesson_from_provider_history():
    context, state, step, payload = request('service')
    fact = teaching.teaching_result_facts(payload)[0]
    state['teaching_journal'] = [{
        'task_key': task_key(step), 'mode': 'user_shared_question_code_and_summaries',
        'question': 'Sonuç?', 'approach': 'contrast', 'explanation': fact['text'],
        'explanation_template': fact['marker'], 'first_action': None}]
    context['mentor_setup']['notebook_teaching_context'] = 'question_and_code'
    with runtime(), patch.object(teaching, 'guarded_responses_parse',
        return_value=SimpleNamespace(output_parsed=answer(step), status='completed')) as call:
        delivered, _ = teaching.explain_pending_task(context, state, step, 'Nasıl seçerim?', allow_provider=True)
    view = json.loads(call.call_args.kwargs['input'])
    assert delivered and view['previous_explanations'] == [] and not view['result_facts']
    assert fact['text'] not in call.call_args.kwargs['input']
    assert all('proportions' not in x for x in view['investigation_context']['verified_checks'])


def test_generic_mode_does_not_send_failed_source_diagnostics_or_real_labels():
    context, state, step, _ = request('sensors', 'error')
    context['mentor_setup']['notebook_teaching_context'] = 'generic'
    with runtime(), patch.object(teaching, 'guarded_responses_parse',
        return_value=SimpleNamespace(output_parsed=answer({**step, 'id': 'pending-task'}), status='completed')) as call:
        delivered, _ = teaching.explain_pending_task(context, state, step, 'private-question', allow_provider=True)
    wire = call.call_args.kwargs['input']
    assert delivered and 'latest_attempt' not in wire
    assert 'reading' not in wire and 'sensor_mode' not in wire and 'private-question' not in wire


def test_compiled_facts_reach_route_once_even_if_model_labels_result_as_concept():
    context, state, step, payload = request('orders')
    fact = teaching.teaching_result_facts(payload)[0]
    candidate = answer(step, conversation_kind='concept', evidence_ids=[fact['evidence_id']],
        explanation=fact['marker'] + ' Bu gözlem tek başına bir iş kuralı kanıtlamaz.')
    with isolated_comparison_memory() as memory, runtime(), patch.object(teaching, 'guarded_responses_parse',
        return_value=SimpleNamespace(output_parsed=candidate, status='completed')):
        memory[(context['workspace_id'], 'n1')] = deepcopy(state)
        visible = generate_research_reply(context, 'Bu sonuç neyi gösterir?', [])
        after = memory[(context['workspace_id'], 'n1')]
    assert visible.count(fact['text']) == 1 and '[[result:' not in visible
    assert after['workflow']['active_step']['id'] == step['id']
    assert after['workflow']['active_step']['status'] == 'awaiting_execution'
    assert after['last_validation']['teaching_accepted']
    assert not after['last_validation']['semantic_quality_verified']
