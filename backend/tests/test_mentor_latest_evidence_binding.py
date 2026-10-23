"""Synthetic regression for a related decision omitting an unrelated latest cell.

All field names, values and expressions below are invented test data. Uploaded
learner diagnostics are not fixtures in the repository.
"""
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.app import database
from backend.app.mentor_grounded_reply import compile_reply
from backend.app.mentor_research_service import (
    GroundedResearchDecision, GroundedResearchPlan, InvalidResearchDecision,
    expand_research_decision, generate_research_reply, prepare_research_context,
    render_turn, validate_turn,
)
from backend.app.mentor_research_store import load_research_state


def example_context():
    codes = [
        ("latest-helper", "df.loc[df['indicator'] == 1, 'category'].isna().sum()", '3'),
        ("target-count", "df['measurement'].isna().sum()", '17'),
        ("unsupported", "df['measurement'].sum()", '25'),
        ("related-helper", "df.loc[df['measurement'].notna(), 'category'].value_counts()", 'example_label    2'),
    ]
    cells = [{'cell_id': name, 'code': code, 'section_title': 'measurement',
              'last_execution': {'success': True, 'output': output,
                                 'input_row_count': 42, 'dataset_kind': 'working',
                                 'executed_at': f'2026-01-01T10:0{9-index}:00'}}
             for index, (name, code, output) in enumerate(codes)]
    return {'workspace_id': 'synthetic-binding', 'ui_context': {'language': 'tr'},
            'dataset_profile_summary': {'columns': ['measurement', 'indicator', 'category']},
            'artifacts': {'selected_notebook': {'notebook_id': 'n1', 'dataset_kind': 'working',
                'configured_development_rows': 42, 'latest_cell': cells[0], 'recent_cells': cells}}}


@pytest.fixture
def example():
    notebook = example_context()['artifacts']['selected_notebook']
    result = prepare_research_context(notebook, 'measurement incelemesine devam edelim.')
    result['response_language'] = 'tr'
    return result


def related_decision(state):
    ref = next(x['id'] for x in state['observations'] if x['cell_id'] == 'related-helper')
    return GroundedResearchDecision(next_action={'kind': 'clarify', 'code': None}, evidence_ids=[ref])


def test_related_decision_keeps_latest_helper_fact_without_requiring_model_to_echo_id(example):
    decision = related_decision(example)
    raw = decision.model_dump()
    old = GroundedResearchPlan(next_action=None, evidence_ids=decision.evidence_ids)
    _, old_errors = compile_reply(old, example, 'Devam edelim, kod verme.')
    assert old_errors == ['The latest executed observation must be addressed']
    expanded = expand_research_decision(decision, example)
    assert decision.model_dump() == raw
    assert expanded.evidence_ids == [example['current_evidence_ids'][0], *raw['evidence_ids']]
    turn, errors = compile_reply(expanded, example, 'Devam edelim, kod verme.')
    assert not errors and not validate_turn(turn, example, 'Devam edelim, kod verme.')
    reply = render_turn(turn, example, 'Devam edelim, kod verme.')
    assert 'category' in turn.answer and '**3**' in turn.answer
    assert 'o satırlar için aynı sonucu çıkarmayız' in turn.answer
    assert turn.next_action.focus_column == 'measurement'
    assert turn.next_action.kind == 'clarify' and turn.next_action.code is None
    assert 'veri sürümü kaydedilmemiş' in reply and '```' not in reply


def test_binding_keeps_unsupported_selected_evidence_rejected(example):
    refs = [x['id'] for x in example['observations'] if x['cell_id'] in {'unsupported', 'target-count'}]
    raw = GroundedResearchDecision(next_action={'kind': 'inspect', 'code': "df['measurement'].head()"}, evidence_ids=refs)
    _, errors = compile_reply(expand_research_decision(raw, example), example, 'Devam edelim.')
    assert 'Selected expression/output has no supported observation contract' in errors
    assert 'The latest executed observation must be addressed' not in errors


@pytest.mark.parametrize('change,expected', [
    ('unknown', 'Select only current evidence IDs'),
    ('stale', 'Selected observation is failed or stale'),
    ('failed', 'Selected observation is failed or stale'),
    ('unsupported_latest', 'Selected expression/output has no supported observation contract'),
])
def test_binding_does_not_bypass_other_evidence_checks(example, change, expected):
    decision = related_decision(example)
    anchor = next(x for x in example['observations'] if x['id'] == example['current_evidence_ids'][0])
    if change == 'unknown': decision.evidence_ids = ['made-up']
    elif change == 'stale': anchor['stale_scope'] = True
    elif change == 'failed': anchor['success'] = False
    else: anchor['analysis_contract']['supported'] = False
    plan = expand_research_decision(decision, example)
    _, errors = compile_reply(plan, example, 'Devam edelim.')
    assert any(expected in error for error in errors)


def test_binding_never_drops_selected_references_to_fit_budget(example):
    decision = GroundedResearchDecision(next_action=None, evidence_ids=example['current_evidence_ids'][1:4])
    with pytest.raises(InvalidResearchDecision, match='at most two additional'):
        expand_research_decision(decision, example)
    for refs in ([], ['unknown']):
        plan = expand_research_decision(GroundedResearchDecision(next_action=None, evidence_ids=refs), example)
        assert compile_reply(plan, example, '')[1]


def test_production_uses_one_controlled_response_and_records_binding_separately(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'mentor.sqlite')
    database.init_db()
    context = example_context()

    def respond(*args, **kwargs):
        request = json.loads(kwargs['input'])
        relevant = next(x for x in request['current_observations'] if x['cell_id'] == 'related-helper')
        assert request['latest_observation_id'] != relevant['id']
        return SimpleNamespace(output_parsed=GroundedResearchDecision(
            next_action={'kind': 'clarify', 'code': None}, evidence_ids=[relevant['id']]))

    with patch('backend.app.mentor_research_service.get_ai_runtime',
               return_value=SimpleNamespace(client=None, provider='groq', model='test')), \
         patch('backend.app.mentor_research_service.guarded_responses_parse', side_effect=respond) as provider:
        reply = generate_research_reply(context, 'measurement incelemesine devam edelim. Kodu verme.', [])
    assert provider.call_count == 1
    saved = load_research_state('synthetic-binding', 'n1')
    validation = saved['last_validation']
    assert validation['accepted'] and len(validation['model_attempts']) == 1
    attempt = validation['model_attempts'][0]
    assert attempt['evidence_binding']['added_latest_ids'] == saved['current_evidence_ids'][:1]
    assert attempt['raw_plan']['evidence_ids'] == attempt['evidence_binding']['selected_ids']
    assert saved['proposals'][-1]['focus_column'] == 'measurement'
    assert 'category' in reply and 'veri sürümü kaydedilmemiş' in reply
    assert 'denetiminden geçmedi' not in reply
