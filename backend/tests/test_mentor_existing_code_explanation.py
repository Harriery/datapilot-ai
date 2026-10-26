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
