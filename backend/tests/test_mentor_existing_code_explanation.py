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


@pytest.mark.parametrize('fragment', ['df[row_flags]', 'df[condition_vector]', 'df.loc[chosen_rows]', 'df.iloc[positions]'])
@pytest.mark.parametrize('language', ['tr', 'en', 'nl'])
def test_conceptual_selection_reference_is_prose_not_execution_evidence(fragment, language):
    from backend.app.mentor_adaptive_teaching_service import render_conceptual_selection_references
    request = payload(language=language)
    original = response(f'`{fragment}` is an illustrative selection, not a completed action.')
    rendered, count = render_conceptual_selection_references(original, request)
    assert count == 1
    assert '[' not in rendered.explanation and '`' not in rendered.explanation
    assert fragment in original.explanation
    assert rendered.first_action == original.first_action
    assert validate_teaching(rendered, request, ['signal_value', 'device_state']) is None


@pytest.mark.parametrize('fragment', [
    'df.dropna()', "df[df['signal_value'].isna()]", "df['another_field']",
    'df[make_mask()]', 'df[[chosen_rows]]', 'other_frame[chosen_rows]',
    'df.loc[chosen_rows, secret_field]', 'df[chosen_rows] = 0',
    '__import__("os").system("example")', 'df.loc[lambda x: x]',
])
def test_conceptual_reference_rendering_cannot_authorize_new_code_or_fields(fragment):
    from backend.app.mentor_adaptive_teaching_service import render_conceptual_selection_references
    request = payload()
    rendered, count = render_conceptual_selection_references(response(f'`{fragment}` is a reference.'), request)
    assert count == 0 and validate_teaching(rendered, request, ['signal_value', 'device_state']) == 'code_or_numeric_claim'


@pytest.mark.parametrize('source', [None, '', "df.dropna(inplace=True)"])
def test_generic_or_unsupported_source_cannot_enable_conceptual_code_rendering(source):
    from backend.app.mentor_adaptive_teaching_service import render_conceptual_selection_references
    rendered, count = render_conceptual_selection_references(response('`df[row_flags]` selects data.'), payload(source=source))
    assert count == 0 and '[' in rendered.explanation


@pytest.mark.parametrize('field', ['first_action', 'why'])
def test_conceptual_code_is_not_rendered_in_an_instruction(field):
    from backend.app.mentor_adaptive_teaching_service import render_conceptual_selection_references
    candidate = response('An ordinary explanation.').model_copy(update={field: '`df[row_flags]`'})
    rendered, count = render_conceptual_selection_references(candidate, payload())
    assert count == 0 and validate_teaching(rendered, payload(), ['signal_value', 'device_state']) == 'code_or_numeric_claim'


def test_concept_rendering_does_not_hide_fences_or_unverified_measurements():
    from backend.app.mentor_adaptive_teaching_service import render_conceptual_selection_references
    for text in ('```python\ndf[row_flags]\n```', '`df[row_flags]` selected 927 records.'):
        rendered, _ = render_conceptual_selection_references(response(text), payload())
        assert validate_teaching(rendered, payload(), ['signal_value', 'device_state']) == 'code_or_numeric_claim'


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
