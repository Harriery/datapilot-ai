"""Real report(8) failure and compact-wire production path; no live AI calls."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from openai import BadRequestError
import pytest
from pydantic import ValidationError

from backend.app import database
from backend.app.mentor_research_service import (
    GroundedResearchDecision, GroundedInspectionDecision, generate_research_reply, prepare_research_context,
)
from backend.app.mentor_research_store import load_research_state, save_research_state
from backend.benchmarks.run_mentor_research_acceptance import CASES, snapshots
from backend.benchmarks.run_mentor_clarification_followup import validate_source_report


@pytest.fixture(autouse=True)
def memory(tmp_path,monkeypatch):
    # Exercise wire parsing even where the production local policy could act.
    monkeypatch.setattr('backend.app.mentor_research_service.plan_missing_preview',lambda *args: None)
    monkeypatch.setattr(database,'DATABASE_PATH',tmp_path/'wire.sqlite')
    database.init_db()


@pytest.fixture
def actual():
    return json.loads((Path(__file__).parent/'fixtures/research_decision_wire_failure.json').read_text(encoding='utf-8'))


def runtime():
    return SimpleNamespace(client=None,provider='groq',model='test')


def test_wire_has_one_evidence_list_and_no_derived_fields():
    schema=GroundedResearchDecision.model_json_schema()
    assert set(schema['required'])=={'next_action','evidence_ids'}
    action=schema['$defs']['ResearchDecisionAction']
    assert set(action['properties'])==set(action['required'])=={'kind','code'}
    assert schema['additionalProperties'] is action['additionalProperties'] is False


def test_report8_original_document_remains_rejected_and_exactly_preserved(actual):
    raw=json.loads(actual['failed_generation'])
    assert 'evidence_ids' not in raw['next_action']
    # JSON display escapes are not a Python syntax error after decoding.
    ast.parse(raw['next_action']['code'])
    with pytest.raises(ValidationError):GroundedResearchDecision.model_validate(raw)
    ctx={'workspace_id':'actual-wire','artifacts':{'selected_notebook':actual['evidence_snapshot']},
         'dataset_profile_summary':{'columns':actual['evidence_snapshot']['available_columns']}}
    error=BadRequestError('recorded schema error',response=httpx.Response(400,request=httpx.Request('POST','https://example.test/responses')),
                          body={'error':{'code':'json_validate_failed','message':'schema mismatch','failed_generation':actual['failed_generation']}})
    with patch('backend.app.mentor_research_service.get_ai_runtime',return_value=runtime()), \
         patch('backend.app.mentor_research_service.guarded_responses_parse',side_effect=error) as model:
        reply=generate_research_reply(ctx,actual['message'],[],max_attempts=1)
    assert model.call_count==1
    saved=load_research_state('actual-wire','n1')
    assert not saved['last_validation']['accepted']
    assert saved['last_validation']['model_attempts'][0]['provider_recovery']['failed_generation']==actual['failed_generation']
    assert not saved['proposals']
    assert 'denetiminden geçmedi' in reply


def test_exact_report8_code_needs_no_repair_under_the_minimal_contract(actual):
    original=json.loads(actual['failed_generation'])
    n=actual['evidence_snapshot']
    ctx={'workspace_id':'same-real-code','artifacts':{'selected_notebook':n},
         'dataset_profile_summary':{'columns':n['available_columns']}}
    decision=GroundedResearchDecision.model_validate({
        'next_action':{'kind':'inspect','code':original['next_action']['code']},
        'evidence_ids':original['evidence_ids'],
    })
    with patch('backend.app.mentor_research_service.get_ai_runtime',return_value=runtime()), \
         patch('backend.app.mentor_research_service.guarded_responses_parse',return_value=SimpleNamespace(output_parsed=decision)) as model:
        reply=generate_research_reply(ctx,actual['message'],[],max_attempts=1)
    assert model.call_count==1
    saved=load_research_state('same-real-code','n1')
    assert saved['last_validation']['accepted']
    assert saved['proposals'][-1]['code']==original['next_action']['code']
    assert saved['proposals'][-1]['columns']==['temperature']
    assert saved['proposals'][-1]['evidence_ids']==original['evidence_ids']
    assert 'ilk 5 satırı görüntüle' in reply


def test_complete_compact_provider_error_document_is_validated_without_an_extra_call(actual):
    original=json.loads(actual['failed_generation'])
    n=actual['evidence_snapshot']
    ctx={'workspace_id':'recover-wire','artifacts':{'selected_notebook':n},
         'dataset_profile_summary':{'columns':n['available_columns']}}
    raw={'next_action':{'kind':'inspect','code':original['next_action']['code']},'evidence_ids':original['evidence_ids']}
    error=BadRequestError('provider schema validation',response=httpx.Response(400,request=httpx.Request('POST','https://example.test/responses')),
                         body={'error':{'code':'json_validate_failed','message':'schema mismatch','failed_generation':json.dumps(raw)}})
    with patch('backend.app.mentor_research_service.get_ai_runtime',return_value=runtime()), \
         patch('backend.app.mentor_research_service.guarded_responses_parse',side_effect=error) as model:
        reply=generate_research_reply(ctx,actual['message'],[],max_attempts=1)
    assert model.call_count==1
    saved=load_research_state('recover-wire','n1')['last_validation']
    assert saved['accepted']
    assert saved['model_attempts'][0]['raw_plan']==raw
    assert saved['model_attempts'][0]['provider_recovery']['http_status']==400
    assert 'ilk 5 satırı görüntüle' in reply


@pytest.mark.parametrize('case',list(CASES))
@pytest.mark.parametrize('language',['tr','en','nl'])
def test_minimal_wire_reaches_a_missing_row_inspection_across_schemas_and_languages(case,language):
    context,message=next(snapshots(case));target=CASES[case][0]
    context['ui_context']={'language':language}
    notebook=context['artifacts']['selected_notebook']
    state=prepare_research_context(notebook,message)
    state['proposals']=[{'kind':'clarify','focus_column':target}]
    save_research_state(context['workspace_id'],'n1',state)
    message={'tr':'Bilmiyorum, veri sözlüğüm yok. Kod vermeden yönlendir.',
             'en':"I don't have a data dictionary. Guide me without code.",
             'nl':'Ik heb geen gegevenswoordenboek. Help me zonder code.'}[language]
    def respond(*args,**kwargs):
        assert kwargs['text_format'] is GroundedInspectionDecision
        request=json.loads(kwargs['input'])
        assert request['definition_availability']['status']=='unavailable'
        raw={'next_action':{'kind':'inspect','code':f"df[df['{target}'].isna()].head()"},
             'evidence_ids':[request['current_observations'][0]['id']]}
        # Cross the actual JSON/Pydantic boundary, rather than construct an
        # expanded action with fields the real provider might forget.
        return SimpleNamespace(output_parsed=kwargs['text_format'].model_validate_json(json.dumps(raw)))
    with patch('backend.app.mentor_research_service.get_ai_runtime',return_value=runtime()), \
         patch('backend.app.mentor_research_service.guarded_responses_parse',side_effect=respond) as model:
        reply=generate_research_reply(context,message,[],max_attempts=1)
    assert model.call_count==1
    saved=load_research_state(context['workspace_id'],'n1')
    assert saved['last_validation']['accepted']
    action=saved['proposals'][-1]
    assert action['focus_column']==target and action['columns']==[target]
    assert action['evidence_ids']==saved['current_evidence_ids'][:1]
    assert set(saved['last_validation']['model_attempts'][0]['raw_plan']['next_action'])=={'kind','code'}
    assert 'df[' not in reply
    assert {'tr':'ilk 5 satırı görüntüle','en':'show the first 5 rows','nl':'toon de eerste 5 rijen'}[language] in reply


@pytest.mark.parametrize('code',[
    'df[df[\\"temperature\\"].isna()].head()',
    "df.loc[df['temperature'].isna(), 'invented_field'].head()",
    "df['temperature'] = 0",
    "df['temperature'].isna().sum()",
    "df['offline'].head()",
    None,
])
def test_compact_wire_does_not_weaken_existing_code_and_focus_checks(actual,code):
    n=actual['evidence_snapshot']
    ctx={'workspace_id':'invalid-wire','artifacts':{'selected_notebook':n},'dataset_profile_summary':{'columns':n['available_columns']}}
    def respond(*args,**kwargs):
        ref=json.loads(kwargs['input'])['current_observations'][0]['id']
        return SimpleNamespace(output_parsed=GroundedResearchDecision.model_validate({'next_action':{'kind':'inspect','code':code},'evidence_ids':[ref]}))
    with patch('backend.app.mentor_research_service.get_ai_runtime',return_value=runtime()), \
         patch('backend.app.mentor_research_service.guarded_responses_parse',side_effect=respond):
        generate_research_reply(ctx,'temperature için kod vermeden yönlendir',[],max_attempts=1)
    assert not load_research_state('invalid-wire','n1')['last_validation']['accepted']


def test_new_initial_clarification_report_is_reusable_without_ai(tmp_path):
    data=json.loads((Path(__file__).parent/'fixtures/research_clarification_source.json').read_text(encoding='utf-8'))
    raw=data['results'][0]['turns'][0]['validation']['model_attempts'][-1]['raw_plan']
    raw['next_action']={'kind':'clarify','code':None}
    path=tmp_path/'compact-source.json';path.write_text(json.dumps(data),encoding='utf-8')
    _,state,history=validate_source_report(path,'sensors')
    assert state['proposals'][0]['kind']=='clarify'
    assert 'veri sözlüğündeki tanımını' in history[-1]['content']


@pytest.mark.parametrize('kind,code,refs',[
    ('inspect',"df[df['temperature'].isna()].head()",['invented-id']),
    ('clarify',"df['temperature'].head()",None),
])
def test_unknown_evidence_and_code_attached_to_clarification_are_rejected(actual,kind,code,refs):
    n=actual['evidence_snapshot']
    ctx={'workspace_id':'bad-refs','artifacts':{'selected_notebook':n},'dataset_profile_summary':{'columns':n['available_columns']}}
    def respond(*args,**kwargs):
        ref=json.loads(kwargs['input'])['current_observations'][0]['id']
        return SimpleNamespace(output_parsed=GroundedResearchDecision.model_validate({'next_action':{'kind':kind,'code':code},'evidence_ids':refs or [ref]}))
    with patch('backend.app.mentor_research_service.get_ai_runtime',return_value=runtime()), \
         patch('backend.app.mentor_research_service.guarded_responses_parse',side_effect=respond):
        generate_research_reply(ctx,'temperature için yönlendir',[],max_attempts=1)
    assert not load_research_state('bad-refs','n1')['last_validation']['accepted']
