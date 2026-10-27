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
from backend.app.mentor_investigation_service import task_key, verified_observations, observation_population
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


def answer(step=None, **changes):
    return teaching.TeachingAnswer(answer=changes.get('explanation', 'Bu gözlem tek başına eksikliğin nedenini açıklamaz.'))


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
    assert view['pending_step']['purpose'] == 'describe category proportions'
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
def test_summary_context_is_typed_scoped_and_has_no_model_copying_protocol(case):
    _, _, _, payload = request(case)
    view = teaching.teaching_provider_view(payload)
    checks = view['investigation_context']['verified_checks']
    assert checks[0]['proportions'] and checks[0]['summary_complete']
    assert checks[0]['population']['dataframe_rows'] == 1000 and not checks[0]['full_source_verified']
    assert 'eksik' in checks[0]['selection']
    assert all('id' not in x and 'marker' not in x for x in checks)
    assert 'result_facts' not in view and 'task_id' not in view


def test_revoking_summary_consent_drops_previous_numeric_lesson_from_provider_history():
    context, state, step, _ = request('service')
    state['teaching_journal'] = [{
        'task_key': task_key(step), 'mode': 'user_shared_question_code_and_summaries',
        'question': 'Sonuç?', 'explanation': 'private-category yaklaşık %81.',
        'contract_version': 3}]
    context['mentor_setup']['notebook_teaching_context'] = 'question_and_code'
    with runtime(), patch.object(teaching, 'guarded_responses_parse',
        return_value=SimpleNamespace(output_parsed=answer(), status='completed')) as call:
        delivered, _ = teaching.explain_pending_task(context, state, step, 'Nasıl seçerim?', allow_provider=True)
    view = json.loads(call.call_args.kwargs['input'])
    assert delivered and view['previous_explanations'] == []
    assert 'private-category' not in call.call_args.kwargs['input']
    assert all('proportions' not in x and 'result' not in x for x in view['investigation_context']['verified_checks'])


def test_generic_mode_does_not_send_failed_source_diagnostics_or_real_labels():
    context, state, step, _ = request('sensors', 'error')
    context['mentor_setup']['notebook_teaching_context'] = 'generic'
    with runtime(), patch.object(teaching, 'guarded_responses_parse',
        return_value=SimpleNamespace(output_parsed=answer(), status='completed')) as call:
        delivered, _ = teaching.explain_pending_task(context, state, step, 'private-question', allow_provider=True)
    wire = call.call_args.kwargs['input']
    assert delivered and 'latest_attempt' not in wire
    assert 'reading' not in wire and 'sensor_mode' not in wire and 'private-question' not in wire


def test_numeric_conversation_reaches_route_without_becoming_a_fact_or_completing_task():
    context, state, step, _ = request('orders')
    candidate = answer(explanation='Eksik grupta açık kayıtların oranı %90; bu, eksikliğin nedenini kanıtlamaz.')
    with isolated_comparison_memory() as memory, runtime(), patch.object(teaching, 'guarded_responses_parse',
        return_value=SimpleNamespace(output_parsed=candidate, status='completed')):
        memory[(context['workspace_id'], 'n1')] = deepcopy(state)
        visible = generate_research_reply(context, 'Bu sonuç neyi gösterir?', [])
        after = memory[(context['workspace_id'], 'n1')]
    assert visible == candidate.answer
    assert after['workflow']['active_step']['id'] == step['id']
    assert after['workflow']['active_step']['status'] == 'awaiting_execution'
    assert after['last_validation']['teaching_accepted']
    assert after['last_validation']['model_factual_prose_published']
    assert not after['last_validation']['factual_claims_verified']
    assert not after['last_validation']['semantic_quality_verified']


@pytest.mark.parametrize('case,selected_rows', [('orders', 250), ('sensors', 400), ('service', 242)])
def test_population_distinguishes_frame_selected_group_and_fraction_denominator(case, selected_rows):
    _, _, _, payload = request(case)
    checks = teaching.teaching_provider_view(payload)['investigation_context']['verified_checks']
    distribution, count = checks
    assert distribution['population'] == {
        'dataframe_rows': 1000, 'selected_rows': selected_rows,
        'selected_rows_basis': 'matching_recorded_missing_count',
        'proportion_denominator_rows': selected_rows,
        'proportion_denominator': 'selected_rows_including_missing_categories'}
    assert 'input_rows' not in distribution
    assert distribution['purpose'] == 'describe category proportions'
    assert count['result'] == selected_rows and count['population']['selected_rows'] == 1000
    assert count['population']['proportion_denominator_rows'] is None


@pytest.mark.parametrize('change', ['version', 'kind', 'rows', 'unknown_version', 'unknown_rows',
    'stale', 'failed', 'unsupported', 'wrong_column', 'filtered_count', 'conflict'])
def test_population_does_not_join_incompatible_or_unverified_counts(change):
    _, state, _, _ = request()
    observations = deepcopy(verified_observations(state))
    distribution, count = observations
    if change == 'version': count['input_data_version'] = 'different'
    elif change == 'kind': count['dataset_kind'] = 'processed'
    elif change == 'rows': count['input_rows'] = 999
    elif change == 'unknown_version': distribution['input_data_version'] = None
    elif change == 'unknown_rows': distribution['input_rows'] = None
    elif change == 'stale': count['stale_scope'] = True
    elif change == 'failed': count['success'] = False
    elif change == 'unsupported': count['analysis_contract']['supported'] = False
    elif change == 'wrong_column': count['analysis_contract']['measured_columns'] = ['another_field']
    elif change == 'filtered_count': count['analysis_contract']['row_predicate'] = {'op': 'present', 'column': 'another_field'}
    elif change == 'conflict':
        other = deepcopy(count); other['analysis_contract']['result'] = 300; observations.append(other)
    population = observation_population(distribution, observations)
    assert population['selected_rows'] is None
    assert population['selected_rows_basis'] == 'unknown'
    assert population['proportion_denominator_rows'] is None


def test_population_complement_and_zero_are_exact_but_excluded_nulls_have_unknown_denominator():
    _, state, _, _ = request()
    observations = deepcopy(verified_observations(state))
    distribution, count = observations
    distribution['analysis_contract']['row_predicate']['op'] = 'present'
    population = observation_population(distribution, observations)
    assert population['selected_rows'] == population['proportion_denominator_rows'] == 750
    count['analysis_contract']['result'] = 1000
    assert observation_population(distribution, observations)['selected_rows'] == 0
    count['analysis_contract']['result'] = 250
    distribution['analysis_contract']['options']['dropna'] = True
    population = observation_population(distribution, observations)
    assert population['selected_rows'] == 750 and population['proportion_denominator_rows'] is None


def test_history_survives_task_transition_without_becoming_execution_evidence():
    context, state, step, _ = request()
    original = deepcopy(step)
    state['teaching_journal'] = [{'task_key': 'previous-completed-task',
        'scope_key': teaching.teaching_scope_key(context, state),
        'mode': 'user_shared_question_code_and_summaries', 'contract_version': 3,
        'question': 'Saymakla seçmek farklı mı?', 'explanation': 'Sayma bir sayı üretir.'}]
    with runtime(), patch.object(teaching, 'guarded_responses_parse',
        return_value=SimpleNamespace(output_parsed=answer(), status='completed')) as model:
        reply, trace = teaching.explain_pending_task(context, state, step, 'Peki sonra?', allow_provider=True)
    assert reply
    history = json.loads(model.call_args.kwargs['input'])['previous_explanations']
    assert history == [{'question': 'Saymakla seçmek farklı mı?', 'explanation': 'Sayma bir sayı üretir.'}]
    assert step == original and not trace['factual_claims_verified']


@pytest.mark.parametrize('boundary', ['workspace', 'notebook', 'version', 'kind', 'focus', 'consent'])
def test_history_does_not_cross_scope_or_sharing_boundaries(boundary):
    context, state, step, _ = request()
    state['teaching_journal'] = [{'task_key': task_key(step),
        'scope_key': teaching.teaching_scope_key(context, state),
        'mode': 'user_shared_question_code_and_summaries', 'contract_version': 3,
        'question': 'old-question', 'explanation': 'old-private-history'}]
    notebook = context['artifacts']['selected_notebook']
    if boundary == 'workspace': context['workspace_id'] = 'another-workspace'
    elif boundary == 'notebook': notebook['notebook_id'] = 'another-notebook'
    elif boundary == 'version': notebook['current_input_version'] = 'another-version'
    elif boundary == 'kind': notebook['dataset_kind'] = 'processed'
    elif boundary == 'focus': state['focus_column'] = 'another-field'
    elif boundary == 'consent': context['mentor_setup']['notebook_teaching_context'] = 'question_and_code'
    with runtime(), patch.object(teaching, 'guarded_responses_parse',
        return_value=SimpleNamespace(output_parsed=answer(), status='completed')) as model:
        teaching.explain_pending_task(context, state, step, 'Şimdi?', allow_provider=True)
    assert 'old-private-history' not in model.call_args.kwargs['input']
