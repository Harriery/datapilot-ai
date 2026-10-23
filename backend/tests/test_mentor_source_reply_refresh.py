"""Unknown source -> one legacy preview refresh -> ordinary evidence guidance.

Only invented notebook fields and outputs; no learner data is included.
"""
from copy import deepcopy
from unittest.mock import patch

import pytest

from backend.app import database
from backend.app.mentor_evidence_refresh_service import plan_evidence_refresh
from backend.app.mentor_research_service import (
    generate_research_reply, prepare_research_context, update_definition_availability,
)
from backend.app.mentor_research_store import load_research_state, save_research_state
from backend.tests.test_mentor_latest_evidence_binding import example_context


@pytest.mark.parametrize('message', [
    'Bunu bilmiyorum, kaynak açıklaması da elimde yok. Bu durumda nasıl ilerleyebilirim?',
    'Kaynak açıklaması elimde yok.',
    'Bunu bilmiyorum.',
    'Bu tanımı bilmiyorum, beraber ilerleyelim.',
])
def test_source_reply_closes_pending_definition_question(message):
    state = {'focus_column': 'measurement', 'open_questions': ['Definition?'],
             'proposals': [{'kind': 'clarify', 'focus_column': 'measurement',
                            'instruction': 'Definition?', 'status': 'proposed'}]}
    update_definition_availability(state, message)
    assert state['definition_availability']['status'] == 'unavailable'
    assert state['proposals'][0]['status'] == 'answered_unavailable'
    assert 'Definition?' not in state['open_questions']


@pytest.mark.parametrize('message', ['Bunu bilmiyorum.', 'Bu sonuç eksik değil.', 'measurement boş değil.'])
def test_unrelated_negatives_without_pending_question_do_not_invent_source_status(message):
    state = {'focus_column': 'measurement', 'proposals': []}
    update_definition_availability(state, message)
    assert 'definition_availability' not in state


def legacy_context():
    context = example_context()
    notebook = context['artifacts']['selected_notebook']
    preview = {'cell_id': 'preview', 'code': "df.loc[df['measurement'].isna()].head(5)",
               'section_title': 'measurement', 'last_execution': {
                   'success': True, 'output': 'measurement indicator\n0 NaN False\n2 NaN True',
                   'input_row_count': 42, 'dataset_kind': 'working',
                   'executed_at': '2026-01-01T10:07:30'}}
    notebook['recent_cells'].insert(1, preview)
    notebook['current_input_version'] = 'toy-v1'
    return context


def test_unknown_source_and_beginner_help_refresh_same_cell_then_advance_without_provider(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'mentor.sqlite')
    database.init_db()
    context = legacy_context()
    state = prepare_research_context(context['artifacts']['selected_notebook'], 'measurement')
    state['proposals'] = [{'kind': 'clarify', 'focus_column': 'measurement',
                           'instruction': 'Definition?', 'status': 'proposed'}]
    save_research_state(context['workspace_id'], 'n1', state)
    with patch('backend.app.mentor_research_service.get_ai_runtime') as runtime, \
         patch('backend.app.mentor_research_service.guarded_responses_parse') as provider:
        first = generate_research_reply(context,
            'Bunu bilmiyorum, kaynak açıklaması da elimde yok. Bu durumda nasıl ilerleyebilirim? '
            'Kodu vermeden, kısa ve anlaşılır biçimde yalnızca yapacağım tek adımı söyle.', [])
        saved = load_research_state(context['workspace_id'], 'n1')
        assert saved['definition_availability']['status'] == 'unavailable'
        assert saved['proposals'][0]['status'] == 'answered_unavailable'
        assert saved['last_validation']['origin'] == 'local_evidence_refresh'
        assert saved['pending_evidence_refresh']['cell_id'] == 'preview'
        assert saved['pending_evidence_refresh']['status'] == 'requested'
        assert len(first) < 600 and '▶' in first and 'veri sözlüğü' not in first
        assert 'category' not in first and '```' not in first
        before = deepcopy(saved['proposals'])
        second = generate_research_reply(context, 'anlamadim ne yapicam bilmiyorum, beraber ilerleyelim', [])
        saved = load_research_state(context['workspace_id'], 'n1')
        assert saved['proposals'] == before  # help does not mark a refresh executed
        assert saved['pending_evidence_refresh']['status'] == 'requested'
        assert saved['pending_evidence_refresh']['cell_id'] == 'preview'
        assert first != second and 'Aynı adımdayız' in second and len(second) < 600

        notebook = context['artifacts']['selected_notebook']
        fresh = deepcopy(next(c for c in notebook['recent_cells'] if c['cell_id'] == 'preview'))
        fresh['last_execution'].update(input_data_version='toy-v1', input_total_row_count=42,
            executed_at='2026-01-01T10:12:00',
            preview_rows=[{'measurement': None, 'indicator': False}, {'measurement': None, 'indicator': True}])
        notebook['latest_cell'] = fresh
        notebook['recent_cells'] = [fresh] + [c for c in notebook['recent_cells'] if c['cell_id'] != 'preview']
        third = generate_research_reply(context, 'Güncel çıktıyı aldım. Sonraki tek adım ne?', [])
        saved = load_research_state(context['workspace_id'], 'n1')
        assert saved['pending_evidence_refresh']['status'] == 'observed'
        assert saved['last_validation']['origin'] == 'local_progress_policy'
        assert 'value_counts' in saved['proposals'][-1]['code']
        assert saved['focus_column'] == 'measurement' and 'denetiminden geçmedi' not in third
    runtime.assert_not_called()
    provider.assert_not_called()


@pytest.mark.parametrize('change', ['fresh', 'failed', 'stale', 'unsupported', 'unknown_scope', 'pending_task', 'explain_only'])
def test_refresh_does_not_invent_work_or_bypass_evidence_conditions(change):
    context = legacy_context()
    state = prepare_research_context(context['artifacts']['selected_notebook'], 'measurement')
    state['definition_availability'] = {'focus_column': 'measurement', 'status': 'unavailable'}
    preview = next(x for x in state['observations'] if x['cell_id'] == 'preview')
    if change == 'fresh': preview['version_verified'] = True
    elif change == 'failed': preview['success'] = False
    elif change == 'stale': preview['stale_scope'] = True
    elif change == 'unsupported': preview['analysis_contract']['supported'] = False
    elif change == 'unknown_scope': preview['input_rows'] = None
    elif change == 'pending_task': state['proposals'] = [{'kind': 'inspect', 'status': 'proposed'}]
    message = 'Anlamadım. Sadece sonucu açıkla. Yeni görev verme.' if change == 'explain_only' else 'Nasıl ilerleyelim?'
    assert plan_evidence_refresh(state, message) is None
