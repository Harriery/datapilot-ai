"""Source-bound explanations with invented fields; no actual user transcript."""
import json

import pytest

from backend.app import database
from backend.app.mentor_adaptive_teaching_service import (
    TeachingExplanation, normalize_teaching_presentation, render_existing_code_references, validate_teaching,
)
from backend.app.mentor_observation_contract import expression_contract
from backend.app.mentor_research_service import generate_research_reply
from backend.app.mentor_research_store import load_research_state
from backend.tests.test_mentor_adaptive_teaching import setup_task, runtime, provider, lesson


def payload(source="df['signal_value'].isna().sum()", language='tr'):
    return {'task_id': 'pending-task', 'response_language': language,
        'latest_verified_expression': source,
        'task_contract': expression_contract("df.loc[df['signal_value'].isna(), 'device_state'].value_counts(dropna=False, normalize=True)"),
        'previous_explanations': []}


def response(text, **changes):
    return TeachingExplanation(task_id='pending-task', approach='break_down', explanation=text,
        first_action='Önce signal_value boş olan kayıtları belirleyen koşulu düşün.',
        why='İlgili satır grubunu ayırmak için.', **changes)


def checked(candidate, request):
    rendered, count = render_existing_code_references(candidate, request)
    rendered = normalize_teaching_presentation(rendered)
    return rendered, count, validate_teaching(rendered, request, ['signal_value', 'device_state'])


@pytest.mark.parametrize('fragment', [
    "df['signal_value'].isna().sum()", 'df["signal_value"].isna().sum()',
    "df['signal_value']", "df['signal_value'].isna()", '.isna()', '.sum()',
    'isna()', 'sum()', 'df',
])
def test_only_exact_verified_parts_are_rendered_as_prose(fragment):
    candidate, count, error = checked(response(f'`{fragment}` mevcut işlemin bir parçasıdır.'), payload())
    assert count == 1 and error is None
    assert '`' not in candidate.explanation and '(' not in candidate.explanation
    assert '[' not in candidate.explanation


@pytest.mark.parametrize('language,label', [('tr', 'isna adımı'), ('en', 'the isna operation'), ('nl', 'de bewerking isna')])
def test_source_reference_labels_follow_response_language(language, label):
    rendered, count, error = checked(response('`.isna()` eksik hücreleri işaretler.'), payload(language=language))
    assert error is None and count == 1 and label in rendered.explanation


@pytest.mark.parametrize('new_code', [
    "df[df['signal_value'].isna()]", "df['device_state'].value_counts()",
    'df.dropna()', '.isna(axis=0)', '.sum(min_count=1)', 'sum(axis=0)',
    "df['another_column']", 'eval()',
])
def test_new_selection_measurement_arguments_or_fields_are_not_source_references(new_code):
    _, count, error = checked(response(f'Şimdi `{new_code}` kullan.'), payload())
    assert count == 0 and error == 'code_or_numeric_claim'


@pytest.mark.parametrize('field', ['first_action', 'why'])
def test_source_code_cannot_be_smuggled_into_an_action_or_reason(field):
    data = response('İşaretler ile sayım farklıdır.').model_dump()
    data[field] = "`df['signal_value'].isna().sum()`"
    _, count, error = checked(TeachingExplanation.model_validate(data), payload())
    assert count == 0 and error == 'code_or_numeric_claim'


def test_code_fences_and_numerical_claims_remain_rejected():
    for text in ("```python\ndf['signal_value'].isna().sum()\n```", '`.isna()` kontrolünde 341 eksik var.'):
        _, _, error = checked(response(text), payload())
        assert error == 'code_or_numeric_claim'


@pytest.mark.parametrize('source', [None, '', "df['other_field'].isna().sum()", "__import__('os').system('example')"])
def test_missing_mismatched_or_unsupported_source_cannot_authorize_code(source):
    _, count, error = checked(response("`df['signal_value'].isna().sum()` işlemini düşün."), payload(source=source))
    assert count == 0 and error == 'code_or_numeric_claim'


def test_code_like_text_inside_a_literal_is_not_extracted_as_verified_source():
    source = "df['not_code.isna()'].isna().sum()"
    _, count, error = checked(response('`not_code.isna()` kullan.'), payload(source=source))
    assert count == 0 and error == 'code_or_numeric_claim'


def test_verified_preview_parameter_is_a_reference_not_an_invented_result():
    request = payload(source="df['signal_value'].head(5)")
    rendered, count, error = checked(response('`.head(5)` daha önceki önizleme adımıdır.'), request)
    assert error is None and count == 1 and '5' not in rendered.explanation
    _, count, error = checked(response('`.head(9)` kullan.'), request)
    assert count == 0 and error == 'code_or_numeric_claim'


@pytest.mark.parametrize('source,fragment', [
    ("df.loc[df['signal_value'].notna(), ['device_state']].head(5)", "df.loc[df['signal_value'].notna(), ['device_state']]"),
    ("df.loc[df['signal_value'] >= 0, 'device_state'].value_counts()", "df['signal_value'] >= 0"),
    ("df['signal_value'].mean()", '.mean()'),
    ("df['device_state'].value_counts(normalize=True, dropna=False)", '.value_counts(normalize=True, dropna=False)'),
])
def test_source_references_cover_supported_inspections_beyond_missing_count(source, fragment):
    _, count, error = checked(response(f'`{fragment}` mevcut incelemenin bu parçasıdır.'), payload(source=source))
    assert count == 1 and error is None


def test_quoted_explanation_passes_actual_pipeline_without_completing_task(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'source-references.sqlite')
    database.init_db()
    context, state, step = setup_task()
    context['teaching_data_policy']['data_sensitivity'] = None
    context['mentor_setup']['notebook_teaching_context'] = 'question_and_code'
    explanation = (
        "`df['delivery_days'].isna().sum()` mevcut sayımı yapar. "
        "`df['delivery_days']` incelenen sütundur. `.isna()` boş hücreleri işaretler. "
        "`.sum()` işaretleri sayar; kayıtları seçmez."
    )
    with runtime(), provider(lesson(step, explanation=explanation)) as model:
        reply = generate_research_reply(context, 'isna ve sumun görevini açıkla; kodu verme.', [])
    after = load_research_state(context['workspace_id'], 'n1')
    assert model.call_count == 1
    assert after['last_validation']['teaching_accepted']
    assert after['last_validation']['existing_code_references_rendered'] == 4
    assert after['proposals'] == state['proposals']
    assert after['workflow']['active_step']['status'] == 'awaiting_execution'
    assert '`' not in reply and 'df[' not in reply and '.isna()' not in reply
    assert 'isna adımı boş hücreleri işaretler' in reply
    # The journal stores the displayed prose, not unapproved generated code.
    assert 'df[' not in json.dumps(after['teaching_journal'])


@pytest.mark.parametrize('generic', [False, True])
def test_concept_only_reply_needs_no_new_assignment_and_does_not_complete_task(tmp_path, monkeypatch, generic):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'concept-only.sqlite')
    database.init_db()
    context, state, step = setup_task()
    if generic:
        context['teaching_data_policy']['data_sensitivity'] = None
    candidate = lesson(step, task_id='pending-task' if generic else step['id'], first_action=None, why=None,
        explanation='True olan satırların kalmasına, False olanların dışarıda kalmasına filtre karar verir.')
    with runtime(), provider(candidate) as model:
        visible = generate_research_reply(context, 'İşaretleri nasıl kullanacağımı yalnızca açıkla, yeni görev verme.', [])
    after = load_research_state(context['workspace_id'], 'n1')
    assert model.call_count == 1
    assert visible == candidate.explanation
    assert after['last_validation']['content_accepted'] and after['last_validation']['workflow_valid']
    assert after['workflow']['active_step']['status'] == 'awaiting_execution'
    assert after['proposals'] == state['proposals']
    assert after['teaching_journal'][-1]['first_action'] is None
    assert after['teaching_journal'][-1]['why'] is None


@pytest.mark.parametrize('field,value', [
    ('first_action', 'df.dropna(inplace=True)'),
    ('first_action', "df[df['signal_value'].isna()]"),
    ('first_action', 'SELECT * FROM private_table'),
    ('first_action', 'another_field sütununu incele.'),
    ('first_action', 'Önce 927 eksik kaydı sil.'),
    ('why', 'Oran yüzde 83 olduğu için.'),
    ('why', 'https://example.invalid adresine gönder.'),
    ('why', 'df[condition_flags] kullanıldığı için.'),
])
def test_invalid_optional_guidance_is_omitted_as_a_unit_not_used_as_a_solution(field, value):
    from backend.app.mentor_adaptive_teaching_service import compile_teaching_delivery
    original = response('Sayım bir toplam verir; satır seçimi ilgili kayıtları ayırır.').model_copy(update={field: value})
    delivered, audit = compile_teaching_delivery(original, payload(), ['signal_value', 'device_state', 'another_field'])
    assert delivered.explanation == original.explanation
    assert delivered.first_action is None and delivered.why is None
    assert audit['provider_contract_accepted'] is False
    assert audit['reason'] == 'optional_guidance_omitted'
    assert audit['delivered_sections'] == ['explanation']
    assert set(audit['omitted_sections']) == {'first_action', 'why'}
    assert original.model_dump()[field] == value
    assert validate_teaching(delivered, payload(), ['signal_value', 'device_state', 'another_field']) is None


@pytest.mark.parametrize('bad_explanation', [
    '`df[row_flags]` ile seç.', 'df.loc[condition_flags] ile seç.',
    'Eksik sayısı 927.', 'another_field sütununu kontrol ettik.',
    "```python\ndf['signal_value'].fillna(0)\n```",
])
def test_bad_explanation_is_not_salvaged_by_dropping_sentences_or_rewriting_new_code(bad_explanation):
    from backend.app.mentor_adaptive_teaching_service import compile_teaching_delivery
    candidate = response(bad_explanation)
    delivered, audit = compile_teaching_delivery(candidate, payload(), ['signal_value', 'device_state', 'another_field'])
    assert delivered is None and audit['delivery_mode'] == 'blocked'
    assert audit['provider_contract_accepted'] is False
    assert not audit['delivered_sections']


@pytest.mark.parametrize('bad_binding', ['task', 'unknown_evidence', 'missing_evidence'])
def test_identity_and_evidence_binding_failures_block_the_whole_delivery(bad_binding):
    from backend.app.mentor_adaptive_teaching_service import compile_teaching_delivery
    candidate = response('Kısa bir kavram açıklaması.')
    if bad_binding == 'task':
        candidate.task_id = 'different-task'
    elif bad_binding == 'unknown_evidence':
        candidate.evidence_ids = ['unknown']
    else:
        candidate.conversation_kind = 'evidence'
    delivered, audit = compile_teaching_delivery(candidate, payload(), ['signal_value', 'device_state'])
    assert delivered is None and audit['provider_contract_accepted'] is False


def test_reason_without_action_is_not_presented_as_an_independent_instruction():
    from backend.app.mentor_adaptive_teaching_service import compile_teaching_delivery
    candidate = response('İşaretler ilgili satırları belirlemeye yarar.').model_copy(update={'first_action': None})
    delivered, audit = compile_teaching_delivery(candidate, payload(), ['signal_value', 'device_state'])
    assert delivered.explanation == candidate.explanation
    assert delivered.why is None and audit['omitted_sections'] == ['why']
    assert audit['guidance_rejection_reason'] == 'orphan_reason'


@pytest.mark.parametrize('generic,request_code', [(False, False), (True, False), (False, True)])
def test_production_delivery_keeps_valid_prose_and_only_backend_authorized_code(tmp_path, monkeypatch, generic, request_code):
    from backend.app.mentor_adaptive_teaching_service import build_teaching_request
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'section-delivery.sqlite')
    database.init_db()
    context, state, step = setup_task()
    if generic:
        context['teaching_data_policy']['data_sensitivity'] = None
    malicious = 'df.dropna(inplace=True)'
    candidate = lesson(step, task_id='pending-task' if generic else step['id'],
        explanation='Sayım tek bir toplam verir. Seçim ise ilgili satırları ayırır.', first_action=malicious)
    message = 'Kodu göster.' if request_code else 'Yalnızca farkı açıkla; kodu verme.'
    with runtime(), provider(candidate) as model:
        visible = generate_research_reply(context, message, [])
    after = load_research_state(context['workspace_id'], 'n1')
    trace = after['last_validation']
    assert model.call_count == 1
    assert trace['teaching_accepted'] and trace['content_accepted'] and trace['workflow_valid']
    assert trace['provider_contract_accepted'] is False
    assert trace['delivery_mode'] == 'explanation_only'
    assert malicious not in visible and 'yerel yedek rehber' not in visible
    assert candidate.explanation in visible
    if request_code:
        assert '```python\n' + step['code'] + '\n```' in visible
    else:
        assert '```' not in visible and visible == candidate.explanation
    assert after['proposals'] == state['proposals']
    assert after['workflow']['active_step']['status'] == 'awaiting_execution'
    assert malicious in after['last_teaching_attempt']['provider_candidate']['first_action']
    assert after['last_teaching_attempt']['accepted'] is False
    assert malicious not in json.dumps(after['teaching_journal'])
    outbound = build_teaching_request(context, after, step, 'Nasıl?')
    assert malicious not in json.dumps(outbound)
