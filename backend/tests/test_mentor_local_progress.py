"""The real production mentor proposes a justified inspection without an AI.

No provider reply is stubbed as successful. Generated code is never executed by
the production path. One fixed local-policy expression is evaluated in the test
against synthetic rows to verify its selection, independently of the report.
"""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from backend.app import database
from backend.app.mentor_local_progress_service import plan_missing_preview
from backend.app.mentor_research_service import generate_research_reply, prepare_research_context
from backend.app.mentor_research_store import load_research_state, save_research_state
from backend.benchmarks.run_mentor_clarification_followup import run_followup, progression_checks
from backend.benchmarks.run_mentor_research_acceptance import CASES, snapshots


@pytest.fixture(autouse=True)
def memory(tmp_path,monkeypatch):
    monkeypatch.setattr(database,'DATABASE_PATH',tmp_path/'local.sqlite')
    database.init_db()


def initial(case='sensors'):
    context,message=next(snapshots(case))
    state=prepare_research_context(context['artifacts']['selected_notebook'],message)
    state['definition_availability']={'focus_column':CASES[case][0],'status':'unavailable'}
    return context,state


def test_report10_accepted_null_still_does_not_count_as_progress():
    r=json.loads((Path(__file__).parent/'fixtures/research_no_progress.json').read_text(encoding='utf-8'))
    checks=progression_checks(r['validation'],{'artifacts':{'selected_notebook':r['evidence_snapshot']}})
    assert checks['structurally_accepted'] is True
    assert checks['proposes_an_inspection'] is False
    assert not all(checks.values())


@pytest.mark.parametrize('case',list(CASES))
@pytest.mark.parametrize('language,message',[
    ('tr','Bilmiyorum, veri sözlüğüm yok. Kod vermeden yönlendir.'),
    ('en',"I don't have a data dictionary. Guide me without code."),
    ('nl','Ik heb geen gegevenswoordenboek. Help me zonder code.'),
])
def test_production_local_policy_advances_without_provider_or_fake_model_attempt(case,language,message):
    context,state=initial(case)
    context['ui_context']={'language':language}
    save_research_state(context['workspace_id'],'n1',state)
    with patch('backend.app.mentor_research_service.get_ai_runtime') as runtime, \
         patch('backend.app.mentor_research_service.guarded_responses_parse') as provider:
        reply=generate_research_reply(context,message,[],max_attempts=1)
    runtime.assert_not_called();provider.assert_not_called()
    saved=load_research_state(context['workspace_id'],'n1')
    v=saved['last_validation']
    assert v['accepted'] and v['origin']=='local_progress_policy'
    assert v['provider_calls']==0 and v['model_attempts']==[]
    assert all(progression_checks(v,context).values())
    assert saved['proposals'][-1]['focus_column']==CASES[case][0]
    assert 'df[' not in reply and 'df.loc' not in reply
    assert {'tr':'ilk 5 satırı görüntüle','en':'show the first 5 rows','nl':'toon de eerste 5 rijen'}[language] in reply


@pytest.mark.parametrize('change',[
    'zero','unknown_version','stale','unknown_scope','filtered_count','helper_count',
    'definition_available','pending_inspection','already_previewed',
])
def test_policy_does_not_invent_a_step_outside_its_evidence_conditions(change):
    _,state=initial()
    latest=state['observations'][0]
    if change=='zero':latest['analysis_contract']['result']=0
    elif change=='unknown_version':latest['version_verified']=False
    elif change=='stale':latest['stale_scope']=True
    elif change=='unknown_scope':latest['input_rows']=None
    elif change=='filtered_count':latest['analysis_contract']['row_predicate']={'op':'eq','column':'offline','value':1}
    elif change=='helper_count':latest['analysis_contract']['measured_columns']=['offline']
    elif change=='definition_available':state['definition_availability']['status']='available'
    elif change=='pending_inspection':state['proposals']=[{'kind':'inspect','status':'proposed'}]
    else:
        old=deepcopy(latest);old['id']='earlier-preview'
        old['analysis_contract'].update(operation='preview_head',row_predicate={'op':'missing','column':'temperature'})
        state['observations'].append(old)
    assert plan_missing_preview(state,'Kod vermeden devam edelim.') is None


@pytest.mark.parametrize('message',[
    'Bu sonuç ne demek?', 'Yeni görev verme, sadece açıkla.',
    'Explain this result. No new task.', 'Geen nieuwe opdracht, leg dit uit.',
])
def test_policy_respects_explanation_only_requests(message):
    _,state=initial()
    assert plan_missing_preview(state,message) is None


def test_preview_selects_only_missing_rows_and_cannot_interpolate_a_column_as_code():
    _,state=initial()
    target="value['quoted']\\name"
    state['focus_column']=target
    state['definition_availability']['focus_column']=target
    state['observations'][0]['analysis_contract']['measured_columns']=[target]
    plan=plan_missing_preview(state,'Devam edelim.')
    df=pd.DataFrame({target:[None,1,None,2,None,None,None,None], 'other':list(range(8))})
    original=df.copy(deep=True)
    # Only the deterministic local policy is evaluated here, never model code.
    result=eval(compile(plan['next_action']['code'],'local-policy-test','eval'),{'__builtins__':{}},{'df':df})
    assert result['other'].tolist()==[0,2,4,5,6]
    assert result[target].isna().all()
    pd.testing.assert_frame_equal(df,original)


def test_real_followup_runner_reports_local_progress_without_claiming_live_model_success(tmp_path):
    source=Path(__file__).parent/'fixtures/research_clarification_source.json'
    with patch('backend.app.mentor_research_service.get_ai_runtime') as runtime, \
         patch('backend.app.mentor_research_service.guarded_responses_parse') as provider:
        report,path=run_followup(source,'sensors',tmp_path,live=True)
    runtime.assert_not_called();provider.assert_not_called()
    assert report['progress_passed'] and report['provider_calls']==0
    assert report['guidance_origin']=='local_progress_policy'
    assert report['mode']=='local_clarification_followup'
    assert report['proposal_executed'] is report['project_completion_proven'] is False
    assert report['research_context']['proposal_statuses'][0]['status']=='answered_unavailable'
    assert json.loads(path.read_text(encoding='utf-8'))['validation']['model_attempts']==[]
