"""Exercise persisted notebook -> real context -> real mentor -> persisted task."""
import json
from unittest.mock import patch

import pandas as pd
import pytest

from backend.app import database
from backend.app.mentor_research_store import load_research_state
from backend.app.models import WorkspaceNotebook, WorkspaceNotebookCell
from backend.app.notebook_scope_service import notebook_input_version


@pytest.mark.parametrize('target,helper', [
    ('temperature', 'offline'), ('delivery_days', 'returned'),
    ('response_seconds', 'closed'),
])
def test_saved_notebook_guidance_uses_actual_context_and_advances_only_after_execution(
    tmp_path, monkeypatch, target, helper,
):
    monkeypatch.setenv('AI_NOTEBOOK_RESEARCH_ENABLED', 'true')
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'chat.sqlite')
    monkeypatch.setattr('backend.app.workspace_data_service.get_workspace_data_dir', lambda _: tmp_path)
    monkeypatch.setattr('backend.app.notebook_scope_service.get_workspace_data_dir', lambda _: tmp_path)
    database.init_db()
    from fastapi.testclient import TestClient
    from backend.app.main import app
    client = TestClient(app)
    database.insert_learner_profile(learner_id='saved', answer_length='concise',
                                   learning_style='guided', code_support='medium')
    created = client.post('/workspaces', json={
        'learner_id': 'saved', 'title': 'Saved notebook integration',
        'workspace_type': 'data_engineering',
    })
    assert created.status_code == 200, created.text
    workspace = database.get_workspace(workspace_id=created.json()['workspace_id'], learner_id='saved')
    frame = pd.DataFrame({target: [None if i % 2 == 0 else float(i) for i in range(10000)],
                          helper: [i % 3 == 0 for i in range(10000)]})
    frame.to_csv(tmp_path / 'working.csv', index=False)
    workspace.development_sample_size = 10000
    workspace.dataset_profile = {'columns': list(frame.columns), 'row_count': len(frame)}
    notebook = WorkspaceNotebook(notebook_id='n1', name='Analysis', dataset_kind='working',
                                 created_at='2026-10-21', updated_at='2026-10-21', cells=[])
    version = notebook_input_version(workspace.workspace_id, notebook, 10000)
    assert version
    scope = dict(success=True, input_row_count=10000, input_total_row_count=10000,
                 input_data_version=version, dataset_kind='working')
    notebook.cells = [WorkspaceNotebookCell(
        cell_id='count', code=f'df["{target}"].isna().sum()',
        last_execution={**scope, 'output': str(int(frame[target].isna().sum())),
                        'executed_at': '2026-10-21T10:00:00'},
    )]
    workspace.notebooks = [notebook]
    database.save_workspace(workspace=workspace)
    request = dict(learner_id='saved', workspace_id=workspace.workspace_id,
                   session_id=workspace.mentor_session_id,
                   ui_context={'selected_notebook_id': 'n1', 'workbench_view': 'notebook', 'language': 'tr'})

    def chat(message):
        response = client.post('/chat', json={**request, 'message': message})
        assert response.status_code == 200, response.text
        return response.json()['reply'], load_research_state(workspace.workspace_id, 'n1')

    with patch('backend.app.mentor_research_service.get_ai_runtime') as provider, \
         patch('backend.app.chat_routes.get_mentor_response_from_message') as legacy:
        reply, state = chat(f'{target} sayımını yaptım. Veri sözlüğüm yok; sonraki tek adımı söyle.')
        assert state['last_validation']['accepted'], reply
        assert state['proposals'][-1]['status'] == 'proposed'
        pending = dict(state['proposals'][-1])
        latest = next(o for o in state['observations'] if o['cell_id'] == 'count')
        assert latest['output'] == '5000' and latest['input_rows'] == 10000
        assert latest['version_verified'] and not latest['stale_scope']
        reply, state = chat('Bunu nasıl yapacağımı bilmiyorum. Kodu gösterme; ipucu ver.')
        assert 'Aynı adım için ipucu' in reply and '```' not in reply
        assert state['proposals'][-1] == pending

        # Save a known, read-only equivalent expression, not arbitrary agent code.
        selected = frame.loc[frame[target].isna()].head(5)
        rows = json.loads(selected.to_json(orient='records'))
        notebook.cells.insert(0, WorkspaceNotebookCell(
            cell_id='preview', code=f'df.loc[df["{target}"].isna()].head()',
            last_execution={**scope, 'output': selected.to_string(), 'preview_rows': rows,
                            'executed_at': '2026-10-21T10:01:00'},
        ))
        # Latest execution is deliberately not the last cell in visual order.
        workspace.notebooks = [notebook]
        database.save_workspace(workspace=workspace)
        reply, state = chat('İstenen örnekleri görüntüledim. Sonuçtan sonra sıradaki tek adım ne?')
        assert state['last_validation']['accepted'], reply
        assert any(p['code'] == pending['code'] and p['status'] == 'observed'
                   for p in state['proposals'])
        action = state['proposals'][-1]
        assert action['status'] == 'proposed' and action['code'] != pending['code']
        assert helper in action['code'] and 'value_counts' in action['code']
        assert state['focus_column'] == target
        latest = next(o for o in state['observations'] if o['cell_id'] == 'preview')
        assert latest['preview_rows'] == rows and latest['input_rows'] == 10000
        assert latest['version_verified'] and not latest['stale_scope']

        # A changed selection must invalidate the recorded 10k execution;
        # asking for help must not show the old task's code as current work.
        proposals = state['proposals']
        workspace.development_sample_size = 5000
        database.save_workspace(workspace=workspace)
        reply, state = chat('Kodu göster. Bunu nasıl yapacağım?')
        assert not state['last_validation']['accepted']
        assert 'güncel değil' in reply and '```' not in reply
        assert state['proposals'] == proposals
        assert all(o['stale_scope'] for o in state['observations'])
        provider.assert_not_called()
        legacy.assert_not_called()
