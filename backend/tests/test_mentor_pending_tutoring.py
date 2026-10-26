"""Help a beginner on the existing task; never fabricate execution or new work."""
from copy import deepcopy
from unittest.mock import patch

import pytest

from backend.app import database
from backend.app.mentor_research_service import generate_research_reply
from backend.app.mentor_research_service import ResearchTurn, render_turn
from backend.app.mentor_research_store import load_research_state
from backend.app.mentor_tutoring_service import explicit_code_requested
from backend.benchmarks.run_mentor_research_acceptance import CASES, snapshots
from backend.benchmarks.run_mentor_connected_followup import run_case


@pytest.fixture(autouse=True)
def memory(tmp_path,monkeypatch):
    monkeypatch.setattr(database,'DATABASE_PATH',tmp_path/'tutoring.sqlite')
    database.init_db()


def seed(case='sensors'):
    context,_=next(snapshots(case))
    target=CASES[case][0]
    generate_research_reply(context,f'{target} sayımını yaptım. Veri sözlüğüm yok; sonraki tek adımı söyle.',[],allow_provider=False)
    return context,load_research_state(context['workspace_id'],'n1')


@pytest.mark.parametrize('message,expected',[
    ('Kodu göster.',True),('Kodu gösterebilir misin?',True),('Kodu yaz.',True),
    ('Show me the code.',True),('Give me code.',True),('Toon de code.',True),('Geef de code.',True),
    ('Kodu gösterme, ipucu ver.',False),('Kodu gostermeden yardim et.',False),
    ('Kodu verme.',False),('Kodu yazma.',False),('Kod vermeden yönlendir.',False),
    ('Kodu göster ama çözümü verme.',False),
    ("Don't show me the code.",False),('Do not give me code.',False),
    ('Guide me without code.',False),('Without giving me the solution, help me.',False),
    ('Toon de code niet.',False),('Geef de code niet.',False),
    ('Zonder code, graag een hint.',False),('Geen code.',False),
    ('Show me the code. No code please.',False),
    ('Show me the code, but do not provide code.',False),
    ('Kodu göster ama çözümü söyleme.',False),
])
def test_explicit_code_request_does_not_match_a_negative_request(message,expected):
    assert explicit_code_requested(message) is expected


@pytest.mark.parametrize('case',list(CASES))
@pytest.mark.parametrize('language,messages',[
    ('tr',['Bunu nasıl yapacağımı bilmiyorum. Kodu gösterme; ipucu ver.',
           'Hâlâ anlamadım; daha basit anlat. Kodu verme.','Kodu gösterebilir misin?',
           'Şimdi kodu gösterme; yalnız ipucu ver.']),
    ('en',["I don't know how to do this. Don't show me the code.",
           "I still don't understand. Explain more simply without code.",'Show me the code.',
           'Do not show me the code. Give me a hint.']),
    ('nl',['Ik weet niet hoe ik dit moet doen. Zonder code graag een hint.',
           'Ik begrijp het nog steeds niet. Leg het eenvoudiger uit, geen code.',
           'Toon de code.','Toon de code niet; geef me een hint.']),
])
def test_help_scaffolds_same_pending_task_and_only_explicitly_shows_code(case,language,messages):
    context,before=seed(case)
    context['ui_context']={'language':language}
    code=before['proposals'][-1]['code']
    replies=[]
    with patch('backend.app.mentor_research_service.get_ai_runtime') as runtime, \
         patch('backend.app.mentor_research_service.guarded_responses_parse') as provider:
        for index,message in enumerate(messages):
            reply=generate_research_reply(context,message,[],allow_provider=False)
            state=load_research_state(context['workspace_id'],'n1');validation=state['last_validation']
            assert validation['accepted'] and validation['origin']=='adaptive_teaching'
            assert validation['teaching_accepted'] is False
            assert validation['reason']=='provider_disabled'
            assert validation['code_shown'] is (index==2)
            assert state['proposals']==before['proposals']
            assert state['proposals'][-1]['status']=='proposed'
            assert state['focus_column']==CASES[case][0]
            assert validation['local_proposal']['next_action'] is None
            assert validation['supported_proposal']['next_action']['code']==code
            assert validation['provider_calls']==0
            assert ('```python\n'+code+'\n```' in reply) is (index==2)
            assert len(reply)<1800 and '5000' not in reply  # do not recap every observation on each hint
            replies.append(reply)
    assert all(replies)  # Offline fallback does not prove adaptive teaching.
    runtime.assert_not_called();provider.assert_not_called()


def test_regular_action_renderer_also_respects_negative_code_requests():
    _,state=seed()
    turn=ResearchTurn.model_validate(state['last_validation']['local_proposal'])
    assert '```' not in render_turn(turn,state,'Kodu gösterme; ipucu ver.')
    assert '```python' in render_turn(turn,state,'Kodu göster.')


@pytest.mark.parametrize('case',list(CASES))
def test_help_requests_fit_in_the_real_connected_production_chain(case):
    with patch('backend.app.mentor_research_service.get_ai_runtime') as runtime:
        report=run_case(case,with_support=True)
    runtime.assert_not_called()
    assert report['passed'] and len(report['support_turns'])==5
    assert all(t['validation']['teaching_accepted'] is False for t in report['support_turns'])
    assert [t['validation']['code_shown'] for t in report['support_turns']]==[False,False,True,False,True]
    assert all(not t['new_task_assigned'] for t in report['support_turns'])
    assert not report['beginner_usability_tested']


def test_workspace_http_chat_preserves_no_code_help_and_pending_task(monkeypatch):
    monkeypatch.setenv('AI_NOTEBOOK_RESEARCH_ENABLED','true')
    from fastapi.testclient import TestClient
    from backend.app.main import app
    client=TestClient(app)
    database.insert_learner_profile(learner_id='help-route',answer_length='concise',learning_style='guided',code_support='medium')
    created=client.post('/workspaces',json={'learner_id':'help-route','title':'Help route','workspace_type':'data_engineering'}).json()
    workspace=database.get_workspace(workspace_id=created['workspace_id'],learner_id='help-route')
    context,_=next(snapshots('sensors'));context['workspace_id']=workspace.workspace_id
    context['ui_context']={'language':'tr'}
    request={'learner_id':'help-route','workspace_id':workspace.workspace_id,'session_id':workspace.mentor_session_id,
             'ui_context':{'selected_notebook_id':'n1','workbench_view':'notebook','language':'tr'}}
    with patch('backend.app.chat_routes.build_chat_mentor_workspace_context',return_value=context), \
         patch('backend.app.mentor_research_service.get_ai_runtime') as runtime, \
         patch('backend.app.chat_routes.get_mentor_response_from_message') as legacy:
        first=client.post('/chat',json={**request,'message':'temperature sayımı hazır. Veri sözlüğüm yok; sonraki tek adımı söyle.'})
        assert first.status_code==200,first.text
        before=deepcopy(load_research_state(workspace.workspace_id,'n1')['proposals'])
        response=client.post('/chat',json={**request,'message':'Bunu nasıl yapacağımı bilmiyorum. Kodu gösterme; ipucu ver.'})
    assert response.status_code==200,response.text
    assert 'yerel yedek rehber' in response.json()['reply']
    assert '```' not in response.json()['reply']
    assert load_research_state(workspace.workspace_id,'n1')['proposals']==before
    runtime.assert_not_called();legacy.assert_not_called()
