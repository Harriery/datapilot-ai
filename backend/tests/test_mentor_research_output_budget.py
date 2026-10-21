"""Replay report(4) provider truncation without sending another model request."""
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
    ResearchTurn, generate_research_reply, research_generation_options,
    research_response_metadata,
)
from backend.app.mentor_research_store import load_research_state
from backend.tests.test_mentor_research_service import state, proposal, grounded_proposal, context


@pytest.fixture(autouse=True)
def memory(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'budget.db')
    monkeypatch.setenv('AI_MAX_OUTPUT_TOKENS_PER_REQUEST', '1500')
    database.init_db()


def recorded_attempts():
    return json.loads((Path(__file__).parent / 'fixtures/research_truncated_output.json').read_text(encoding="utf-8"))['model_attempts']


def error_for(failure):
    return BadRequestError('recorded provider truncation',
        response=httpx.Response(400, request=httpx.Request('POST', 'https://example.test/responses')),
        body={'error': {k: v for k, v in failure.items() if k in {'code', 'type', 'message', 'failed_generation'}}})


@pytest.mark.parametrize('index', [0, 1])
def test_actual_provider_partial_document_never_fabricates_missing_action(index):
    failure = recorded_attempts()[index]['provider_recovery']
    raw = json.loads(failure['failed_generation'])
    assert 'next_action' not in raw
    with pytest.raises(ValidationError):
        ResearchTurn.model_validate(raw)
    good = grounded_proposal(state())
    with patch('backend.app.mentor_research_service.get_ai_runtime', return_value=SimpleNamespace(client=None, provider='groq', model='openai/gpt-oss-120b')), \
         patch('backend.app.mentor_research_service.guarded_responses_parse', side_effect=[error_for(failure), SimpleNamespace(output_parsed=good)]) as call:
        generate_research_reply(context(), 'sensor_value için kod verme, yönlendir', [])
    saved = load_research_state('w1', 'n1')['last_validation']
    assert saved['accepted'] is True
    assert saved['runtime']['max_output_tokens'] == 1500
    assert saved['runtime']['reasoning'] == {'effort': 'low'}
    first = saved['model_attempts'][0]
    assert first['proposal'] is None
    assert 'token limit' in first['errors'][0]
    assert first['provider_recovery']['failed_generation'] == failure['failed_generation']
    for invocation in call.call_args_list:
        assert invocation.kwargs['reasoning'] == {'effort': 'low'}
        # The common usage guard still owns the configured token ceiling.
        assert 'max_output_tokens' not in invocation.kwargs
    repair = json.loads(call.call_args_list[1].kwargs['input'])
    assert repair['required_internal_contract']['output_token_limit'] == 1500
    assert 'complete' in repair['repair_required'][0]


def test_even_schema_complete_json_is_rejected_when_provider_declares_truncation():
    failure = dict(recorded_attempts()[0]['provider_recovery'])
    failure['failed_generation'] = proposal(state()).model_dump_json()
    with patch('backend.app.mentor_research_service.get_ai_runtime', return_value=SimpleNamespace(client=None, provider='groq', model='openai/gpt-oss-120b')), \
         patch('backend.app.mentor_research_service.guarded_responses_parse', side_effect=[error_for(failure), error_for(failure)]) as call:
        generate_research_reply(context(), 'sensor_value için kod verme, yönlendir', [])
    saved = load_research_state('w1', 'n1')['last_validation']
    assert saved['accepted'] is False
    assert call.call_count == 2
    assert all(item['proposal'] is None for item in saved['model_attempts'])
    assert load_research_state('w1', 'n1').get('proposals', []) == []


def test_success_transport_with_incomplete_status_cannot_bypass_review():
    partial = SimpleNamespace(output_parsed=proposal(state()), status='incomplete',
        incomplete_details=SimpleNamespace(reason='max_output_tokens'))
    with patch('backend.app.mentor_research_service.get_ai_runtime', return_value=SimpleNamespace(client=None, provider='groq', model='openai/gpt-oss-120b')), \
         patch('backend.app.mentor_research_service.guarded_responses_parse', side_effect=[partial, partial]):
        generate_research_reply(context(), 'sensor_value için kod verme, yönlendir', [])
    saved = load_research_state('w1', 'n1')['last_validation']
    assert saved['accepted'] is False
    assert saved['model_attempts'][0]['response_metadata']['incomplete_reason'] == 'max_output_tokens'


@pytest.mark.parametrize('provider,model', [('groq','llama-model'), ('openai','gpt-5-mini'), ('other','openai/gpt-oss-120b')])
def test_reasoning_option_is_not_sent_to_unverified_adapters(provider, model):
    assert research_generation_options(provider, model) == {}


def test_telemetry_never_copies_reasoning_content():
    response = SimpleNamespace(status='completed', output=['private reasoning'],
        usage=SimpleNamespace(input_tokens=900, output_tokens=800, total_tokens=1700,
            output_tokens_details=SimpleNamespace(reasoning_tokens=200)))
    assert research_response_metadata(response) == {
        'status':'completed','input_tokens':900,'output_tokens':800,
        'total_tokens':1700,'reasoning_tokens':200}
