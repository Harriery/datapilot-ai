"""Regression coverage for scope selection and stale Explorer routing."""
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import pytest

from backend.app.mentor_action_evidence_service import record_action_evidence
from backend.app.mentor_local_dispatcher_service import dispatch_local_investigation
from backend.app.mentor_prompt_context_service import compact_mentor_workspace_context
from backend.app.workspace_routes import get_workspace_notebook_data


def workspace_with_preview(path, target="old_field"):
    stat = path.stat()
    workspace = SimpleNamespace(action_evidence_events=[])
    record_action_evidence(
        workspace, action="preview_investigation", dataset="working",
        parameters={"filters": [{"column": target, "operator": "is_missing"}]},
        result={"total_rows": 4, "matching_rows": 1},
        data_version=f"{stat.st_size}:{stat.st_mtime_ns}",
    )
    return workspace


@pytest.mark.parametrize("field", ["AIR_SYSTEM_DELAY", "sensor_value", "customer_age"])
@pytest.mark.parametrize("question", [
    "{field} icin isna kullanarak yazdim cikan sonucu gordun mu dogru yapmismiyim",
    "{field} için sırada neyi kontrol edeyim?",
    "What does {field} mean?",
    "Review my {field} notebook output without giving code.",
])
def test_named_field_does_not_inherit_old_target(tmp_path, field, question):
    path = tmp_path / "working.csv"
    pd.DataFrame({"old_field": [None, 1], field: [None, 2]}).to_csv(path, index=False)
    workspace = workspace_with_preview(path)
    result = dispatch_local_investigation(workspace, question.format(field=field), path)
    assert result["status"] == "not_applicable"
    assert len(workspace.action_evidence_events) == 1


def test_explicit_pair_wins_over_old_preview(tmp_path):
    path = tmp_path / "working.csv"
    pd.DataFrame({"old_field": [None, 1], "new_field": [1, None]}).to_csv(path, index=False)
    workspace = workspace_with_preview(path)
    result = dispatch_local_investigation(
        workspace, "new_field sütunundaki eksikleri old_field ile karşılaştır", path,
    )
    assert result["status"] == "verified"
    assert result["evidence"]["target_column"] == "new_field"


def test_notebook_comparison_does_not_silently_use_working_data(tmp_path):
    path = tmp_path / "working.csv"
    pd.DataFrame({"old_field": [None, 1], "flag": [0, 1]}).to_csv(path, index=False)
    workspace = workspace_with_preview(path)
    result = dispatch_local_investigation(
        workspace, "old_field sütunundaki eksikleri flag ile karşılaştır", path,
        ui_context={"selected_notebook_id": "n1", "workbench_view": "notebook"},
    )
    assert result == {"status": "not_applicable", "reason": "use_notebook_evidence"}
    assert len(workspace.action_evidence_events) == 1


@pytest.mark.parametrize("kind", ["working", "raw", "processed"])
@pytest.mark.parametrize("size", [1000, 10000])
def test_notebook_honors_selected_scope(kind, size):
    notebook = SimpleNamespace(notebook_id="n1", dataset_kind=kind, processed_dataset_id="p1")
    workspace = SimpleNamespace(
        notebooks=[notebook], development_sample_size=size,
        development_sample_row_count=size, development_sample_max_size=50000,
        dataset_storage_mode="pandas",
    )
    frame = pd.DataFrame({"value": range(12000)})
    with patch("backend.app.workspace_routes.database.get_workspace", return_value=workspace), \
         patch("backend.app.workspace_routes.load_workspace_working_dataframe", return_value=frame), \
         patch("backend.app.workspace_routes.load_workspace_source_dataframe", return_value=frame), \
         patch("backend.app.workspace_routes.load_workspace_processed_dataset", return_value=frame):
        result = get_workspace_notebook_data("learner", "w1", "n1")
    assert result.row_count == size
    assert len(result.rows) == size
    assert result.total_row_count == 12000
    assert result.sampled is True


def test_duckdb_notebook_honors_selected_scope():
    workspace = SimpleNamespace(
        notebooks=[SimpleNamespace(notebook_id="n1", dataset_kind="raw")],
        development_sample_size=10000, development_sample_row_count=10000,
        development_sample_max_size=50000, dataset_storage_mode="duckdb",
    )
    with patch("backend.app.workspace_routes.database.get_workspace", return_value=workspace), \
         patch("backend.app.workspace_routes.get_workspace_source_path", return_value="source.csv"), \
         patch("backend.app.workspace_routes.load_large_source_sample", return_value=(pd.DataFrame({"x": range(10000)}), 5819079)) as load:
        result = get_workspace_notebook_data("learner", "w1", "n1")
    assert load.call_args.kwargs["limit"] == 10000
    assert result.row_count == 10000
    assert result.total_row_count == 5819079


def test_compaction_preserves_old_execution_scope_after_selection_changes():
    context = {"artifacts": {"selected_notebook": {
        "notebook_id": "n1", "configured_development_rows": 10000,
        "latest_cell": {"code": 'df["sensor"].isna().sum()', "last_execution": {
            "success": True, "output": "4123", "input_row_count": 5000,
            "input_total_row_count": 10000, "dataset_kind": "working",
        }},
        "quality_checks": [{"title": "Earlier check", "status": "recorded",
                            "sample_row_count": 5000, "total_row_count": 10000}],
    }}}
    selected = compact_mentor_workspace_context(context)["artifacts"]["selected_notebook"]
    assert selected["configured_development_rows"] == 10000
    assert selected["latest_cell"]["last_execution"]["input_row_count"] == 5000
    assert selected["quality_checks"][0]["status"] == "recorded"
    del context["artifacts"]["selected_notebook"]["latest_cell"]
    selected = compact_mentor_workspace_context(context)["artifacts"]["selected_notebook"]
    assert selected["latest_cell"] is None
    assert selected["quality_checks"][0]["sample_row_count"] == 5000


def test_chat_reviews_saved_notebook_instead_of_old_explorer_filter(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_NOTEBOOK_RESEARCH_ENABLED", "true")
    from fastapi.testclient import TestClient
    import backend.app.database as database
    from backend.app.main import app

    with patch.object(database, "DATABASE_PATH", tmp_path / "chat.db"):
        database.init_db()
        database.insert_learner_profile(
            learner_id="scope-review", answer_length="concise",
            learning_style="guided", code_support="medium",
        )
        client = TestClient(app)
        created = client.post("/workspaces", json={
            "learner_id": "scope-review", "title": "Independent sensor project",
            "workspace_type": "data_engineering",
        }).json()
        workspace = database.get_workspace(
            workspace_id=created["workspace_id"], learner_id="scope-review",
        )
        from backend.app.models import WorkspaceNotebook, WorkspaceNotebookCell
        workspace.notebooks = [WorkspaceNotebook(
            notebook_id="n1", name="Analysis", dataset_kind="working",
            created_at="2026-10-18", updated_at="2026-10-18",
            cells=[WorkspaceNotebookCell(cell_id="c1", code='df["sensor_value"].isna().sum()', last_execution={
                "success": True, "output": "1", "input_row_count": 5000,
                "dataset_kind": "working", "executed_at": "2026-10-18",
            })],
        )]
        workspace.development_sample_size = 10000
        path = tmp_path / "working.csv"
        pd.DataFrame({"old_field": [None, 1], "sensor_value": [None, 2]}).to_csv(path, index=False)
        workspace.action_evidence_events = workspace_with_preview(path).action_evidence_events
        database.save_workspace(workspace=workspace)
        with patch("backend.app.workspace_data_service.get_workspace_data_dir", return_value=tmp_path), \
             patch("backend.app.chat_routes._deterministic_workspace_guidance", return_value=None), \
             patch("backend.app.chat_routes.generate_research_reply", return_value="Notebook observation reviewed.") as mentor:
            response = client.post("/chat", json={
                "learner_id": "scope-review", "workspace_id": workspace.workspace_id,
                "session_id": workspace.mentor_session_id,
                "message": "sensor_value icin isna kullanarak yazdim dogru yapmismiyim?",
                "ui_context": {"selected_notebook_id": "n1", "workbench_view": "notebook"},
            })
        assert response.status_code == 200, response.text
        assert response.json()["reply"] == "Notebook observation reviewed."
        context = mentor.call_args.args[0]
        assert context["local_investigation"]["status"] == "not_applicable"
        notebook = context["artifacts"]["selected_notebook"]
        assert notebook["latest_cell"]["last_execution"]["input_row_count"] == 5000
        assert notebook["configured_development_rows"] == 10000
