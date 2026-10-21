"""Answered clarifications leave the queue and cannot recur in the wire schema."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from backend.app.mentor_research_service import (
    GroundedResearchDecision, GroundedInspectionDecision, build_research_request,
    decision_schema, prepare_research_context,
)
from backend.benchmarks.run_mentor_clarification_followup import validate_source_report, run_followup


@pytest.fixture
def source():
    return Path(__file__).parent/'fixtures/research_clarification_source.json'


def answered(source):
    context,state,history=validate_source_report(source,'sensors')
    notebook=context['artifacts']['selected_notebook']
    return context,prepare_research_context(notebook,'Bilmiyorum, veri sözlüğüm yok.',state),history


def test_real_report9_choice_is_absent_from_the_answered_question_schema(source):
    _,state,_=answered(source)
    raw=json.loads((Path(__file__).parent/'fixtures/research_answered_clarification.json').read_text(encoding='utf-8'))['raw_plan']
    assert decision_schema(state) is GroundedInspectionDecision
    with pytest.raises(ValidationError):decision_schema(state).model_validate(raw)
    schema=decision_schema(state).model_json_schema()
    assert schema['$defs']['InspectionDecisionAction']['properties']['kind']['const']=='inspect'


def test_answer_is_recorded_once_and_old_question_is_not_still_pending(source):
    context,state,history=validate_source_report(source,'sensors')
    old=state['proposals'][0]['instruction']
    state['open_questions'].append('An unrelated research question')
    notebook=context['artifacts']['selected_notebook']
    updated=prepare_research_context(notebook,'Bilmiyorum.',state)
    assert updated['proposals'][0]['status']=='answered_unavailable'
    assert old not in updated['open_questions']
    assert 'An unrelated research question' in updated['open_questions']
    again=prepare_research_context(notebook,'Devam edelim.',updated)
    assert again['proposals']==updated['proposals']
    assert old not in again['open_questions']
    request=build_research_request(context,again,'Devam edelim.',history)
    assert request['allowed_action_kinds']==['inspect']
    assert request['previous_proposals'][0]['status']=='answered_unavailable'


def test_existing_unavailable_state_repairs_old_pending_queue_without_reasking(source):
    context,state,_=validate_source_report(source,'sensors')
    state['definition_availability']={'focus_column':'temperature','status':'unavailable'}
    updated=prepare_research_context(context['artifacts']['selected_notebook'],'Sonucu gördün mü?',state)
    assert updated['proposals'][0]['status']=='answered_unavailable'
    assert state['proposals'][0]['instruction'] not in updated['open_questions']
    # Reading/upgrading a state does not mutate the caller's old snapshot.
    assert state['proposals'][0]['status']=='proposed'


def test_source_discovery_and_focus_switch_reopen_only_the_appropriate_choices(source):
    context,state,_=answered(source)
    notebook=context['artifacts']['selected_notebook']
    found=prepare_research_context(notebook,'Veri sözlüğünü buldum.',state)
    assert found['definition_availability']['status']=='available'
    assert decision_schema(found) is GroundedResearchDecision
    switched=prepare_research_context(notebook,'offline sütununa geçelim',state)
    assert switched['focus_column']=='offline' and 'definition_availability' not in switched
    assert decision_schema(switched) is GroundedResearchDecision


def test_schema_still_allows_no_new_task_for_explanation_or_insufficient_evidence(source):
    _,state,_=answered(source)
    result=decision_schema(state).model_validate({'next_action':None,'evidence_ids':state['current_evidence_ids'][:1]})
    assert result.next_action is None


def test_followup_uses_context_schema_and_records_resolved_state(source,tmp_path,monkeypatch):
    # The provider path still needs coverage when the local policy has no step.
    monkeypatch.setattr('backend.app.mentor_research_service.plan_missing_preview',lambda *args: None)
    def respond(*args,**kwargs):
        payload=json.loads(kwargs['input'])
        assert kwargs['text_format'] is GroundedInspectionDecision
        assert payload['allowed_action_kinds']==['inspect']
        assert payload['previous_proposals'][0]['status']=='answered_unavailable'
        assert 'veri sözlüğündeki tanımını' not in ' '.join(payload['open_questions'])
        raw={'next_action':{'kind':'inspect','code':"df[df['temperature'].isna()].head(5)"},
             'evidence_ids':[payload['current_observations'][0]['id']]}
        return SimpleNamespace(output_parsed=kwargs['text_format'].model_validate_json(json.dumps(raw)))
    with patch('backend.app.mentor_research_service.get_ai_runtime',return_value=SimpleNamespace(provider='groq',model='test',client=None)), \
         patch('backend.app.mentor_research_service.guarded_responses_parse',side_effect=respond) as model:
        report,_=run_followup(source,'sensors',tmp_path,live=True)
    assert model.call_count==1 and report['progress_passed']
    assert report['validation']['runtime']['decision_schema']=='GroundedInspectionDecision'
    assert report['research_context']['proposal_statuses'][0]['status']=='answered_unavailable'
