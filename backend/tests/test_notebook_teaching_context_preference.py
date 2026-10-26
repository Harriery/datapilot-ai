"""Scoped, explicit question/code sharing. All data and model replies invented."""
import json
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from backend.app import database
from backend.app.mentor_adaptive_teaching_service import build_teaching_request
from backend.app.mentor_research_service import generate_research_reply
from backend.app.mentor_research_store import load_research_state
from backend.tests.test_mentor_adaptive_teaching import setup_task, lesson, runtime, provider


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'context-choice.sqlite')
    database.init_db()


def client_workspace(**changes):
    from backend.app.main import app
    client = TestClient(app)
    database.insert_learner_profile(learner_id='context-choice', answer_length='concise', learning_style='guided', code_support='medium')
    response = client.post('/workspaces', json={
        'learner_id': 'context-choice', 'title': 'Invented teaching workspace',
        'usage_context': 'personal',
        'mentor_setup': {'intent': 'portfolio', 'experience_level': 'beginner', 'approach': 'guided', 'learning_focus': ['python', 'quality']},
        **changes,
    })
    assert response.status_code == 200, response.text
    return client, response.json()


def test_preference_persists_without_reclassifying_data_or_changing_other_project_state():
    client, before = client_workspace()
    workspace_id = before['workspace_id']
    response = client.patch(f'/workspaces/context-choice/{workspace_id}/notebook-teaching', json={'mode': 'question_and_code'})
    assert response.status_code == 200, response.text
    saved = database.get_workspace(workspace_id=workspace_id, learner_id='context-choice').model_dump()
    assert saved['mentor_setup']['notebook_teaching_context'] == 'question_and_code'
    assert saved['data_sensitivity'] is None
    assert saved['mentor_setup']['learning_focus'] == ['python', 'quality']
    for key in ('notebooks', 'dataset_profile', 'checkpoint', 'project_deliverables', 'mentor_session_id'):
        assert saved[key] == before[key]
    response = client.patch(f'/workspaces/context-choice/{workspace_id}/notebook-teaching', json={'mode': 'generic'})
    assert response.status_code == 200
    assert response.json()['mentor_setup']['notebook_teaching_context'] == 'generic'


@pytest.mark.parametrize('context,sensitivity,status', [
    ('work', 'public', 403), ('work', 'internal', 403),
    ('personal', 'confidential', 409), ('personal', 'restricted', 409),
])
def test_preference_does_not_bypass_protected_data_or_work_policy(context, sensitivity, status):
    client, workspace = client_workspace(usage_context=context, data_sensitivity=sensitivity)
    response = client.patch(f"/workspaces/context-choice/{workspace['workspace_id']}/notebook-teaching", json={'mode': 'question_and_code'})
    assert response.status_code == status
    saved = database.get_workspace(workspace_id=workspace['workspace_id'], learner_id='context-choice')
    assert saved.data_sensitivity == sensitivity
    assert saved.mentor_setup is None or saved.mentor_setup.notebook_teaching_context is None


def test_preference_endpoint_checks_workspace_owner_and_rejects_unrelated_updates():
    client, workspace = client_workspace()
    path = f"/workspaces/context-choice/{workspace['workspace_id']}/notebook-teaching"
    assert client.patch(path.replace('context-choice', 'another-learner'), json={'mode': 'question_and_code'}).status_code == 404
    assert client.patch(path, json={'mode': 'public'}).status_code == 422
    assert client.patch(path, json={'mode': 'question_and_code', 'data_sensitivity': 'public'}).status_code == 422
    assert client.patch(path, json={}).status_code == 422


def test_explicit_personal_choice_preserves_real_question_current_expression_and_surface():
    context, state, step = setup_task()
    context['teaching_data_policy']['data_sensitivity'] = None
    context['mentor_setup']['notebook_teaching_context'] = 'question_and_code'
    message = 'isna ile sum arasındaki farkı son hücrem üzerinden açıkla; Explorer istemiyorum, kodu verme.'
    answer = lesson(step, explanation='isna boş hücreleri işaretler; sum bu işaretleri sayar. Satır seçimi için işaretleri satır filtresi olarak kullanırız.')
    with runtime(), provider(answer) as model:
        reply = generate_research_reply(context, message, [])
    payload = json.loads(model.call_args.kwargs['input'])
    assert payload['learner_question'] == message
    assert payload['execution_surface'] == 'python_notebook'
    assert payload['latest_verified_expression'] == "df['delivery_days'].isna().sum()"
    assert payload['completed_operations'][0]['operation'] == 'missing_count'
    assert payload['task_contract']['operation'] == 'distribution'
    assert '250' not in model.call_args.kwargs['input']  # no measured output
    after = load_research_state(context['workspace_id'], 'n1')
    assert after['last_validation']['teaching_context_mode'] == 'user_shared_question_and_code'
    assert after['last_validation']['teaching_accepted'] and after['proposals'] == state['proposals']
    assert 'isna boş hücreleri' in reply and '```' not in reply
    with runtime(), provider(lesson(step, explanation='Sayım sonucu tek bir miktardır; seçim ise ilgili kayıtları getirir.')) as second:
        generate_research_reply(context, 'sum kısmını neden çıkarmalıyım? Kodu verme.', [])
    followup = json.loads(second.call_args.kwargs['input'])
    assert followup['previous_explanations'][0]['question'] == message
    assert 'sum' in followup['learner_question']


def test_turning_sharing_off_excludes_previous_questions_schema_and_expression():
    context, state, step = setup_task()
    context['teaching_data_policy']['data_sensitivity'] = None
    context['mentor_setup']['notebook_teaching_context'] = 'question_and_code'
    with runtime(), provider(lesson(step)):
        generate_research_reply(context, 'private-message-canary, isna ve sum?', [])
    context['mentor_setup']['notebook_teaching_context'] = 'generic'
    with runtime(), provider(lesson(step, task_id='pending-task', first_action='Önce FIELD_A boş olan satırları düşün.')) as model:
        generate_research_reply(context, 'private-second-question. Daha basit anlat.', [])
    outbound = model.call_args.kwargs['input']
    for secret in ('private-message-canary', 'private-second-question', 'delivery_days', 'shipment_status', 'latest_verified_expression'):
        assert secret not in outbound
    assert json.loads(outbound)['previous_explanations'] == []


@pytest.mark.parametrize('sensitivity', ['confidential', 'restricted'])
def test_saved_sharing_preference_is_denied_after_data_protection_changes(sensitivity):
    context, state, step = setup_task()
    context['teaching_data_policy']['data_sensitivity'] = sensitivity
    context['mentor_setup']['notebook_teaching_context'] = 'question_and_code'
    with runtime() as model, provider(lesson(step)) as service:
        generate_research_reply(context, 'isna ve sum farkı nedir?', [])
    model.assert_not_called()
    service.assert_not_called()
    assert load_research_state(context['workspace_id'], 'n1')['last_validation']['reason'] == 'external_ai_policy'


def test_verified_expression_strips_comments_and_unknown_attempts_never_export_raw_code():
    context, state, step = setup_task()
    current = state['observations'][0]
    current['code'] += ' # private-comment-canary'
    payload = build_teaching_request(context, state, step, 'Açıkla.')
    assert 'private-comment-canary' not in json.dumps(payload)
    current['analysis_contract'] = {'supported': False}
    current['code'] = "secret_token = 'private-token-canary'"
    payload = build_teaching_request(context, state, step, 'Açıkla.')
    assert payload['latest_verified_expression'] is None
    assert 'private-token-canary' not in json.dumps(payload)


def test_generic_preference_is_honored_even_for_public_data():
    context, state, step = setup_task()
    context['mentor_setup']['notebook_teaching_context'] = 'generic'
    with runtime(), provider(lesson(step, task_id='pending-task', first_action='Önce FIELD_A boş olan satırları düşün.')) as model:
        generate_research_reply(context, 'private-question-canary', [])
    assert 'private-question-canary' not in model.call_args.kwargs['input']
    assert load_research_state(context['workspace_id'], 'n1')['last_validation']['teaching_context_mode'] == 'generic_concepts_only'


def test_saved_project_choice_flows_through_actual_workspace_context_and_chat(tmp_path, monkeypatch):
    import pandas as pd
    from backend.app.models import WorkspaceNotebook, WorkspaceNotebookCell
    from backend.app.notebook_scope_service import notebook_input_version
    from backend.app.mentor_adaptive_teaching_service import TeachingExplanation
    monkeypatch.setenv('AI_NOTEBOOK_RESEARCH_ENABLED', 'true')
    monkeypatch.setattr('backend.app.workspace_data_service.get_workspace_data_dir', lambda _: tmp_path)
    monkeypatch.setattr('backend.app.notebook_scope_service.get_workspace_data_dir', lambda _: tmp_path)
    client, created = client_workspace()
    workspace = database.get_workspace(workspace_id=created['workspace_id'], learner_id='context-choice')
    frame = pd.DataFrame({'measure': [None if i % 2 == 0 else i for i in range(1000)], 'status': [i % 3 for i in range(1000)]})
    frame.to_csv(tmp_path / 'working.csv', index=False)
    workspace.development_sample_size = 1000
    workspace.dataset_profile = {'columns': list(frame.columns), 'row_count': len(frame)}
    notebook = WorkspaceNotebook(notebook_id='n1', name='Investigation', dataset_kind='working', created_at='2026-10-26', updated_at='2026-10-26', cells=[])
    version = notebook_input_version(workspace.workspace_id, notebook, 1000)
    notebook.cells = [WorkspaceNotebookCell(cell_id='count', code='df["measure"].isna().sum()', last_execution={
        'success': True, 'input_row_count': 1000, 'input_total_row_count': 1000,
        'input_data_version': version, 'dataset_kind': 'working', 'output': '500', 'executed_at': '2026-10-26T10:00:00'})]
    workspace.notebooks = [notebook]
    database.save_workspace(workspace=workspace)
    request = {'learner_id': 'context-choice', 'workspace_id': workspace.workspace_id, 'session_id': workspace.mentor_session_id,
        'ui_context': {'selected_notebook_id': 'n1', 'workbench_view': 'notebook', 'language': 'tr'}}
    first = client.post('/chat', json={**request, 'message': 'measure sayımını yaptım. Veri sözlüğüm yok; sonraki tek adımı söyle.'})
    assert first.status_code == 200, first.text
    before = load_research_state(workspace.workspace_id, 'n1')
    task = before['workflow']['active_step']
    response = client.patch(f'/workspaces/context-choice/{workspace.workspace_id}/notebook-teaching', json={'mode': 'question_and_code'})
    assert response.status_code == 200
    message = 'isna ile sumun farkını son hücrem üzerinden açıkla. Kodu verme.'
    reply = TeachingExplanation(task_id=task['id'], approach='contrast',
        explanation='isna boş hücreleri işaretler; sum bu işaretleri sayar.',
        first_action='Önce measure boş olan satırları seçen koşulu düşün.', why='İlgili satır grubunu ayırmak için.')
    with runtime(), provider(reply) as model, patch('backend.app.chat_routes.get_mentor_response_from_message') as legacy:
        response = client.post('/chat', json={**request, 'message': message})
    assert response.status_code == 200, response.text
    payload = json.loads(model.call_args.kwargs['input'])
    assert payload['learner_question'] == message
    assert payload['latest_verified_expression'] == "df['measure'].isna().sum()"
    assert payload['execution_surface'] == 'python_notebook'
    after = load_research_state(workspace.workspace_id, 'n1')
    assert after['last_validation']['teaching_context_mode'] == 'user_shared_question_and_code'
    assert after['proposals'] == before['proposals']
    assert after['workflow']['active_step']['id'] == task['id']
    legacy.assert_not_called()
