"""Proposal-driven production chain and adversarial preview boundaries, no AI."""
from copy import deepcopy
import json
from unittest.mock import patch

import pandas as pd
import pytest

from backend.app import database
from backend.app.mentor_grounded_reply import compile_reply
from backend.app.mentor_local_progress_service import plan_preview_continuation
from backend.app.mentor_preview_evidence_service import missing_preview_rows, preview_summary
from backend.app.mentor_research_service import (
    GroundedResearchPlan, GroundedResearchDecision, expand_research_decision,
    generate_research_reply, inspection_signature, prepare_research_context, validate_turn,
)
from backend.app.mentor_research_store import save_research_state, load_research_state
from backend.benchmarks.run_mentor_connected_followup import CASES, execute_inspection, main, recorded_cell, run_case


@pytest.fixture(autouse=True)
def memory(tmp_path,monkeypatch):
    monkeypatch.setattr(database,'DATABASE_PATH',tmp_path/'connected.sqlite')
    database.init_db()


def preview_state():
    df=pd.DataFrame({'value':[None]*5,'flag':[True,False,False,True,False],
                     'other':[1,2,3,4,5]})
    code="df.loc[df['value'].isna()].head(5)"
    cell=recorded_cell('preview',code,df,'value','v1',10000)
    notebook={'notebook_id':'n1','dataset_kind':'working','configured_development_rows':10000,
              'current_input_version':'v1','latest_cell':cell,'recent_cells':[],
              'available_columns':list(df.columns)}
    state=prepare_research_context(notebook,'value sonucunu incele')
    state['definition_availability']={'focus_column':'value','status':'unavailable'}
    state['response_language']='tr'
    return notebook,state


@pytest.mark.parametrize('case',list(CASES))
def test_actual_proposals_drive_subsequent_outputs_across_three_schemas(case):
    with patch('backend.app.mentor_research_service.get_ai_runtime') as runtime, \
         patch('backend.app.mentor_research_service.guarded_responses_parse') as provider:
        report=run_case(case)
    runtime.assert_not_called();provider.assert_not_called()
    assert report['passed'] and all(report['checks'].values())
    assert [turn['proposal_executed'] for turn in report['turns']]==[True,True,False]
    assert [turn['validation']['policy'] for turn in report['turns']]==[
        'missing_examples_v1','preview_distribution_v1','preview_review_v1']
    for index in (1,2):
        assert report['turns'][index]['evidence_snapshot']['latest_cell']['code']==report['turns'][index-1]['validation']['local_proposal']['next_action']['code']
    assert 'gösterilen 5 örnek' in report['turns'][1]['reply']
    assert 'true` (2)' in report['turns'][1]['reply'] and 'false` (3)' in report['turns'][1]['reply']
    assert '5000' not in report['turns'][1]['reply']  # five-row observations are not a 5k distribution
    assert '3333' in report['turns'][2]['reply'] and '1667' in report['turns'][2]['reply']
    assert not report['beginner_usability_tested'] and not report['live_model_quality_tested']


def test_completed_default_head_is_not_left_as_a_pending_task():
    notebook,state=preview_state()
    state['proposals']=[{'kind':'inspect','code':"df[df['value'].isna()].head()",'instruction':'Old preview task','status':'proposed'}]
    state['open_questions']=['Old preview task']
    updated=prepare_research_context(notebook,'Sonraki tek adım?',state)
    assert updated['proposals'][0]['status']=='observed'
    assert 'Old preview task' not in updated['open_questions']
    assert inspection_signature("df[df['value'].isna()].head()") == inspection_signature("df.loc[df['value'].isna()].head(5)")
    assert plan_preview_continuation(updated,'Sonraki tek adım?')['next_action']['code'].endswith('value_counts(dropna=False)')


def test_boolean_candidate_has_no_inferred_business_semantics():
    _,state=preview_state()
    plan=plan_preview_continuation(state,'Sonraki tek adım?')
    assert "'flag'" in plan['next_action']['code']
    compiled,errors=compile_reply(GroundedResearchPlan(next_action=None,evidence_ids=state['current_evidence_ids'][:1]),state,'Sonucu açıkla')
    assert not errors
    text=' '.join(claim.text for claim in compiled.claims)
    assert 'true` (2)' in text and 'false` (3)' in text
    assert 'iptal' not in text and 'cihaz' not in text


@pytest.mark.parametrize('language,message,word',[
    ('tr','Sonraki tek adım?','gösterilen 5 örnek'),
    ('en','What is the next step?','5 displayed example'),
    ('nl','Wat is de volgende stap?','5 getoonde voorbeeld'),
])
def test_preview_summary_and_next_step_respect_the_requested_language(language,message,word):
    _,state=preview_state();state['response_language']=language
    plan=plan_preview_continuation(state,message)
    turn,errors=compile_reply(expand_research_decision(GroundedResearchDecision.model_validate(plan),state),state,message)
    assert not errors and not validate_turn(turn,state,message)
    assert word in ' '.join(claim.text for claim in turn.claims)


@pytest.mark.parametrize('values',[[0,1,0,1,0],['True','False','False','True','False']])
def test_binary_looking_values_are_not_assumed_to_be_booleans(values):
    _,state=preview_state()
    for row,value in zip(state['observations'][0]['preview_rows'],values):row['flag']=value
    assert plan_preview_continuation(state,'Sonraki tek adım?') is None
    assert plan_preview_continuation(state,'flag sütununun dağılımıyla devam edelim.') is not None


def test_ambiguous_candidates_require_explicit_choice():
    _,state=preview_state()
    for row in state['observations'][0]['preview_rows']:
        row['other']=False
    assert plan_preview_continuation(state,'Sonraki tek adım?') is None
    chosen=plan_preview_continuation(state,'other dağılımıyla devam edelim.')
    assert "'other'" in chosen['next_action']['code']


@pytest.mark.parametrize('change',['no_rows','contradiction','stale','unknown_version','wrong_focus','already_done','pending','unknown_helper'])
def test_no_distribution_is_invented_without_current_unambiguous_evidence(change):
    _,state=preview_state();latest=state['observations'][0]
    if change=='no_rows':latest['preview_rows']=[]
    elif change=='contradiction':latest['preview_rows'][0]['value']=7
    elif change=='stale':latest['stale_scope']=True
    elif change=='unknown_version':latest['version_verified']=False
    elif change=='wrong_focus':state['focus_column']='other'
    elif change=='pending':state['proposals']=[{'kind':'inspect','status':'proposed'}]
    elif change=='unknown_helper':state['available_columns']=['value']
    else:
        old=deepcopy(latest);old['id']='old-distribution'
        old['analysis_contract'].update(operation='distribution',measured_columns=['flag'])
        state['observations'].append(old)
    assert plan_preview_continuation(state,'Sonraki tek adım?') is None


def test_contradictory_rows_cannot_support_a_grounded_preview():
    _,state=preview_state();state['observations'][0]['preview_rows'][0]['value']=7
    plan=GroundedResearchPlan(next_action=None,evidence_ids=state['current_evidence_ids'][:1])
    compiled,errors=compile_reply(plan,state,'Sonucu açıkla')
    assert compiled is None and any('contradict' in error for error in errors)
    assert preview_summary(state['observations'][0],'tr') is None


def test_contradictory_preview_stops_before_spending_any_ai_quota():
    notebook,_=preview_state()
    notebook['latest_cell']['last_execution']['preview_rows'][0]['value']=7
    context={'workspace_id':'contradiction','artifacts':{'selected_notebook':notebook},
             'dataset_profile_summary':{'columns':['value','flag','other']}}
    with patch('backend.app.mentor_research_service.get_ai_runtime') as runtime, \
         patch('backend.app.mentor_research_service.guarded_responses_parse') as provider:
        generate_research_reply(context,'Sonraki tek adım?',[])
    runtime.assert_not_called();provider.assert_not_called()
    assert not load_research_state('contradiction','n1')['last_validation']['accepted']


def test_ambiguous_offline_probe_stops_without_a_provider_call():
    notebook,state=preview_state()
    for row in state['observations'][0]['preview_rows']:row['other']=False
    notebook['latest_cell']['last_execution']['preview_rows']=state['observations'][0]['preview_rows']
    context={'workspace_id':'ambiguous','artifacts':{'selected_notebook':notebook},
             'dataset_profile_summary':{'columns':['value','flag','other']}}
    save_research_state('ambiguous','n1',state)
    with patch('backend.app.mentor_research_service.get_ai_runtime') as runtime:
        generate_research_reply(context,'Sonraki tek adım?',[],allow_provider=False)
    runtime.assert_not_called()
    assert not load_research_state('ambiguous','n1')['last_validation']['accepted']


@pytest.mark.parametrize('code',[
    "df['value'] = 0", "__import__('os').getcwd()", "df.head(5)",
    "df.loc[df['other'].isna()].head(5)", "df.loc[df['value'].isna()].head(99)",
])
def test_probe_interpreter_rejects_every_shape_outside_its_contract(code):
    with pytest.raises(ValueError):execute_inspection(pd.DataFrame({'value':[None],'other':[1]}),code,'value')


def test_connected_cli_restores_database_and_reports_both_scope_and_limits(tmp_path):
    original=database.DATABASE_PATH
    assert main(['--case','sensors','--output-dir',str(tmp_path/'reports')])==0
    assert database.DATABASE_PATH==original
    report=json.loads(next((tmp_path/'reports').glob('*/report.json')).read_text(encoding='utf-8'))
    assert report['passed'] and report['results'][0]['provider_calls']==0
    assert report['results'][0]['project_completion_proven'] is False


def test_unsupported_execution_is_a_recorded_blocker_not_a_substituted_result():
    with patch('backend.benchmarks.run_mentor_connected_followup.execute_inspection',side_effect=ValueError('outside the approved shape')):
        report=run_case('sensors')
    assert not report['passed'] and len(report['turns'])==1
    assert report['turns'][0]['proposal_executed'] is False
    assert report['turns'][0]['execution_error']=='outside the approved shape'
