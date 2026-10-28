"""Conversation delivery and authority boundaries; invented data, controlled model.

Numbers/formatting are not factual proof. This suite deliberately does not turn
schema or presentation acceptance into a learning-quality score.
"""
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from backend.app import database
from backend.app.mentor_adaptive_teaching_service import (
    TeachingAnswer, build_teaching_request, conceptual_request, explain_pending_task,
    assess_teaching_answer,
)
from backend.app.mentor_research_service import generate_research_reply
from backend.app.mentor_research_store import load_research_state
from backend.benchmarks.run_mentor_teaching_probe import synthetic_context, run_probe
from backend.benchmarks.run_mentor_connected_followup import recorded_cell


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'teaching.sqlite')
    database.init_db()


def setup_task():
    context = synthetic_context(public=True)
    generate_research_reply(context, 'delivery_days sayımını yaptım. Veri sözlüğüm yok; sonraki tek adımı söyle.', [], allow_provider=False)
    state = load_research_state(context['workspace_id'], 'n1')
    return context, state, state['workflow']['active_step']


def lesson(step=None, *, explanation='Sayım miktarı bulur; seçim ilgili kayıtları ayırır.'):
    return TeachingAnswer(answer=explanation)


def provider(reply):
    return patch('backend.app.mentor_adaptive_teaching_service.guarded_responses_parse',
        return_value=SimpleNamespace(output_parsed=reply, status='completed'))


def runtime():
    return patch('backend.app.mentor_adaptive_teaching_service.get_ai_runtime',
        return_value=SimpleNamespace(provider='groq', model='synthetic-test', client=object()))


def test_current_question_work_scope_and_history_reach_one_answer_only_call():
    context, state, step = setup_task()
    with runtime(), provider(lesson(step)) as model:
        visible = generate_research_reply(context, 'Önce neyi seçmeliyim? Kodu verme.', [])
    payload = json.loads(model.call_args.kwargs['input'])
    assert model.call_args.kwargs['text_format'] is TeachingAnswer
    assert payload['learner_question'] == 'Önce neyi seçmeliyim? Kodu verme.'
    assert payload['completed_operations'][0]['purpose'] == 'count missing values'
    assert payload['pending_step']['purpose'] == 'describe category proportions'
    assert payload['pending_step']['columns'] == ['shipment_status']
    assert payload['response_preferences'] == {'show_code': False}
    assert 'task_id' not in payload and 'result_facts' not in payload
    assert 'row_predicate' not in json.dumps(payload)
    assert visible == lesson(step).answer
    after = load_research_state(context['workspace_id'], 'n1')
    assert after['proposals'] == state['proposals']
    assert after['workflow']['active_step']['id'] == step['id']
    assert after['workflow']['active_step']['status'] == 'awaiting_execution'
    assert not after['last_validation']['semantic_quality_verified']
    with runtime(), provider(lesson(explanation='Bir süzgeç düşün: işaretler hangi kayıtların kalacağını belirler.')) as second:
        generate_research_reply(context, 'Hâlâ anlamadım.', [])
    assert json.loads(second.call_args.kwargs['input'])['previous_explanations'][0]['explanation'] == lesson().answer


@pytest.mark.parametrize('text', [
    'Eksik kayıtların %90 kadarı açık, %10 kadarı kapalı; bu tek başına iş kuralı değildir.',
    'Oran olarak 0.9, yüzde olarak %90 ifade edilir.',
    'İşlem 2 aşamada düşünülebilir: işaretleme ve satır seçimi.',
    '`isna` işaretleri üretir; `sum` bunları sayar.',
    'Koşul (True veya False) bir satır seçimi değildir.',
])
def test_natural_measurements_and_formatting_are_delivered_without_certifying_truth(text):
    context, state, step = setup_task()
    with runtime(), provider(lesson(explanation=text)) as model:
        visible = generate_research_reply(context, 'Kodu verme, açıkla.', [])
    after = load_research_state(context['workspace_id'], 'n1')
    assert visible == text and model.call_count == 1
    assert after['last_validation']['content_accepted']
    assert after['last_validation']['model_factual_prose_published']
    assert not after['last_validation']['factual_claims_verified']
    assert not after['last_validation']['semantic_quality_verified']
    assert after['proposals'] == state['proposals']


def test_wrong_measurement_is_not_silently_certified_by_a_matching_number_or_passing_schema():
    # No semantic/numeric checker is claimed. Deliberately wrong prose remains
    # a quality problem, flagged for human evaluation, never factual authority.
    context, state, step = setup_task()
    with runtime(), provider(lesson(explanation='Eksik değer sayısı 999999.')):
        generate_research_reply(context, 'Sonucu açıkla.', [])
    after = load_research_state(context['workspace_id'], 'n1')
    trace = after['last_validation']
    assert 'numeric_prose_requires_review' in trace['quality_signals']
    assert trace['factual_claims_verified'] is False
    assert trace['semantic_quality_verified'] is False
    assert after['workflow']['active_step']['status'] == 'awaiting_execution'
    assert after['proposals'] == state['proposals']


@pytest.mark.parametrize('text', [
    "df['delivery_days'].isna()", '```python\ndf.head()\n```',
    'Bu işaretleri df[mask] ile kullan.', 'isna () ile koşulu kur.',
])
def test_unrequested_code_is_a_preference_failure_not_a_numeric_or_provider_failure(text):
    context, state, step = setup_task()
    with runtime(), provider(lesson(explanation=text)) as model:
        visible = generate_research_reply(context, 'Kodu verme.', [])
    after = load_research_state(context['workspace_id'], 'n1')
    assert 'Kod istemediğin' in visible and text not in visible
    assert model.call_count == 2 and after['last_validation']['reason'] == 'code_not_requested'
    assert not after['last_validation']['content_accepted']
    assert after['proposals'] == state['proposals']
    assert not after.get('teaching_journal')


def test_requested_model_code_is_suggestion_text_and_never_a_validated_execution_artifact():
    context, state, step = setup_task()
    code = "df['delivery_days'].isna()"
    with runtime(), provider(lesson(explanation='```python\n'+code+'\n```')):
        visible = generate_research_reply(context, 'Kodu göster.', [])
    after = load_research_state(context['workspace_id'], 'n1')
    assert code in visible and step['code'] not in visible
    assert after['last_validation']['code_artifact_source'] == 'model_suggestion_not_executed'
    assert after['proposals'] == state['proposals']
    assert after['workflow']['active_step']['status'] == 'awaiting_execution'


def test_requesting_code_can_still_display_pending_read_only_code_without_provider():
    context, state, step = setup_task()
    visible = generate_research_reply(context, 'Kodu göster.', [], allow_provider=False)
    assert '```python\n'+step['code']+'\n```' in visible
    assert load_research_state(context['workspace_id'], 'n1')['last_validation']['code_artifact_source'] == 'validated_pending_task'


def test_repetition_is_a_quality_signal_not_an_all_answer_delivery_gate():
    context, state, step = setup_task()
    with runtime(), provider(lesson()) as model:
        generate_research_reply(context, 'Anlamadım.', [])
        visible = generate_research_reply(context, 'Hâlâ anlamadım.', [])
    trace = load_research_state(context['workspace_id'], 'n1')['last_validation']
    assert visible == lesson().answer and model.call_count == 2
    assert 'repeated_explanation' in trace['quality_signals']
    assert not trace['semantic_quality_verified']


@pytest.mark.parametrize('policy', [None, {},
    {'usage_context': 'personal', 'data_sensitivity': 'confidential'},
    {'usage_context': 'personal', 'data_sensitivity': 'restricted'},
    {'usage_context': 'work', 'data_sensitivity': 'internal', 'organization_id': 'org'}])
def test_protected_or_unknown_context_never_calls_provider(policy):
    context, state, step = setup_task()
    context['teaching_data_policy'] = policy
    with runtime() as model, provider(lesson()) as service:
        result, trace = explain_pending_task(context, state, step, 'Nasıl?', allow_provider=True)
    assert result is None and trace['reason'] == 'external_ai_policy'
    model.assert_not_called(); service.assert_not_called()


def test_generic_mode_never_transmits_actual_question_code_or_labels_and_restores_aliases():
    context, state, step = setup_task()
    context['mentor_setup'] = {'notebook_teaching_context': 'generic'}
    with runtime(), provider(lesson(explanation='FIELD_A boş olan satırları düşün.')) as model:
        visible = generate_research_reply(context, 'private-question', [])
    wire = model.call_args.kwargs['input']
    assert 'delivery_days' not in wire and 'private-question' not in wire and 'latest_attempt' not in wire
    assert 'delivery_days boş' in visible and 'FIELD_A' not in visible


def test_provider_failure_does_not_persist_exception_body_or_make_a_retry():
    context, state, step = setup_task()
    with runtime(), patch('backend.app.mentor_adaptive_teaching_service.guarded_responses_parse', side_effect=RuntimeError('secret-body')) as model:
        generate_research_reply(context, 'Nasıl?', [])
    after = load_research_state(context['workspace_id'], 'n1')
    assert model.call_count == 1 and after['last_validation']['reason'] == 'provider_or_schema_error'
    assert 'secret-body' not in json.dumps(after)


def test_stale_task_does_not_call_teacher():
    context, state, step = setup_task()
    step['status'] = 'needs_revalidation'
    with runtime() as model:
        result, trace = explain_pending_task(context, state, step, 'Nasıl?', allow_provider=True)
    assert result is None and trace['reason'] == 'task_requires_revalidation'
    model.assert_not_called()


def test_provider_schema_cannot_propose_completion_task_ids_evidence_ids_or_actions():
    assert set(TeachingAnswer.model_json_schema()['properties']) == {'answer'}
    for key in ('task_id', 'evidence_ids', 'next_action', 'complete'):
        with pytest.raises(ValidationError):
            TeachingAnswer.model_validate({'answer': 'Açıklama.', key: True})


def test_no_code_revision_delivers_only_rechecked_answer_and_retains_first_rejection():
    context, state, step = setup_task()
    before = deepcopy(state)
    rejected = lesson(explanation='İşaretleri df[mask] ile satır seçmekte kullan.')
    revised = lesson(explanation='Her satırın işaretini bir seçim listesi olarak tabloya uygula; doğru işaretli satırlar alınır.')
    responses = [SimpleNamespace(status='completed', output_parsed=x) for x in (rejected, revised)]
    with runtime(), patch('backend.app.mentor_adaptive_teaching_service.guarded_responses_parse',
        side_effect=responses) as model:
        visible = generate_research_reply(context, 'Kodu vermeden açıkla.', [])
    after = load_research_state(context['workspace_id'], 'n1')
    trace = after['last_validation']
    assert visible == revised.answer and model.call_count == trace['provider_calls'] == 2
    assert trace['style_rewrite_used']
    assert trace['attempt_outcomes'] == [{'attempt': 1, 'reason': 'code_not_requested'}, {'attempt': 2, 'reason': None}]
    assert after['last_rejected_teaching']['candidate'] == rejected.model_dump()
    assert after['last_teaching_attempt']['provider_candidate'] == revised.model_dump()
    assert len(after['teaching_journal']) == 1 and after['teaching_journal'][0]['explanation'] == revised.answer
    first,second = [call.kwargs for call in model.call_args_list]
    a,b = json.loads(first['input']),json.loads(second['input'])
    revision = b.pop('answer_revision')
    assert a == b and revision['previous_answer'] == rejected.answer
    assert first['model'] == second['model'] and first['max_output_tokens'] == second['max_output_tokens']
    assert after['workflow']['active_step']['id'] == before['workflow']['active_step']['id']
    assert after['workflow']['active_step']['status'] == 'awaiting_execution'
    assert 'completion_evidence_id' not in after['workflow']['active_step']
    assert after['workflow']['step_history'] == before['workflow']['step_history']
    assert after['observations'] == before['observations']
    assert after['proposals'] == before['proposals']
    assert not trace['factual_claims_verified'] and not trace['semantic_quality_verified']


@pytest.mark.parametrize('second_kind', ['code', 'incomplete', 'schema', 'provider'])
def test_failed_revision_never_retries_again_or_records_a_delivered_lesson(second_kind):
    context, state, step = setup_task()
    before = deepcopy(step)
    rejected = SimpleNamespace(status='completed', output_parsed=lesson(explanation='df[mask] ile seç.'))
    second = {'code': rejected, 'incomplete': SimpleNamespace(status='incomplete'),
        'schema': SimpleNamespace(status='completed', output_parsed={'answer': '', 'next_action': 'execute'}),
        'provider': RuntimeError('private-provider-body')}[second_kind]
    with runtime(), patch('backend.app.mentor_adaptive_teaching_service.guarded_responses_parse',
        side_effect=[rejected, second]) as model:
        reply, trace = explain_pending_task(context, state, step, 'Kod verme.', allow_provider=True, max_attempts=2)
    assert reply is None and model.call_count == trace['provider_calls'] == 2
    assert step == before and not state.get('teaching_journal')
    assert 'private-provider-body' not in json.dumps(state) + json.dumps(trace)


def test_revision_is_not_requested_for_valid_answer_or_explicit_code_request():
    for message, candidate in [('Basit açıkla.', lesson()), ('Kodu göster.', lesson(explanation='df[mask]'))]:
        context, state, step = setup_task()
        with runtime(), provider(candidate) as model:
            reply, trace = explain_pending_task(context, state, step, message, allow_provider=True, max_attempts=2)
        assert reply and model.call_count == trace['provider_calls'] == 1
        assert not trace['style_rewrite_used']


def test_single_attempt_mode_preserves_benchmark_request_cap():
    context, state, step = setup_task()
    with runtime(), provider(lesson(explanation='df[mask]')) as model:
        reply, trace = explain_pending_task(context, state, step, 'Kod verme.', allow_provider=True, max_attempts=1)
    assert reply is None and model.call_count == trace['provider_calls'] == 1
    assert trace['reason'] == 'code_not_requested' and not trace['style_rewrite_used']


def test_revision_does_not_turn_wrong_prose_into_verified_facts():
    context, state, step = setup_task()
    with runtime(), patch('backend.app.mentor_adaptive_teaching_service.guarded_responses_parse',
        side_effect=[SimpleNamespace(status='completed', output_parsed=lesson(explanation='df[mask]')),
            SimpleNamespace(status='completed', output_parsed=lesson(explanation='Eksik kayıt sayısı 999999.'))]):
        reply, trace = explain_pending_task(context, state, step, 'Kod verme.', allow_provider=True, max_attempts=2)
    assert reply and not trace['factual_claims_verified'] and not trace['semantic_quality_verified']
    assert step['status'] == 'awaiting_execution'


@pytest.mark.parametrize('daily_limit,expected_requests', [(1, 1), (2, 2)])
def test_revision_uses_normal_usage_ledger_and_respects_remaining_quota(monkeypatch, daily_limit, expected_requests):
    monkeypatch.setenv('AI_FREE_ONLY', 'true')
    monkeypatch.setenv('AI_FREE_PROVIDER_ALLOWLIST', 'groq')
    monkeypatch.setenv('AI_DAILY_REQUEST_LIMIT', str(daily_limit))
    monkeypatch.setenv('AI_MONTHLY_REQUEST_LIMIT', '100')
    context, state, step = setup_task()
    parse = Mock(side_effect=[
        SimpleNamespace(status='completed', output_parsed=lesson(explanation='df[mask]')),
        SimpleNamespace(status='completed', output_parsed=lesson())])
    client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    with patch('backend.app.mentor_adaptive_teaching_service.get_ai_runtime',
        return_value=SimpleNamespace(provider='groq', model='controlled', client=client)):
        reply, trace = explain_pending_task(context, state, step, 'Kod verme.', allow_provider=True, max_attempts=2)
    assert parse.call_count == database.get_ai_usage_counts()['daily_requests'] == expected_requests
    assert bool(reply) == (daily_limit == 2)
    assert step['status'] == 'awaiting_execution'


def test_no_code_revision_keeps_generic_privacy_projection_and_paces_each_request():
    context, state, step = setup_task()
    context['mentor_setup']['notebook_teaching_context'] = 'generic'
    pacer = Mock()
    with runtime(), patch('backend.app.mentor_adaptive_teaching_service.guarded_responses_parse',
        side_effect=[SimpleNamespace(status='completed', output_parsed=lesson(explanation='df[mask]')),
            SimpleNamespace(status='completed', output_parsed=lesson(explanation='FIELD_A için işaretleri satır filtresi olarak uygula.'))]) as model:
        reply, trace = explain_pending_task(context, state, step, 'private-question', allow_provider=True,
            max_attempts=2, request_pacer=pacer)
    assert reply and pacer.call_count == model.call_count == 2
    for call in model.call_args_list:
        wire = call.kwargs['input']
        assert 'private-question' not in wire and 'delivery_days' not in wire and 'shipment_status' not in wire


def test_revision_is_skipped_when_its_added_draft_exceeds_existing_context_bound():
    context, state, step = setup_task()
    from backend.app import mentor_adaptive_teaching_service as teaching
    original = teaching.teaching_provider_view
    def large_but_valid(payload):
        view = original(payload)
        view['synthetic_padding'] = 'x' * (8900 - len(json.dumps(view, ensure_ascii=False)))
        return view
    candidate = lesson(explanation='df[mask] ' + 'x' * 2300)
    with runtime(), patch.object(teaching, 'teaching_provider_view', side_effect=large_but_valid), provider(candidate) as model:
        reply, trace = explain_pending_task(context, state, step, 'Kod verme.', allow_provider=True, max_attempts=2)
    assert reply is None and model.call_count == trace['provider_calls'] == 1
    assert trace['style_rewrite_blocker'] == 'context_budget'
    assert not state.get('teaching_journal')



def test_teaching_code_mode_scaffolds_without_a_strict_code_ban():
    from backend.app.mentor_tutoring_service import teaching_code_mode
    assert teaching_code_mode('İki sütunu nasıl karşılaştırabilirim?') == 'example'
    assert teaching_code_mode('Bana kod örneği ver.') == 'example'
    assert teaching_code_mode('Önce mantığını açıkla, kod verme.') == 'none'
    assert teaching_code_mode('Denedim; kodu göster.') == 'direct'
    assert teaching_code_mode('Explain this concept.') == 'none'


def test_general_how_question_can_receive_analogous_teaching_code():
    context, state, step = setup_task()
    example = ("Bir koşul, hangi satırların eksik olduğunu işaretler. "
               "Örneğin başka bir veri setinde `df['height'].isna()` "
               "True/False işaretleri üretir; satır saymaz.")
    with runtime(), provider(lesson(explanation=example)) as model:
        visible = generate_research_reply(context, 'Eksik satırları nasıl seçebilirim?', [])
    trace = load_research_state(context['workspace_id'], 'n1')['last_validation']
    assert visible == example and model.call_count == 1
    preferences = json.loads(model.call_args.kwargs['input'])['response_preferences']
    assert preferences == {'show_code': True, 'code_mode': 'example'}
    assert trace['teaching_accepted'] and trace['code_shown']
    assert trace['code_artifact_source'] == 'model_suggestion_not_executed'
