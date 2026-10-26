"""Invented-data protocol tests; controlled replies do not prove live quality."""
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.app import database
from backend.app.mentor_adaptive_teaching_service import (
    TeachingExplanation, build_teaching_request, conceptual_request, explain_pending_task,
    normalize_teaching_presentation, validate_teaching,
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


def lesson(step, **changes):
    return TeachingExplanation.model_validate({'task_id': step['id'], 'approach': 'break_down',
        'explanation': 'Boşlukları saymak ile ilgili satırları seçmek farklı işlemlerdir.',
        'first_action': 'Önce delivery_days boş olan satırları belirleyen koşulu kur.',
        'why': 'Sonraki incelemeyi yalnız bu grupta yapabilmek için.', **changes})


def provider(reply):
    return patch('backend.app.mentor_adaptive_teaching_service.guarded_responses_parse',
        return_value=SimpleNamespace(output_parsed=reply, status='completed'))


def runtime():
    return patch('backend.app.mentor_adaptive_teaching_service.get_ai_runtime',
        return_value=SimpleNamespace(provider='groq', model='synthetic-test', client=object()))


def test_actual_question_prior_count_and_normalized_task_reach_teacher_without_help_keyword():
    context, state, step = setup_task()
    with runtime(), provider(lesson(step)) as model:
        reply = generate_research_reply(context, 'Önce neyi seçmeliyim? Kodu verme.', [])
    payload = json.loads(model.call_args.kwargs['input'])
    assert payload['learner_question'] == 'Önce neyi seçmeliyim? Kodu verme.'
    assert [x['operation'] for x in payload['completed_operations']] == ['missing_count']
    assert payload['completed_operations'][0]['row_predicate'] == {'op': 'all_current_df'}
    assert payload['task_contract']['operation'] == 'distribution'
    assert payload['task_contract']['options']['normalize'] is True
    assert payload['task_contract']['measured_columns'] == ['shipment_status']
    after = load_research_state(context['workspace_id'], 'n1')
    assert after['proposals'] == state['proposals'] and '```' not in reply
    assert after['workflow']['active_step']['id'] == step['id']
    assert after['workflow']['active_step']['status'] == 'awaiting_execution'
    assert after['last_validation']['teaching_accepted']
    assert not after['last_validation']['semantic_quality_verified']
    with runtime(), provider(lesson(step, approach='analogy', explanation='Bir süzgeç gibi düşün; koşul hangi satırların kalacağını belirler.')) as second:
        generate_research_reply(context, 'Hâlâ anlamadım; daha basit anlat.', [])
    followup = json.loads(second.call_args.kwargs['input'])
    assert followup['previous_explanations'][0]['explanation'] == lesson(step).explanation
    assert len(load_research_state(context['workspace_id'], 'n1')['teaching_journal']) == 2


def test_payload_excludes_raw_outputs_rows_and_relationship_map():
    context, state, step = setup_task()
    context['local_relationship_map'] = {'private-canary': 'secret'}
    state['observations'][0].update(output='private-canary', preview_rows=[{'key': 'private-canary'}])
    payload = json.dumps(build_teaching_request(context, state, step, 'Nasıl yaparım?'))
    assert 'private-canary' not in payload and 'input_rows' not in payload


@pytest.mark.parametrize('policy', [None, {},
    {'usage_context': 'personal', 'data_sensitivity': 'confidential'},
    {'usage_context': 'personal', 'data_sensitivity': 'restricted'},
    {'usage_context': 'work', 'data_sensitivity': 'internal', 'organization_id': 'org'}])
def test_protected_or_unknown_context_never_calls_provider(policy):
    context, state, step = setup_task()
    context['teaching_data_policy'] = policy
    with runtime() as model, provider(lesson(step)) as service:
        reply, trace = explain_pending_task(context, state, step, 'Nasıl yaparım?', allow_provider=True)
    assert reply is None and trace['reason'] == 'external_ai_policy' and trace['provider_calls'] == 0
    model.assert_not_called()
    service.assert_not_called()


@pytest.mark.parametrize('changes,reason', [
    ({'task_id': 'another-task'}, 'task_mismatch'),
    ({'first_action': 'df[delivery_days].isna()'}, 'code_or_numeric_claim'),
    ({'explanation': 'Eksik değer sayısı 207.'}, 'code_or_numeric_claim'),
    ({'first_action': 'private_reason sütununu incele.'}, 'unrelated_column')])
def test_invalid_explanation_uses_explicit_fallback_and_preserves_task(changes, reason):
    context, state, step = setup_task()
    context['dataset_profile_summary']['columns'].append('private_reason')
    with runtime(), provider(lesson(step, **changes)):
        reply = generate_research_reply(context, 'Anlamadım; kodu verme.', [])
    after = load_research_state(context['workspace_id'], 'n1')
    assert 'yerel yedek rehber' in reply and '```' not in reply
    assert after['last_validation']['reason'] == reason
    assert not after['last_validation']['teaching_accepted']
    assert after['proposals'] == state['proposals']
    assert 'teaching_journal' not in after


def test_same_explanation_is_not_republished_and_no_retry_cascade():
    context, state, step = setup_task()
    with runtime(), provider(lesson(step)) as model:
        generate_research_reply(context, 'Anlamadım.', [])
        reply = generate_research_reply(context, 'Hâlâ anlamadım.', [])
    assert model.call_count == 2
    assert 'yerel yedek rehber' in reply
    assert load_research_state(context['workspace_id'], 'n1')['last_validation']['reason'] == 'repeated_explanation'


def test_code_only_comes_from_pending_task_after_positive_consent():
    context, state, step = setup_task()
    with runtime(), provider(lesson(step)):
        reply = generate_research_reply(context, 'Kodu göster.', [])
    assert '```python\n' + step['code'] + '\n```' in reply
    with runtime(), provider(lesson(step, explanation='Önce koşulun hangi satırları seçtiğini düşün.')):
        reply = generate_research_reply(context, 'Kodu gösterme; daha basit anlat.', [])
    assert '```' not in reply


def test_provider_failure_is_visible_without_persisting_exception_body():
    context, state, step = setup_task()
    with runtime(), patch('backend.app.mentor_adaptive_teaching_service.guarded_responses_parse', side_effect=RuntimeError('secret-provider-body')):
        reply = generate_research_reply(context, 'Nasıl yaparım?', [])
    after = load_research_state(context['workspace_id'], 'n1')
    assert 'yerel yedek rehber' in reply and 'secret-provider-body' not in json.dumps(after)
    assert after['last_validation']['reason'] == 'provider_or_schema_error'
    assert after['last_validation']['provider_calls'] == 1
    assert not after['last_validation']['teaching_accepted']


def test_stale_task_does_not_call_teacher():
    context, state, step = setup_task()
    step['status'] = 'needs_revalidation'
    with runtime() as model:
        reply, trace = explain_pending_task(context, state, step, 'Anlamadım.', allow_provider=True)
    assert reply is None and trace['reason'] == 'task_requires_revalidation'
    model.assert_not_called()


def test_unclassified_personal_mode_never_transmits_schema_free_text_or_values():
    context, state, step = setup_task()
    context['teaching_data_policy']['data_sensitivity'] = None
    neutral = lesson(step, task_id='pending-task', first_action='Önce FIELD_A boş olan satırları seçen koşulu düşün.')
    with runtime(), provider(neutral) as model:
        reply = generate_research_reply(context, 'Tam anlamadım; önce neyi seçmeliyim? private-customer-canary.', [])
    payload = model.call_args.kwargs['input']
    assert 'delivery_days' not in payload and 'shipment_status' not in payload and 'private-customer-canary' not in payload
    assert 'Tam anlamadım' not in payload
    assert json.loads(payload)['learner_question']['asks_where_to_start']
    assert 'delivery_days boş olan' in reply and 'FIELD_A' not in reply
    with runtime(), provider(neutral.model_copy(update={'explanation': 'Bir süzgeç gibi düşün; boş hücreli satırları ayıracağız.'})) as second:
        generate_research_reply(context, 'Hâlâ anlamadım.', [])
    followup = second.call_args.kwargs['input']
    assert 'private-customer-canary' not in followup and 'delivery_days' not in followup
    assert json.loads(followup)['previous_explanations'][0]['first_action'].startswith('Önce FIELD_A')


def test_conceptual_payload_strips_comparison_literals_and_arbitrary_learner_metadata():
    context, state, step = setup_task()
    step['code'] = "df.loc[df['private_status'] == 'private-category', ['private_amount']].value_counts()"
    context['mentor_setup'] = {'experience_level': 'private-canary'}
    payload, _ = conceptual_request(build_teaching_request(context, state, step, 'private-question'), 'private-question')
    assert 'private-' not in json.dumps(payload) and 'private_' not in json.dumps(payload)


def test_partial_attempt_is_visible_without_completing_distribution():
    context, state, step = setup_task()
    cell = recorded_cell('partial', "df['delivery_days'].isna()", '0 True\n1 False', 'delivery_days', 'teaching-synthetic-v1', 1000)
    notebook = context['artifacts']['selected_notebook']
    notebook['latest_cell'] = cell
    notebook['recent_cells'].insert(0, cell)
    with runtime(), provider(lesson(step)) as model:
        generate_research_reply(context, 'Koşulu kurdum; şimdi?', [])
    shape = json.loads(model.call_args.kwargs['input'])['last_attempt_shape']
    assert shape['uses_missing_condition'] and not shape['uses_row_selection']
    assert not shape['uses_distribution'] and not shape['contract_supported']
    after = load_research_state(context['workspace_id'], 'n1')
    assert after['workflow']['active_step']['id'] == step['id']
    assert after['workflow']['active_step']['status'] == 'awaiting_execution'


def test_same_step_number_on_another_version_does_not_reuse_old_explanation():
    context, state, step = setup_task()
    with runtime(), provider(lesson(step)):
        reply, _ = explain_pending_task(context, state, step, 'Anlamadım.', allow_provider=True)
    assert reply is not None
    assert build_teaching_request(context, state, {**step, 'expected_version': 'different'}, 'Anlamadım.')['previous_explanations'] == []


def test_probe_mechanical_pass_is_not_mislabeled_as_novice_or_live_acceptance():
    replies = [TeachingExplanation(task_id='pending-task', approach='break_down', explanation=text,
        first_action='Önce FIELD_A boş olan satırların koşulunu düşün.', why='Karşılaştırmanın grubunu belirlemek için.')
        for text in ('Sayım miktarı bulur; seçim kayıtları ayırır.', 'Bir süzgeç düşün; koşula uyan kayıtlar kalır.')]
    with runtime(), patch('backend.app.mentor_adaptive_teaching_service.guarded_responses_parse',
        side_effect=[SimpleNamespace(output_parsed=x, status='completed') for x in replies]):
        report = run_probe()
    assert report['mechanical_checks_passed'] and report['human_review_required']
    assert not report['novice_usability_accepted'] and not report['project_completion_proven']


@pytest.mark.parametrize('explanation', [
    'Önce `delivery_days` boş olan satırları seçen koşulu düşün.',
    'Önce **`delivery_days`** boş olan satırları seçen koşulu düşün.',
    'Burada koşul (boşluk kontrolü) hangi satırların kalacağını belirler.',
    'First choose the condition (missing values) that defines the rows.',
    'Kies eerst de voorwaarde (ontbrekende waarden) voor de rijselectie.',
    '1. Önce delivery_days boş olan satırları düşün.',
    'Boşlukları isna ile belirleriz; `value_counts` dağılımı anlatan işlem adıdır.',
])
def test_prose_formatting_and_parentheses_do_not_masquerade_as_code(explanation):
    context, state, step = setup_task()
    with runtime(), provider(lesson(step, explanation=explanation)):
        reply = generate_research_reply(context, 'Önce neyi seçmeliyim? Kodu verme.', [])
    after = load_research_state(context['workspace_id'], 'n1')
    assert after['last_validation']['teaching_accepted'], after['last_validation']
    assert after['proposals'] == state['proposals']
    assert 'yerel yedek rehber' not in reply and '```' not in reply and '`' not in reply


def test_generic_alias_markup_is_restored_locally_after_normalizing_format():
    context, state, step = setup_task()
    context['teaching_data_policy']['data_sensitivity'] = None
    formatted = lesson(step, task_id='pending-task',
        explanation='Satır seçimi (bir süzgeç gibi) ilgili grubu ayırır.',
        first_action='1. Önce `FIELD_A` boş olan satırların koşulunu düşün.')
    with runtime(), provider(formatted) as model:
        reply = generate_research_reply(context, 'Önce neyi seçmeliyim?', [])
    trace = load_research_state(context['workspace_id'], 'n1')['last_validation']
    assert trace['teaching_accepted'] and trace['presentation_normalized']
    assert 'delivery_days boş olan' in reply and 'FIELD_A' not in reply
    assert 'delivery_days' not in model.call_args.kwargs['input']


@pytest.mark.parametrize('bad', [
    '```python\ndf.head()\n```', '`df["delivery_days"].isna()`',
    'df["delivery_days"]', 'isna()', 'isna ()', 'custom_function()',
    'Eksik satır sayısı 207.', 'Oran yüzde 80.', '2. Yeni bir incelemeye geç.',
])
def test_formatting_cleanup_does_not_strip_actual_code_or_measurements(bad):
    context, state, step = setup_task()
    candidate = normalize_teaching_presentation(lesson(step, explanation=bad))
    payload = build_teaching_request(context, state, step, 'Kodu verme.')
    assert validate_teaching(candidate, payload, ['delivery_days', 'shipment_status']) == 'code_or_numeric_claim'


def test_rejection_records_exact_field_and_category_without_leaking_candidate_into_prompt():
    context, state, step = setup_task()
    with runtime(), provider(lesson(step, why='Eksik sayısı 207 olduğu için.')):
        generate_research_reply(context, 'Kodu verme.', [])
    after = load_research_state(context['workspace_id'], 'n1')
    expected = [{'field': 'why', 'kind': 'numeric_literal'}]
    assert after['last_validation']['validation_violations'] == expected
    assert after['last_rejected_teaching']['violations'] == expected
    assert after['last_rejected_teaching']['candidate']['why'] == 'Eksik sayısı 207 olduğu için.'
    outbound = json.dumps(build_teaching_request(context, after, step, 'Nasıl?'))
    assert '207' not in outbound and 'last_rejected_teaching' not in outbound
    assert '207' not in json.dumps(after['last_validation'])


def test_presentation_changes_do_not_evade_repeat_guard():
    context, state, step = setup_task()
    first = lesson(step, explanation='Önce `delivery_days` boş olan satırları düşün.')
    with runtime(), provider(first):
        generate_research_reply(context, 'Nasıl?', [])
    with runtime(), provider(first.model_copy(update={'explanation': 'Önce delivery_days boş olan satırları düşün.'})):
        generate_research_reply(context, 'Hâlâ anlamadım.', [])
    assert load_research_state(context['workspace_id'], 'n1')['last_validation']['reason'] == 'repeated_explanation'
