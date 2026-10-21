"""Real provider rejection is replayed locally, without another paid call."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, Mock

import httpx
from openai import BadRequestError
import pytest

from backend.app import database
from backend.app.mentor_research_service import (
    ResearchTurn, GroundedResearchPlan, prepare_research_context, normalize_review_references,
    validate_turn, generate_research_reply,
)
from backend.app.mentor_research_store import load_research_state
from backend.benchmarks.run_mentor_research_acceptance import reusable_prefix, run_live_case, main


@pytest.fixture
def actual():
    return json.loads((Path(__file__).parent / 'fixtures/research_long_response.json').read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def memory(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'length.db')
    database.init_db()


def test_wire_schema_does_not_turn_style_lengths_into_provider_400():
    schema = ResearchTurn.model_json_schema()
    assert 'maxLength' not in schema['properties']['answer']
    assert 'maxItems' not in schema['properties']['claims']
    assert 'maxLength' not in schema['$defs']['ResearchClaim']['properties']['text']
    assert 'maxLength' not in schema['$defs']['ResearchAction']['properties']['instruction']


def test_actual_long_response_reaches_local_review_instead_of_parse_failure(actual):
    turn = ResearchTurn.model_validate(actual['failed_generation'])
    assert len(turn.answer) == 1727
    state = prepare_research_context(actual['notebook'], actual['message'])
    state['response_language'] = 'tr'
    clean, _ = normalize_review_references(turn, state)
    errors = validate_turn(clean, state, actual['message'])
    assert any('too long' in error for error in errors)
    assert 'Answer must not assign a task outside the validated action' in errors


def test_provider_returned_long_json_gets_local_checks_and_one_repair(actual):
    ctx = {'workspace_id': 'length-replay', 'artifacts': {'selected_notebook': actual['notebook']},
           'dataset_profile_summary': {'columns': actual['notebook']['available_columns']}}
    raw = actual['failed_generation']
    state = prepare_research_context(actual['notebook'], actual['message'])
    concise = GroundedResearchPlan(next_action=None, evidence_ids=state['current_evidence_ids'][:1])
    error = BadRequestError('schema length rejection',
        response=httpx.Response(400, request=httpx.Request('POST','https://example.test/responses')),
        body={'error': {'code':'json_validate_failed','message':'maxLength exceeded','failed_generation':json.dumps(raw)}})
    pacer = Mock()
    with patch('backend.app.mentor_research_service.get_ai_runtime',return_value=SimpleNamespace(client=None,provider='groq',model='test')), \
         patch('backend.app.mentor_research_service.guarded_responses_parse',side_effect=[error,SimpleNamespace(output_parsed=concise)]) as model:
        reply = generate_research_reply(ctx,actual['message'],[],request_pacer=pacer)
    assert model.call_count == 2
    assert pacer.call_count == 2
    saved = load_research_state('length-replay','n1')['last_validation']
    assert saved['accepted'] is True
    assert saved['model_attempts'][0]['provider_recovery']['http_status'] == 400
    assert any('Invalid research field' in e for e in saved['model_attempts'][0]['errors'])
    assert '**0**' in reply
    assert 'offline' in reply


def test_actual_two_completed_turns_are_reusable_under_current_checks(actual):
    prefix, history = reusable_prefix('sensors',actual['accepted_prefix'],4)
    assert len(prefix) == 2
    assert len(history) == 4
    assert prefix[0]['reply'] != actual['accepted_prefix'][0]['reply']
    assert prefix[0]['validation']['cached_display_recompiled'] is True
    assert '**5000**' in prefix[0]['reply']


def test_resume_refuses_changed_fixture_without_model_call(actual):
    actual['accepted_prefix'][0]['evidence_snapshot']['configured_development_rows'] = 20000
    with pytest.raises(ValueError,match='evidence changed'):
        reusable_prefix('sensors',actual['accepted_prefix'],4)


def test_resume_calls_only_unfinished_turn_and_keeps_learner_message(actual,tmp_path):
    error = BadRequestError('unexpected request',response=httpx.Response(400,request=httpx.Request('POST','https://example.test/responses')),body={'error':{'message':'provider diagnosis','code':'bad_request'}})
    with patch('backend.benchmarks.run_mentor_research_acceptance.generate_research_reply',side_effect=error) as model:
        result = run_live_case('sensors',tmp_path/'case.json',0,4,actual['accepted_prefix'])
    model.assert_called_once()
    assert model.call_args.args[1] == actual['message']
    assert result['reused_turns'] == 2
    assert result['turns'][2]['message'] == actual['message']
    assert result['turns'][2]['provider_message'] == 'provider diagnosis'
    assert result['turns'][2]['http_status'] == 400


def test_resume_never_silently_starts_over_without_report(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(['--live','--resume-latest','--output-dir',str(tmp_path)])
    assert exc.value.code == 2


def test_resume_cli_preserves_passed_turns_and_calls_only_turns_three_and_four(actual,tmp_path):
    from backend.app.mentor_research_store import save_research_state
    folder = tmp_path / '20261018-122000'
    folder.mkdir()
    original = {'mode':'live','results':[{'case':'sensors','planned_turns':4,'turns':actual['accepted_prefix']}]}
    (folder/'report.json').write_text(json.dumps(original),encoding='utf-8')
    previous_db = database.DATABASE_PATH
    database.DATABASE_PATH = folder/'isolated-research.sqlite'
    database.init_db()
    saved = prepare_research_context(actual['notebook'],actual['message'])
    save_research_state('acceptance-sensors','n1',saved)
    def accept(ctx,message,history):
        state = load_research_state(ctx['workspace_id'],'n1')
        state['last_validation'] = {'accepted':True}
        save_research_state(ctx['workspace_id'],'n1',state)
        return 'New simulated reply'
    try:
        with patch('backend.benchmarks.run_mentor_research_acceptance.generate_research_reply',side_effect=accept) as model:
            result = main(['--live','--resume-latest','--case','sensors','--delay','0','--output-dir',str(tmp_path)])
        assert result == 0
        assert model.call_count == 2
        assert model.call_args_list[0].args[1] == actual['message']
        report = json.loads((folder/'report.json').read_text(encoding="utf-8"))
        assert report['results'][0]['reused_turns'] == 2
        assert all(t['validation']['cached_display_recompiled'] for t in report['results'][0]['turns'][:2])
        assert report['results'][0]['turns'][0]['evidence_snapshot'] == actual['accepted_prefix'][0]['evidence_snapshot']
        assert len(list(folder.glob('report-before-resume-*.json'))) == 1
    finally:
        database.DATABASE_PATH = previous_db
