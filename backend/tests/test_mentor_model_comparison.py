"""Controlled model-comparison wiring; no real provider/model-quality claims."""
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.app import database
from backend.app.ai_provider_service import AIRuntime
from backend.app.mentor_adaptive_teaching_service import TeachingAnswer
from backend.benchmarks import run_mentor_teaching_probe as probe


@pytest.fixture(autouse=True)
def ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'ledger.sqlite')
    database.init_db()


class Client:
    def __init__(self, models=None):
        self.retry_options = []
        self.models = SimpleNamespace(list=lambda: SimpleNamespace(data=[
            SimpleNamespace(id=x) for x in (probe.MODEL_COMPARISON_IDS if models is None else models)]))
    def with_options(self, **options):
        self.retry_options.append(options)
        return self


def runtime(client=None):
    return AIRuntime(provider='groq', model='openai/gpt-oss-120b', client=client or Client())


def policy():
    return patch.object(probe, 'get_ai_billing_policy', return_value={
        'free_only': True, 'allowed_free_providers': ['groq']})


def response(*args, **kwargs):
    return SimpleNamespace(status='completed', output_parsed=TeachingAnswer(answer='Bir koşul işaretleri üretir; satır seçimi başka bir işlemdir.'),
        usage=SimpleNamespace(input_tokens=500, output_tokens=50, total_tokens=550))


def test_completion_metadata_preserves_unfinished_text_without_claiming_quality():
    raw = json.dumps({'answer': 'Koşul her satır için bir'}, ensure_ascii=False)
    original = response()
    original.output_text = raw
    original.output = [SimpleNamespace(type='reasoning', summary='private-reasoning'),
        SimpleNamespace(type='message', status='completed', content=[
            SimpleNamespace(type='output_text', text=raw)])]
    original.usage.output_tokens_details = SimpleNamespace(reasoning_tokens=17)
    metadata = probe.response_completion_metadata(original)
    assert metadata['status'] == 'completed'
    assert metadata['output_text']['text'] == raw
    assert metadata['output_items'][1]['content'][0]['text'] == metadata['output_text']
    assert metadata['reasoning_tokens'] == 17
    assert metadata['incomplete_reason'] is metadata['finish_reason'] is None
    assert 'private-reasoning' not in json.dumps(metadata)
    assert 'quality' not in metadata and 'accepted' not in metadata


def test_completion_metadata_handles_missing_fields_and_bounds_text():
    assert probe.response_completion_metadata(SimpleNamespace())['status'] is None
    metadata = probe.response_completion_metadata({
        'status': 'incomplete', 'incomplete_details': {'reason': 'max_output_tokens'},
        'output_text': 'x' * 12001, 'output': [{'type': 'message', 'status': 'incomplete',
            'content': [{'type': 'output_text', 'text': 'unfinished'},
                {'type': 'refusal', 'refusal': 'private-body'}]}],
        'headers': {'authorization': 'secret'}, 'error': {'message': 'private-error'}})
    assert metadata['incomplete_reason'] == 'max_output_tokens'
    assert metadata['output_text']['characters'] == 12001
    assert metadata['output_text']['capture_truncated']
    assert len(metadata['output_text']['text']) == 12000
    assert metadata['output_items'][0]['content'][0]['text']['text'] == 'unfinished'
    assert 'private-' not in json.dumps(metadata) and 'secret' not in json.dumps(metadata)


def test_real_sdk_parse_keeps_provider_text_separate_from_teaching_extraction():
    import httpx
    from openai import OpenAI

    raw = json.dumps({'answer': 'Bu işaretleri satır seçmek için'}, ensure_ascii=False)
    body = {'id': 'resp_synthetic', 'object': 'response', 'created_at': 0,
        'status': 'completed', 'model': 'synthetic-model',
        'output': [{'id': 'msg_synthetic', 'type': 'message', 'role': 'assistant',
            'status': 'completed', 'content': [{'type': 'output_text', 'text': raw, 'annotations': []}]}]}
    with OpenAI(api_key='synthetic-test-key', max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json=body)))) as sdk:
        parsed = sdk.responses.parse(model='synthetic-model', input='synthetic', text_format=TeachingAnswer)
    metadata = probe.response_completion_metadata(parsed)
    assert parsed.output_parsed.answer == 'Bu işaretleri satır seçmek için'
    assert metadata['output_text']['text'] == raw
    assert metadata['output_items'][0]['content'][0]['text']['text'] == raw
    assert metadata['status'] == 'completed'  # Status alone does not prove a finished explanation.


def test_offline_all_six_inputs_are_equal_and_never_touch_provider_or_database():
    with patch.object(probe, 'get_ai_runtime') as model, \
         patch.object(probe, 'guarded_responses_parse') as provider, \
         patch.object(database, 'get_connection', side_effect=AssertionError('project database accessed')):
        report = probe.run_model_comparison(live=False)
    model.assert_not_called(); provider.assert_not_called()
    assert report['status'] == 'prepared_not_live_tested'
    assert report['provider_calls'] == report['model_catalog_requests'] == 0
    assert report['max_provider_calls'] == 12 and len(report['pairs']) == 6
    for pair in report['pairs']:
        arms = list(pair['arms'].values())
        assert arms[0] == arms[1] and pair['same_request_context']
        assert arms[0]['input']['previous_explanations'] == []
        assert 'context-capture-only' not in json.dumps(arms)
        assert arms[0]['response_schema'] == 'TeachingAnswer'
    # The failure and result states are not generated by either model.
    assert report['pairs'][3]['arms'][probe.MODEL_COMPARISON_IDS[0]]['input']['latest_attempt']['success'] is False
    assert report['pairs'][4]['arms'][probe.MODEL_COMPARISON_IDS[0]]['input']['investigation_context']['verified_checks'][0]['proportions'] == {'open': .9, 'closed': .1}


@pytest.mark.parametrize('case', ['sensors', 'service'])
def test_other_schemas_prepare_without_generation(case):
    report = probe.run_model_comparison(live=False, case=case, turns=1)
    assert report['status'] == 'prepared_not_live_tested' and report['provider_calls'] == 0
    assert report['pairs'][0]['arms'][probe.MODEL_COMPARISON_IDS[0]]['input']['investigation_context']['focus_column'] in {'reading','resolution_time'}


def test_live_wiring_keeps_input_options_caps_order_and_actual_candidates():
    calls, saved = [], []
    client = Client(); original = runtime(client)
    def provider(*args, **kwargs):
        calls.append(kwargs)
        return response(*args, **kwargs)
    with policy(), patch.object(probe, 'get_ai_runtime', return_value=original), \
         patch.object(probe, 'guarded_responses_parse', side_effect=provider), \
         patch.object(database, 'get_connection', side_effect=AssertionError('project database accessed')):
        report = probe.run_model_comparison(live=True, turns=6, delay=0,
            checkpoint=lambda x: saved.append(x))
    assert report['status'] == 'completed_requires_human_review'
    assert report['provider_calls'] == len(calls) == 12
    assert client.retry_options == [{'max_retries': 0}]
    assert original.model == 'openai/gpt-oss-120b'
    assert report['pairs'][0]['call_order'] == list(probe.MODEL_COMPARISON_IDS)
    assert report['pairs'][1]['call_order'] == list(reversed(probe.MODEL_COMPARISON_IDS))
    for pair in report['pairs']:
        assert pair['same_request_context']
        a,b = pair['arms'].values()
        assert a['input'] == b['input'] and a['instructions'] == b['instructions']
        assert a['reasoning'] == b['reasoning'] == {'effort': 'low'}
        assert a['max_output_tokens'] == b['max_output_tokens'] <= 1200
        assert a['provider_candidate']['answer'] == a['displayed_reply']
        assert a['response_completion']['status'] == 'completed'
        assert a['diagnostics']['semantic_quality_verified'] is False
        assert a['pending_task']['status'] == 'awaiting_execution'
    assert saved[-1]['status'] == report['status'] and report['comparison_winner'] is None
    assert not report['novice_usability_accepted'] and not report['project_completion_proven']


def test_real_guard_counts_both_models_in_normal_ledger_without_project_memory(monkeypatch):
    monkeypatch.setenv('AI_FREE_ONLY', 'true')
    monkeypatch.setenv('AI_FREE_PROVIDER_ALLOWLIST', 'groq')
    client = Client()
    client.responses = SimpleNamespace(parse=lambda **kwargs: response(**kwargs))
    before = database.get_ai_usage_counts()['daily_requests']
    with patch.object(probe, 'get_ai_runtime', return_value=runtime(client)):
        report = probe.run_model_comparison(live=True, turns=1, delay=0)
    assert report['status'] == 'completed_requires_human_review'
    assert database.get_ai_usage_counts()['daily_requests'] - before == 2
    connection = database.get_connection()
    try:
        assert connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='mentor_research_memory'").fetchone()[0] == 0
    finally:
        connection.close()


@pytest.mark.parametrize('kind', ['configuration', 'missing_model', 'provider_failure', 'incomplete', 'code_preference'])
def test_blockers_and_content_failures_are_distinct_and_never_retried(kind):
    class Failure(Exception):
        status_code = 429
        body = {'error': {'code': 'rate_limit_exceeded', 'message': 'private-provider-body'}}
    client = Client(models=['openai/gpt-oss-120b'] if kind == 'missing_model' else None)
    def provider(*args, **kwargs):
        if kind == 'provider_failure': raise Failure('private-exception')
        if kind == 'incomplete': return SimpleNamespace(status='incomplete', output_parsed=None)
        if kind == 'code_preference':
            return SimpleNamespace(status='completed', output_parsed=TeachingAnswer(answer='df[flags] ile seç.'))
        return response(*args, **kwargs)
    with patch.object(probe, 'get_ai_billing_policy', return_value={
        'free_only': kind != 'configuration', 'allowed_free_providers': ['groq']}), \
         patch.object(probe, 'get_ai_runtime', return_value=runtime(client)), \
         patch.object(probe, 'guarded_responses_parse', side_effect=provider) as model:
        report = probe.run_model_comparison(live=True, turns=2, delay=0)
    assert 'private-' not in json.dumps(report)
    if kind in {'configuration','missing_model'}:
        assert report['provider_calls'] == model.call_count == 0
        assert report['status'] in {'blocked_configuration','blocked_model_unavailable'}
    elif kind == 'code_preference':
        assert report['provider_calls'] == model.call_count == 4
        assert report['status'] == 'completed_requires_human_review'
        assert all(not arm['diagnostics']['teaching_accepted'] for pair in report['pairs'] for arm in pair['arms'].values())
    else:
        assert report['provider_calls'] == model.call_count == 1
        assert report['status'] == 'blocked' and len(report['pairs'][0]['arms']) == 1
        if kind == 'provider_failure':
            failed = next(iter(report['pairs'][0]['arms'].values()))
            assert failed['failure']['provider_error_code'] == 'rate_limit_exceeded'
        else:
            failed = next(iter(report['pairs'][0]['arms'].values()))
            assert failed['response_completion']['status'] == 'incomplete'


def test_interrupt_checkpoints_completed_work_and_does_not_retry():
    saved = []
    with policy(), patch.object(probe, 'get_ai_runtime', return_value=runtime()), \
         patch.object(probe, 'guarded_responses_parse', side_effect=[response(), KeyboardInterrupt()]) as provider:
        with pytest.raises(KeyboardInterrupt):
            probe.run_model_comparison(live=True, turns=2, delay=0, checkpoint=lambda x: saved.append(x))
    assert provider.call_count == 2 and saved[-1]['status'] == 'interrupted'
    assert next(iter(saved[-1]['pairs'][0]['arms'].values()))['provider_candidate']


def test_format_comparison_offline_is_one_pair_with_only_schema_changed():
    with patch.object(probe, 'get_ai_runtime') as model, \
         patch.object(probe, 'guarded_responses_create') as provider:
        report = probe.run_model_comparison(live=False, format_comparison=True)
    model.assert_not_called(); provider.assert_not_called()
    assert report['max_provider_calls'] == 2 and len(report['pairs']) == 1
    assert report['models'] == ['qwen/qwen3.8-27b']
    a,b = report['pairs'][0]['arms'].values()
    assert a['response_schema'] == 'TeachingAnswer' and b['response_schema'] == 'PlainText'
    assert {k:v for k,v in a.items() if k != 'response_schema'} == {k:v for k,v in b.items() if k != 'response_schema'}


@pytest.mark.parametrize('plain_status', ['completed', 'incomplete'])
def test_format_comparison_real_guards_keep_ledger_caps_and_raw_text(monkeypatch, plain_status):
    monkeypatch.setenv('AI_FREE_ONLY', 'true')
    monkeypatch.setenv('AI_FREE_PROVIDER_ALLOWLIST', 'groq')
    calls = []
    client = Client(models=['qwen/qwen3.8-27b'])
    def structured(**kwargs):
        calls.append(('parse', kwargs))
        return response()
    raw = 'Bir sayı elde ettin. Şimdi ilgili satırları seç.'
    def plain(**kwargs):
        calls.append(('create', kwargs))
        return SimpleNamespace(status=plain_status, output_text=raw,
            incomplete_details=SimpleNamespace(reason='max_output_tokens') if plain_status == 'incomplete' else None)
    client.responses = SimpleNamespace(parse=structured, create=plain)
    before = database.get_ai_usage_counts()['daily_requests']
    with patch.object(probe, 'get_ai_runtime', return_value=runtime(client)):
        report = probe.run_model_comparison(live=True, format_comparison=True, delay=0)
    assert database.get_ai_usage_counts()['daily_requests'] - before == 2
    assert report['provider_calls'] == report['max_provider_calls'] == len(calls) == 2
    assert calls[0][0] == 'parse' and calls[1][0] == 'create'
    first,second = calls[0][1].copy(),calls[1][1].copy()
    assert first.pop('text_format') is TeachingAnswer
    assert first == second and second['model'] == 'qwen/qwen3.8-27b'
    assert second['reasoning'] == {'effort': 'low'} and second['max_output_tokens'] <= 1200
    arm = report['pairs'][0]['arms']['plain_text']
    assert arm['response_completion']['output_text']['text'] == raw
    assert arm['pending_task']['status'] == 'awaiting_execution'
    if plain_status == 'completed':
        assert report['status'] == 'completed_requires_human_review'
        assert report['pairs'][0]['same_request_context']
        assert arm['provider_candidate']['answer'] == arm['displayed_reply'] == raw
    else:
        assert report['status'] == 'blocked'
        assert arm['diagnostics']['reason'] == 'incomplete_response'
    assert report['comparison_winner'] is None and not report['project_completion_proven']
