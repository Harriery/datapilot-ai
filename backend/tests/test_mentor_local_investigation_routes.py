import pandas as pd
import pytest
from fastapi.testclient import TestClient

import backend.app.database as database
from backend.app.main import app
from backend.app.workspace_data_service import save_workspace_working_dataframe
import backend.app.workspace_data_service as data_service

client = TestClient(app)


@pytest.fixture
def sample_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")
    monkeypatch.setattr(data_service, "WORKSPACE_DATA_ROOT", tmp_path / "workspaces")
    database.init_db()
    database.insert_learner_profile(
        learner_id="evidence-learner",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )
    response = client.post(
        "/workspaces",
        json={
            "learner_id": "evidence-learner",
            "title": "Generic Missingness Study",
            "workspace_type": "data_engineering",
        },
    )
    assert response.status_code == 200
    workspace_id = response.json()["workspace_id"]
    save_workspace_working_dataframe(
        workspace_id,
        pd.DataFrame({
            "flag": [0, 0, 1, 1],
            "optional_text": [None, None, "yes", None],
        }),
    )
    return workspace_id


def test_investigation_endpoint_records_verified_evidence(sample_workspace):
    path = (
        f"/workspaces/evidence-learner/{sample_workspace}"
        "/mentor/investigate-missingness"
    )
    body = {
        "target_column": "optional_text",
        "group_column": "flag",
    }
    response = client.post(path, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["total_missing"] == 3
    assert response.json()["business_rule_confirmed"] is False
    workspace = database.get_workspace(
        sample_workspace, "evidence-learner"
    )
    assert len(workspace.action_evidence_events) == 1
    assert workspace.action_evidence_events[0]["origin"] == "backend"

    repeated = client.post(path, json=body)
    assert repeated.status_code == 200
    workspace = database.get_workspace(
        sample_workspace, "evidence-learner"
    )
    assert len(workspace.action_evidence_events) == 1


def test_investigation_invalid_column_does_not_record(sample_workspace):
    path = (
        f"/workspaces/evidence-learner/{sample_workspace}"
        "/mentor/investigate-missingness"
    )
    response = client.post(
        path,
        json={"target_column": "unknown", "group_column": "flag"},
    )
    assert response.status_code == 400
    workspace = database.get_workspace(
        sample_workspace, "evidence-learner"
    )
    assert workspace.action_evidence_events == []
