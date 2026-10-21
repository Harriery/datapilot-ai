"""Rejected attempts survive Ctrl+C, including the wait before repair."""
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from backend.app import database
from backend.app.mentor_research_service import GroundedResearchPlan, ResearchAction, generate_research_reply
from backend.app.mentor_research_store import load_research_state
from backend.benchmarks.run_mentor_research_acceptance import main
from backend.tests.test_mentor_research_service import state, context, grounded_proposal


@pytest.fixture(autouse=True)
def memory(tmp_path,monkeypatch):
    monkeypatch.setattr(database,'DATABASE_PATH',tmp_path/'interrupt.db')
    database.init_db()


def runtime():
    return SimpleNamespace(client=None,provider='groq',model='test')


def test_first_rejected_response_is_saved_before_repair_pacing():
    bad=grounded_proposal(state());bad.next_action.code=None
    pacer=Mock()
    def pace():
        if pacer.call_count==2:
            saved=load_research_state('w1','n1')['last_validation']
            assert saved['status']=='repair_pending'
            assert len(saved['model_attempts'])==1
            assert saved['model_attempts'][0]['raw_plan']['next_action']['code'] is None
            assert saved['errors']
            raise KeyboardInterrupt()
    pacer.side_effect=pace
    with patch('backend.app.mentor_research_service.get_ai_runtime',return_value=runtime()), \
         patch('backend.app.mentor_research_service.guarded_responses_parse',return_value=SimpleNamespace(output_parsed=bad)) as provider:
        with pytest.raises(KeyboardInterrupt):
            generate_research_reply(context(),'sensor_value için sıradaki adım ne?',[],request_pacer=pacer)
    assert provider.call_count==1
    saved=load_research_state('w1','n1')['last_validation']
    assert saved['accepted'] is False and saved['status']=='interrupted'
    assert saved['interrupted_during']=='quota_wait'
    assert saved['previous_attempt_errors']==saved['model_attempts'][0]['errors']


def test_interruption_during_initial_request_is_not_reported_as_success():
    with patch('backend.app.mentor_research_service.get_ai_runtime',return_value=runtime()), \
         patch('backend.app.mentor_research_service.guarded_responses_parse',side_effect=KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            generate_research_reply(context(),'sensor_value',[])
    saved=load_research_state('w1','n1')['last_validation']
    assert saved['accepted'] is False
    assert saved['interrupted_during']=='provider_request'
    assert saved['model_attempts']==[]


def test_one_attempt_mode_records_rejection_without_wait_or_second_call():
    bad=grounded_proposal(state());bad.next_action.code=None;pacer=Mock()
    with patch('backend.app.mentor_research_service.get_ai_runtime',return_value=runtime()), \
         patch('backend.app.mentor_research_service.guarded_responses_parse',return_value=SimpleNamespace(output_parsed=bad)) as provider:
        generate_research_reply(context(),'sensor_value',[],max_attempts=1,request_pacer=pacer)
    assert provider.call_count==pacer.call_count==1
    saved=load_research_state('w1','n1')['last_validation']
    assert saved['accepted'] is False
    assert len(saved['model_attempts'])==1 and saved['errors']


@pytest.mark.parametrize('attempts',[0,3,True])
def test_invalid_attempt_limit_fails_before_provider_access(attempts):
    with patch('backend.app.mentor_research_service.get_ai_runtime') as provider:
        with pytest.raises(ValueError):
            generate_research_reply(context(),'sensor_value',[],max_attempts=attempts)
    provider.assert_not_called()


def rejected_response(*args,**kwargs):
    payload=json.loads(kwargs['input'])
    return SimpleNamespace(output_parsed=GroundedResearchPlan(
        evidence_ids=[payload['current_observations'][0]['id']],
        next_action=ResearchAction(instruction='inspect',why='inspect',focus_column=payload['focus'],
            columns=[payload['focus']],kind='inspect',code=None,
            evidence_ids=[payload['current_observations'][0]['id']]),
    ))


def test_cli_interruption_saves_final_report_and_prints_wait_reason(tmp_path,capsys):
    with patch('backend.app.mentor_research_service.get_ai_runtime',return_value=runtime()), \
         patch('backend.app.mentor_research_service.guarded_responses_parse',side_effect=rejected_response) as provider, \
         patch('backend.benchmarks.run_mentor_research_acceptance.time.monotonic',return_value=0), \
         patch('backend.benchmarks.run_mentor_research_acceptance.time.sleep',side_effect=KeyboardInterrupt):
        code=main(['--live','--case','sensors','--max-turns','1','--output-dir',str(tmp_path/'reports')])
    assert code==130 and provider.call_count==1
    report=json.loads(next((tmp_path/'reports').glob('*/report.json')).read_text(encoding='utf-8'))
    turn=report['results'][0]['turns'][0]
    assert turn['status']=='interrupted' and turn['accepted'] is False
    assert len(turn['validation']['model_attempts'])==1
    assert turn['validation']['model_attempts'][0]['errors']
    console=capsys.readouterr().out
    assert 'first attempt rejected:' in console
    assert 'waiting 65s' in console
    assert 'REPORT:' in console


def test_cli_single_attempt_has_no_repair_wait_and_still_saves_diagnosis(tmp_path):
    with patch('backend.app.mentor_research_service.get_ai_runtime',return_value=runtime()), \
         patch('backend.app.mentor_research_service.guarded_responses_parse',side_effect=rejected_response) as provider, \
         patch('backend.benchmarks.run_mentor_research_acceptance.time.sleep') as sleep:
        code=main(['--live','--case','sensors','--max-turns','1','--model-attempts','1','--output-dir',str(tmp_path/'reports')])
    assert code==1 and provider.call_count==1
    sleep.assert_not_called()
    report=json.loads(next((tmp_path/'reports').glob('*/report.json')).read_text(encoding='utf-8'))
    assert report['results'][0]['turns'][0]['validation']['model_attempts'][0]['errors']
