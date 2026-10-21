"""Population/measurement semantics, counterexamples, and recorded live regressions."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import pytest
from pydantic import ValidationError

from backend.app import database
from backend.app.mentor_observation_contract import expression_contract, observation_contract, observation_text
from backend.app.mentor_grounded_reply import compile_reply
from backend.app.mentor_research_service import GroundedResearchPlan, ResearchTurn, prepare_research_context, generate_research_reply, render_turn
from backend.app.mentor_research_store import load_research_state
from backend.benchmarks.run_mentor_research_acceptance import reusable_prefix


@pytest.fixture(autouse=True)
def memory(tmp_path, monkeypatch):
    monkeypatch.setattr(database,'DATABASE_PATH',tmp_path/'grounded.db')
    database.init_db()


def execution(code, output='0'):
    return observation_contract(code, {'success':True,'output':output})


@pytest.mark.parametrize('code', [
    'df.loc[df["flag"] == 1, "reason"].isna().sum()',
    'df[df["flag"] == 1]["reason"].isnull().sum()',
    'print(df.loc[df["flag"] == 1, "reason"].isna().sum())',
    'df.loc[df["flag"] == 1, ["reason"]].isna().sum()',
])
def test_measurement_and_selected_group_are_separate(code):
    c=execution(code)
    assert c['supported'] is True
    assert c['row_predicate']=={'op':'eq','column':'flag','value':1}
    assert c['measured_columns']==['reason']
    assert c['operation']=='missing_count'
    assert c['result']==0


def test_real_counterexample_zero_in_one_group_does_not_transfer_to_target_missing():
    df=pd.DataFrame({'target':[None,7,None,4],'flag':[0,1,1,0], 'reason':[None,'A','B',None]})
    actual=df.loc[df.flag==1,'reason'].isna().sum()
    wrong=df.loc[df.target.isna(),'reason'].isna().sum()
    assert actual==0 and wrong==1
    c=execution('df.loc[df["flag"] == 1, "reason"].isna().sum()',str(actual))
    assert c['row_predicate']['column']=='flag'
    assert 'target' not in observation_text(c)


def test_empty_group_and_nonempty_group_can_both_return_zero():
    df=pd.DataFrame({'flag':[0,0],'reason':[None,'A']})
    assert df.loc[df.flag==1,'reason'].isna().sum()==0
    c=execution('df.loc[df["flag"] == 1, "reason"].isna().sum()')
    assert c['result']==0
    assert 'selected_row_count' not in c


@pytest.mark.parametrize('code',[
    'df_alias["reason"].isna().sum()',
    'df.query("flag == 1")["reason"].isna().sum()',
    'df.loc[mask,"reason"].isna().sum()',
    'df.loc[df["flag"] == 1,"reason"].isna().sum(); df.dropna(inplace=True)',
    'df.loc[df["flag"] == 1,"reason"].isna().sum(axis=1)',
    'df.loc[df["flag"] == 1,"reason"].apply(external)',
    'df.groupby("flag")["reason"].count()',
    'df["reason"].value_counts(**options)',
    'df["reason"].head(-1)',
])
def test_unknown_expression_is_not_assumed_to_be_unfiltered_df(code):
    assert expression_contract(code).get('supported') is False


@pytest.mark.parametrize('text',['np.int64(0','0)','-1','0.0','True','0\n999','some text'])
def test_ambiguous_missing_count_is_not_a_measurement(text):
    assert execution('df["reason"].isna().sum()',text)['supported'] is False


@pytest.mark.parametrize('text',['0','np.int64(0)','int32(0)','reason    0\ndtype: int64'])
def test_recorded_scalar_and_single_column_series_counts(text):
    assert execution('df[["reason"]].isna().sum()',text)['result']==0


def test_nested_predicates_preserve_and_or_not_and_signed_literals():
    code='df.loc[((df["flag"] == 1) | (df["metric"] < -2)) & ~df["reason"].isna(), "target"].isna().sum()'
    c=execution(code,'3')
    p=c['row_predicate']
    assert p['op']=='and'
    assert p['args'][0]['op']=='or'
    assert p['args'][0]['args'][1]=={'op':'lt','column':'metric','value':-2}
    assert p['args'][1]=={'op':'not','arg':{'op':'missing','column':'reason'}}


def test_distribution_is_not_promoted_to_population_or_cause():
    c=execution('df.loc[df["target"].isna(), "metric"].value_counts()', 'metric\n-1    3\n 0    2\n...\nName: count, dtype: int64')
    assert c['row_predicate']=={'op':'missing','column':'target'}
    assert c['output_truncated'] is True
    assert 'result' not in c
    text=observation_text(c)
    assert 'dropna=False' in text
    assert 'kısaltıldı' in text


@pytest.fixture
def actual():
    return json.loads((Path(__file__).parent/'fixtures/research_group_confusion.json').read_text(encoding="utf-8"))


@pytest.mark.parametrize('case', ['sensors','retail','service'])
def test_all_actual_accepted_turns_are_recompiled_without_using_old_factual_prose(actual,case):
    old=next(x for x in actual['results'] if x['case']==case)
    with patch('backend.app.mentor_research_service.guarded_responses_parse') as provider:
        turns,history=reusable_prefix(case,old['turns'],4)
    provider.assert_not_called()
    assert len(turns)==4 and len(history)==8
    for turn in turns:
        assert turn['validation']['cached_display_recompiled'] is True
        assert turn['validation']['model_factual_prose_published'] is False
        assert turn['reply']!=old['turns'][turns.index(turn)]['reply']
    latest=turns[2]['reply']
    flag,reason={'sensors':('offline','status_reason'),'retail':('returned','return_reason'),'service':('closed','closure_reason')}[case]
    assert f'`{flag}` = `1`' in latest
    assert f'Ölçülen sütun: `{reason}`' in latest
    assert '**0**' in latest
    assert 'o satırlar için aynı sonucu çıkarmayız' in latest
    assert 'grubun boş olmadığını' in latest
    assert 'Sonraki tek adım' not in turns[3]['reply']


def test_original_wrong_prose_is_not_permitted_by_new_wire_protocol(actual):
    service=next(x for x in actual['results'] if x['case']=='service')
    raw=service['turns'][2]['validation']['model_attempts'][-1]['proposal']
    assert 'bu eksik kayıtların closure_reason alanının hiçbirinde' in raw['answer']
    with pytest.raises(ValidationError):
        GroundedResearchPlan.model_validate(raw)
    assert set(GroundedResearchPlan.model_json_schema()['properties'])=={'next_action','evidence_ids'}


def test_model_cannot_hide_latest_check_or_select_an_unknown_population(actual):
    t=actual['results'][0]['turns'][2]
    state=prepare_research_context(t['evidence_snapshot'],t['message'])
    for refs in [['made-up'],state['current_evidence_ids'][1:]]:
        _,errors=compile_reply(GroundedResearchPlan(next_action=None,evidence_ids=refs),state,t['message'])
        assert errors


def test_old_memory_is_upgraded_from_exact_current_execution(actual):
    t=actual['results'][0]['turns'][2]
    state=prepare_research_context(t['evidence_snapshot'],t['message'])
    for item in state['observations']:
        item.pop('analysis_contract')
    rebuilt=prepare_research_context(t['evidence_snapshot'],t['message'],state)
    assert all(x['analysis_contract']['supported'] for x in rebuilt['observations'])


@pytest.mark.parametrize('language,groupword', [('tr','Seçilen satırlar'),('en','Selected rows'),('nl','Geselecteerde rijen')])
def test_factual_group_is_rendered_in_all_supported_languages(actual,language,groupword):
    t=actual['results'][0]['turns'][2]
    state=prepare_research_context(t['evidence_snapshot'],t['message']);state['response_language']=language
    turn,errors=compile_reply(GroundedResearchPlan(next_action=None,evidence_ids=state['current_evidence_ids'][:1]),state,t['message'])
    assert not errors
    assert groupword in render_turn(turn,state,t['message'])
    assert '`offline` = `1`' in turn.answer


def test_unsupported_current_expression_stops_without_spending_model_quota(actual):
    t=deepcopy(actual['results'][0]['turns'][2]);n=t['evidence_snapshot']
    n['latest_cell']['code']='custom_transform(df)'
    ctx={'workspace_id':'unsupported','artifacts':{'selected_notebook':n},'dataset_profile_summary':{'columns':n['available_columns']}}
    with patch('backend.app.mentor_research_service.guarded_responses_parse') as model, patch('backend.app.mentor_research_service.get_ai_runtime') as runtime:
        reply=generate_research_reply(ctx,t['message'],[])
    model.assert_not_called();runtime.assert_not_called()
    assert 'güvenle eşleştiremiyorum' in reply
    assert not load_research_state('unsupported','n1')['last_validation']['accepted']


def test_direct_call_rejects_stale_result_even_with_valid_id(actual):
    t=actual['results'][0]['turns'][2]
    state=prepare_research_context(t['evidence_snapshot'],t['message'])
    state['observations'][0]['stale_scope']=True
    # Find the latest by ID rather than insertion order.
    latest=next(x for x in state['observations'] if x['id']==state['current_evidence_ids'][0]);latest['stale_scope']=True
    turn,errors=compile_reply(GroundedResearchPlan(next_action=None,evidence_ids=[latest['id']]),state,t['message'])
    assert turn is None and errors


def test_connected_checks_use_the_actual_previous_proposal_output():
    from backend.app.mentor_research_service import GroundedResearchDecision
    df=pd.DataFrame({'target':[None,7,None,4], 'flag':[0,1,1,0], 'reason':[None,'A','B',None]})
    untouched=df.copy(deep=True)
    expressions=[
        'df["target"].isna().sum()',
        'df.loc[df["target"].isna(), "flag"].value_counts(dropna=False)',
        'df.loc[df["target"].isna() & (df["flag"] == 1), "reason"].isna().sum()',
    ]
    cells=[];history=[];replies=[]
    for step,code in enumerate(expressions):
        # These are fixed local test expressions, NOT arbitrary model execution.
        output=eval(compile(code,'synthetic-fixed-test','eval'),{'__builtins__':{}},{'df':df})
        cell={'cell_id':str(step),'code':code,'section_title':'target','last_execution':{
            'success':True,'output':str(output),'input_row_count':4,'input_total_row_count':4,
            'dataset_kind':'working','input_data_version':'connected-v1'}}
        cells.append(cell)
        n={'notebook_id':'connected','dataset_kind':'working','configured_development_rows':4,
           'current_input_version':'connected-v1','latest_cell':cell,'recent_cells':list(reversed(cells)),
           'available_columns':list(df.columns)}
        ctx={'workspace_id':'connected','artifacts':{'selected_notebook':n},'dataset_profile_summary':{'columns':list(df.columns)}}
        msg='target boşluklarını inceleyelim, sonraki tek adım ne?' if step<2 else 'Bu sonuç neyi gösteriyor? Yeni görev verme.'
        def response(*args,**kwargs):
            payload=json.loads(kwargs['input']);ref=payload['current_observations'][0]['id']
            action=None
            if step<2:
                next_code=expressions[step+1]
                action={'kind':'inspect','code':next_code}
            return SimpleNamespace(output_parsed=GroundedResearchDecision.model_validate_json(
                json.dumps({'next_action':action,'evidence_ids':[ref]})))
        with patch('backend.app.mentor_research_service.get_ai_runtime',return_value=SimpleNamespace(client=None,provider='groq',model='test')), \
             patch('backend.app.mentor_research_service.guarded_responses_parse',side_effect=response) as model:
            reply=generate_research_reply(ctx,msg,history)
        assert model.call_count==1
        assert load_research_state('connected','connected')['last_validation']['accepted']
        assert 'UNTRUSTED' not in reply
        history.extend([{'role':'user','content':msg},{'role':'assistant','content':reply}]);replies.append(reply)
        if step<2:
            saved=load_research_state('connected','connected')['proposals'][-1]
            assert saved['code']==expressions[step+1]
    assert '**0**' in replies[-1]
    assert '`target` eksik VE `flag` = `1`' in replies[-1]
    assert 'grubun boş olmadığını' in replies[-1]
    assert 'Sonraki tek adım' not in replies[-1]
    pd.testing.assert_frame_equal(df,untouched)
