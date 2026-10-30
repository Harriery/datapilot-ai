"""Real CSV/query/chat boundaries with controlled replies, not teaching acceptance."""
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from backend.app import database, personal_data_mentor_service as mentor
from backend.app.mentor_research_store import load_research_state
from backend.app.models import WorkspaceNotebook, WorkspaceNotebookCell
from backend.app.notebook_scope_service import notebook_input_version
from backend.tests.test_notebook_teaching_context_preference import client_workspace


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'chat.sqlite')
    monkeypatch.setattr('backend.app.workspace_data_service.get_workspace_data_dir', lambda _: tmp_path)
    monkeypatch.setattr('backend.app.notebook_scope_service.get_workspace_data_dir', lambda _: tmp_path)
    database.init_db()
    client, created = client_workspace()
    workspace = database.get_workspace(workspace_id=created['workspace_id'], learner_id='context-choice')
    frame = pd.DataFrame({'days': [None, 2., None, 3.], 'status': ['pending', 'done', 'done', 'done']})
    frame.to_csv(tmp_path / 'working.csv', index=False)
    workspace.development_sample_size = 1000
    workspace.dataset_profile = {'columns': list(frame.columns), 'row_count': len(frame)}
    notebook = WorkspaceNotebook(notebook_id='n1', name='Investigation', dataset_kind='working',
        created_at='2026-10-27', updated_at='2026-10-27', cells=[])
    version = notebook_input_version(workspace.workspace_id, notebook, 1000)
    notebook.cells = [WorkspaceNotebookCell(cell_id='count', code='draft_not_executed', last_execution={
        'executed_code': "df['days'].isna().sum()", 'success': True,
        'input_row_count': 4, 'input_data_version': version, 'output': '2', 'executed_at': '2026-10-27T10:00:00'})]
    workspace.notebooks = [notebook]
    database.save_workspace(workspace=workspace)
    changed = client.patch(f'/workspaces/context-choice/{workspace.workspace_id}/notebook-teaching', json={'mode': 'personal_data'})
    assert changed.status_code == 200, changed.text
    workspace = database.get_workspace(workspace_id=workspace.workspace_id, learner_id='context-choice')
    context = {'ui_context': {'selected_notebook_id': 'n1', 'language': 'tr'},
        'artifacts': {'selected_notebook': {'notebook_id': 'n1'}}}
    return client, workspace, context, frame, tmp_path


def completion(content=None, calls=None, finish='stop'):
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish,
        message=SimpleNamespace(content=content, tool_calls=calls))])


def tool(query, identity='query-1'):
    return SimpleNamespace(id=identity, function=SimpleNamespace(name='inspect_data_sql', arguments=json.dumps({'query': query})))


def runtime(client=None):
    return patch.object(mentor, 'get_ai_runtime', return_value=SimpleNamespace(
        provider='groq', model='openai/gpt-oss-120b', client=client or object()))


def test_context_contains_actual_rows_schema_and_distinguishes_executed_code_from_draft(project):
    _, workspace, context, original, _ = project
    frame, scope, notebook = mentor.load_input_snapshot(workspace, context)
    data = mentor.build_data_context(workspace, context, frame, scope, notebook)
    assert scope['snapshot_rows'] == scope['persisted_input_rows'] == 4
    assert not scope['live_notebook_df'] and not scope['full_source_verified']
    assert data['dataset']['example_rows'][0] == {'days': None, 'status': 'pending'}
    assert data['dataset']['schema'][0]['missing'] == 2
    cell = data['notebook']['recent_cells'][0]
    assert cell['draft_code']['text'] == 'draft_not_executed'
    assert cell['executed_code']['text'] == "df['days'].isna().sum()"
    assert cell['recorded_code_and_scope_match']
    assert cell['recorded_output']['text'] == '2'
    notebook.cells[0].last_execution['input_row_count'] = 4000
    assert not mentor.build_data_context(workspace, context, frame, scope, notebook)['notebook']['recent_cells'][0]['recorded_code_and_scope_match']
    notebook.cells[0].last_execution['input_row_count'] = 4
    notebook.cells[0].last_execution.pop('executed_code')
    assert not mentor.build_data_context(workspace, context, frame, scope, notebook)['notebook']['recent_cells'][0]['recorded_code_and_scope_match']


def test_sampling_matches_notebook_random_selection_and_version(project):
    _, workspace, context, _, root = project
    pd.DataFrame({'days': range(100), 'status': range(100)}).to_csv(root / 'working.csv', index=False)
    workspace.development_sample_size = 17
    frame, scope, _ = mentor.load_input_snapshot(workspace, context)
    expected = pd.read_csv(root / 'working.csv').sample(n=17, random_state=42).reset_index(drop=True)
    pd.testing.assert_frame_equal(frame, expected)
    assert scope['snapshot_rows'] == 17 and scope['persisted_input_rows'] == 100


def test_local_query_compares_actual_groups_without_mutating_data(project):
    _, _, _, frame, _ = project
    before = frame.copy(deep=True)
    result = mentor.inspect_sql(frame, {'snapshot_rows': 4},
        'SELECT status, COUNT(*) AS total, COUNT(*) FILTER (WHERE days IS NULL) AS missing FROM data GROUP BY status ORDER BY status')
    assert result['status'] == 'ok'
    assert result['rows'] == [{'status': 'done', 'total': 3, 'missing': 1}, {'status': 'pending', 'total': 1, 'missing': 1}]
    pd.testing.assert_frame_equal(frame, before)


@pytest.mark.parametrize('query', ['DELETE FROM data', 'CREATE TABLE hidden AS SELECT * FROM data',
    'SELECT 1; SELECT 2', "SELECT * FROM read_csv('/etc/passwd')", "COPY data TO '/tmp/mentor-output.csv'"])
def test_query_is_read_only_and_cannot_access_external_files(project, query):
    frame = project[3]
    assert mentor.inspect_sql(frame, {}, query)['status'] in {'read_only_query_required', 'query_failed'}


def test_query_marks_bounded_rows_and_does_not_silently_claim_complete_distribution():
    result = mentor.inspect_sql(pd.DataFrame({'value': range(100)}), {'snapshot_rows': 100}, 'SELECT * FROM data')
    assert result['result_truncated'] and len(result['rows']) == 20


def test_one_tool_round_reaches_model_and_next_turn_preserves_real_inspection(project):
    _, workspace, context, _, root = project
    before = deepcopy(workspace.model_dump())
    query = 'SELECT COUNT(*) AS n FROM data WHERE days IS NULL'
    with runtime(), patch.object(mentor, 'guarded_chat_completions_create', side_effect=[
        completion(calls=[tool(query)], finish='tool_calls'), completion('Eksik grup iki kayıt içeriyor.')]) as model:
        reply = mentor.generate_personal_data_reply(workspace, context, 'Ne buldun?', [])
    assert reply == 'Eksik grup iki kayıt içeriyor.' and model.call_count == 2
    calls = model.call_args_list
    assert calls[0].kwargs['reasoning_effort'] == 'medium'
    assert calls[0].kwargs['tools'] == [mentor.TOOL] and calls[0].kwargs['tool_choice'] == 'auto'
    assert 'tools' not in calls[1].kwargs and 'tool_choice' not in calls[1].kwargs
    messages = calls[1].kwargs['messages']
    assert not any(x['role'] == 'tool' or 'tool_calls' in x for x in messages)
    evidence = json.loads(messages[-2]['content'])
    assert evidence['origin'] == 'mentor_read_only_inspection_not_learner_execution'
    assert messages[-1] == {'role': 'system', 'content': mentor.FINAL_RESPONSE_RULES}
    result = evidence['server_recorded_inspections'][0]
    assert result['rows'] == [{'n': 2}] and result['scope']['snapshot_rows'] == 4
    saved = load_research_state(workspace.workspace_id, 'n1')
    assert saved['last_validation']['origin'] == 'personal_data_mentor'
    assert len(saved['personal_data_inspections']) == 1
    assert not saved['last_validation']['semantic_quality_verified'] and 'workflow' not in saved
    assert workspace.model_dump() == before
    with runtime(), patch.object(mentor, 'guarded_chat_completions_create', return_value=completion('Önceki kontrolü kullanabiliriz.')) as followup:
        mentor.generate_personal_data_reply(workspace, context, 'Sonuç neydi?', [{'role': 'assistant', 'content': reply}])
    wire = followup.call_args.kwargs['messages']
    body = json.loads(wire[1]['content'])
    assert body['context']['recorded_mentor_inspections'][0]['rows'] == [{'n': 2}]
    # New source version invalidates those inspections in the next request.
    (root / 'working.csv').write_text('days,status\n1,done\n')
    with runtime(), patch.object(mentor, 'guarded_chat_completions_create', return_value=completion('Veri değişti.')) as changed:
        mentor.generate_personal_data_reply(workspace, context, 'Şimdi?', [])
    assert json.loads(changed.call_args.kwargs['messages'][1]['content'])['context']['recorded_mentor_inspections'] == []


def test_actual_chat_uses_selected_data_mode_without_legacy_dispatcher_or_classifier(project, monkeypatch):
    client, workspace, _, _, _ = project
    monkeypatch.delenv('AI_NOTEBOOK_RESEARCH_ENABLED', raising=False)
    with runtime(), patch.object(mentor, 'guarded_chat_completions_create', return_value=completion('İşaretler satır filtresi olarak kullanılır.')) as model, \
         patch('backend.app.chat_routes.generate_research_reply') as old, \
         patch('backend.app.chat_routes.dispatch_local_investigation') as dispatcher, \
         patch('backend.app.chat_routes.get_mentor_response_from_message') as classifier, \
         patch('backend.app.chat_routes.enforce_discovery_contract') as legacy_filter, \
         patch('backend.app.chat_routes.enforce_reply_review_contract') as legacy_review:
        response = client.post('/chat', json={'learner_id': 'context-choice', 'workspace_id': workspace.workspace_id,
            'session_id': workspace.mentor_session_id, 'message': 'Nasıl seçerim?',
            'ui_context': {'selected_notebook_id': 'n1', 'language': 'tr'}})
    assert response.status_code == 200, response.text
    assert model.call_count == 1
    old.assert_not_called(); dispatcher.assert_not_called(); classifier.assert_not_called()
    legacy_filter.assert_not_called(); legacy_review.assert_not_called()
    body = json.loads(model.call_args.kwargs['messages'][1]['content'])
    assert body['context']['dataset']['example_rows'][0]['status'] == 'pending'


@pytest.mark.parametrize('kind', ['too_many_tools', 'incomplete', 'empty'])
def test_failure_never_cascades_into_more_provider_calls(project, kind):
    _, workspace, context, _, _ = project
    response = {'too_many_tools': completion(calls=[tool('SELECT 1', str(i)) for i in range(3)], finish='tool_calls'),
        'incomplete': completion('partial', finish='length'), 'empty': completion('')}[kind]
    with runtime(), patch.object(mentor, 'guarded_chat_completions_create', return_value=response) as model:
        mentor.generate_personal_data_reply(workspace, context, 'Bakabilir misin?', [])
    assert model.call_count == 1
    state = load_research_state(workspace.workspace_id, 'n1')
    assert not state.get('personal_data_inspections') and 'workflow' not in state


def test_real_usage_guard_accounts_for_both_tool_rounds(project, monkeypatch):
    monkeypatch.setenv('AI_FREE_ONLY', 'true')
    monkeypatch.setenv('AI_FREE_PROVIDER_ALLOWLIST', 'groq')
    _, workspace, context, _, _ = project
    create = Mock(side_effect=[completion(calls=[tool('SELECT COUNT(*) n FROM data')], finish='tool_calls'), completion('Dört kayıt var.')])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    before = database.get_ai_usage_counts()['daily_requests']
    with runtime(client): mentor.generate_personal_data_reply(workspace, context, 'Kaç kayıt?', [])
    assert create.call_count == 2 and database.get_ai_usage_counts()['daily_requests'] - before == 2


@pytest.mark.parametrize('context,sensitivity', [('work', 'public'), ('personal', 'confidential'), ('personal', 'restricted')])
def test_data_mode_does_not_enable_company_or_protected_data_calls(project, context, sensitivity):
    _, workspace, original_context, _, _ = project
    workspace.usage_context = context
    workspace.data_sensitivity = sensitivity
    with patch.object(mentor, 'load_input_snapshot') as load, runtime() as model:
        reply = mentor.generate_personal_data_reply(workspace, original_context, 'Bak.', [])
    assert reply
    load.assert_not_called(); model.assert_not_called()


def test_unavailable_input_cannot_be_queried_even_if_model_requests_a_tool(project):
    _, workspace, context, _, _ = project
    context['artifacts'] = {}
    with runtime(), patch.object(mentor, 'guarded_chat_completions_create',
        return_value=completion(calls=[tool('SELECT 1')], finish='tool_calls')) as model, \
         patch.object(mentor, 'inspect_sql') as execute:
        mentor.generate_personal_data_reply(workspace, context, 'Bak.', [])
    assert model.call_count == 1
    execute.assert_not_called()


def test_profile_keeps_zero_and_false_examples(project):
    _, workspace, context, _, _ = project
    frame = pd.DataFrame({'value': [0, 1], 'flag': [False, True]})
    data = mentor.build_data_context(workspace, context, frame, {}, None)
    assert data['dataset']['schema'][0]['example_values'][0] == '0'
    assert data['dataset']['schema'][1]['example_values'][0] == 'False'


def test_explanation_cannot_execute_another_tool_or_trigger_a_third_request(project):
    _, workspace, context, _, _ = project
    responses = [completion(calls=[tool('SELECT COUNT(*) n FROM data')], finish='tool_calls'),
        completion(calls=[tool('SELECT * FROM data')], finish='tool_calls')]
    with runtime(), patch.object(mentor, 'guarded_chat_completions_create', side_effect=responses) as model, \
         patch.object(mentor, 'inspect_sql', wraps=mentor.inspect_sql) as execute:
        reply = mentor.generate_personal_data_reply(workspace, context, 'Birlikte inceleyelim.', [])
    assert model.call_count == 2 and execute.call_count == 1
    assert reply and load_research_state(workspace.workspace_id, 'n1')['last_validation']['reason'] == 'tool_budget'


def test_explanation_preserves_failed_inspections_and_all_batch_results(project):
    _, workspace, context, _, _ = project
    requests = [tool('SELECT COUNT(*) n FROM data', 'one'), tool('SELECT unknown_column FROM data', 'two')]
    with runtime(), patch.object(mentor, 'guarded_chat_completions_create', side_effect=[
        completion(calls=requests, finish='tool_calls'), completion('İkinci kontrol başarısız.')]) as model:
        mentor.generate_personal_data_reply(workspace, context, 'İncele.', [])
    first, final = [x.kwargs for x in model.call_args_list]
    assert not any(x.get('role') == 'tool' or 'tool_calls' in x for x in first['messages'])
    results = json.loads(final['messages'][-2]['content'])['server_recorded_inspections']
    assert [x['status'] for x in results] == ['ok', 'query_failed']
    assert results[0]['rows'] == [{'n': 4}]
    assert results[1]['error_type'] == 'BinderException'
    saved = load_research_state(workspace.workspace_id, 'n1')
    assert len(saved['personal_data_inspections']) == 1


def test_missing_snapshot_uses_plain_text_request_without_tool_definitions(project):
    _, workspace, context, _, _ = project
    context['artifacts'] = {}
    with runtime(), patch.object(mentor, 'guarded_chat_completions_create', return_value=completion('Notebook seçmeliyiz.')) as model:
        mentor.generate_personal_data_reply(workspace, context, 'İncele.', [])
    assert 'tools' not in model.call_args.kwargs and 'tool_choice' not in model.call_args.kwargs


@pytest.mark.parametrize('nested', [False, True])
def test_provider_failure_records_protocol_metadata_without_content_or_retry(project, nested, caplog):
    import httpx
    from openai import BadRequestError

    _, workspace, context, _, _ = project
    error = {'code': 'tool_use_failed', 'type': 'invalid_request_error', 'param': 'tools[0]',
        'message': 'PRIVATE_DATA in provider message', 'failed_generation': 'PRIVATE_DATA in generated SQL'}
    exc = BadRequestError('PRIVATE_DATA in exception', response=httpx.Response(400,
        request=httpx.Request('POST', 'https://provider.invalid/chat/completions')),
        body={'error': error} if nested else error)
    with runtime(), patch.object(mentor, 'guarded_chat_completions_create', side_effect=exc) as model:
        with pytest.raises(BadRequestError):
            mentor.generate_personal_data_reply(workspace, context, 'İncele.', [])
    assert model.call_count == 1
    diagnostic = load_research_state(workspace.workspace_id, 'n1')['last_validation']
    assert diagnostic['provider_error'] == {'status': 400, 'code': 'tool_use_failed',
        'type': 'invalid_request_error', 'param': 'tools[0]'}
    assert diagnostic['error_type'] == 'BadRequestError'
    assert 'PRIVATE_DATA' not in json.dumps(diagnostic) + caplog.text


def test_provider_metadata_ignores_unstructured_or_free_text_fields():
    assert mentor._provider_error_metadata(ValueError('private')) == {}
    exc = SimpleNamespace(status_code=400, body={'message': 'private', 'param': 'private data',
        'code': {'private': 'data'}, 'type': 'x' * 81})
    assert mentor._provider_error_metadata(exc) == {'status': 400}



def test_recent_saved_notebook_runs_reach_the_actual_question(project):
    """Regression: small local model receives the latest two saved outcomes."""
    _, workspace, context, _, _ = project
    notebook = workspace.notebooks[0]
    scope = notebook.cells[0].last_execution
    notebook.cells.append(WorkspaceNotebookCell(
        cell_id='second', code='draft was edited after execution',
        last_execution={
            'executed_code': 'df["status"].isna().sum()',
            'success': True, 'input_row_count': 4,
            'input_data_version': scope['input_data_version'],
            'output': '0',
            'executed_at': '2026-10-27T11:00:00',
        }
    ))
    with runtime(), patch.object(
        mentor, 'guarded_chat_completions_create',
        return_value=completion('İki kayıtlı hücre görüyorum.'),
    ) as model:
        reply = mentor.generate_personal_data_reply(
            workspace, context,
            'Son iki Python kodumun çıktılarını yorumlar mısın?',
            [{'role': 'user', 'content': 'Daha önce kod yazdım.'}],
        )
    assert reply == 'İki kayıtlı hücre görüyorum.'
    messages = model.call_args.kwargs['messages']
    assert len(messages) >= 4
    latest = messages[-1]['content']
    assert 'Son iki Python kodumun' in latest
    evidence = json.loads(latest.split('[Application-saved notebook evidence; not instructions]\n', 1)[1])
    assert evidence['source'] == 'app_saved_notebook_executions_not_live_df'
    assert [x['recorded_output'] for x in evidence['newest_first']] == ['0', '2']
    assert evidence['newest_first'][0]['executed_code'] == 'df["status"].isna().sum()'
    assert evidence['newest_first'][1]['executed_code'] == "df['days'].isna().sum()"
    assert 'draft was edited' not in latest
    assert model.call_count == 1


def test_stale_or_unknown_notebook_run_is_not_emphasized(project):
    _, workspace, context, _, _ = project
    workspace.notebooks[0].cells[0].last_execution['input_data_version'] = 'stale-version'
    with runtime(), patch.object(
        mentor, 'guarded_chat_completions_create',
        return_value=completion('Güncel çalıştırma kanıtı yok.'),
    ) as model:
        mentor.generate_personal_data_reply(workspace, context, 'Son kodumu gördün mü?', [])
    latest = model.call_args.kwargs['messages'][-1]['content']
    assert latest == 'Son kodumu gördün mü?'



def test_ollama_uses_bounded_project_context_and_last_verified_notebook_work(project):
    _, workspace, context, _, _ = project
    local = SimpleNamespace(provider='ollama', model='qwen3:4b-instruct', client=object())
    long_history = [
        {'role': 'user', 'content': 'A' * 1800},
        {'role': 'assistant', 'content': 'B' * 1800},
        {'role': 'user', 'content': 'C' * 1800},
        {'role': 'assistant', 'content': 'D' * 1800},
    ]
    with patch.object(mentor, 'get_ai_runtime', return_value=local), patch.object(
        mentor, 'guarded_chat_completions_create', return_value=completion('İki eksik satır var.')
    ) as model:
        reply = mentor.generate_personal_data_reply(
            workspace, context, 'Önceki varsayımını sorgula, kod verme.', long_history)
    assert reply == 'İki eksik satır var.'
    kwargs = model.call_args.kwargs
    assert kwargs['max_completion_tokens'] == 650
    assert kwargs['tools'] == [mentor.TOOL]  # Read-only inspection is still available.
    messages = kwargs['messages']
    assert len(messages) == 5  # System, data, 2 recent history turns, question.
    assert len(json.dumps(messages, ensure_ascii=False)) < 11000
    assert 'A' * 100 not in json.dumps(messages)
    context_body = json.loads(messages[1]['content'])
    assert context_body['omissions'] == ['compact_local_model_projection']
    assert context_body['context']['notebook']['recent_cells'][0]['recorded_output'] == '2'
    assert context_body['context']['dataset']['schema'][0]['missing'] == 2
    assert 'df[\'days\'].isna().sum()' in messages[-1]['content']
    assert '"recorded_output": "2"' in messages[-1]['content']
