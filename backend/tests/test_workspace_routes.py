from fastapi.testclient import TestClient

import backend.app.database as database

import backend.app.workspace_routes as workspace_routes

from backend.app.models import (
    DataQualityAnalysis,
)

from backend.app.main import app


client = TestClient(app)


def prepare_database(tmp_path):
    database.DATABASE_PATH = (
        tmp_path / "test.db"
    )

    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )


def test_create_workspace(tmp_path):
    prepare_database(tmp_path)

    response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Data Quality",

            "usage_context": "work",
            "organization_id": "company-001",
            "data_sensitivity": "internal",

            "workspace_type": "data_engineering",
            "current_task_id": "task-001",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["learner_id"] == "learner-001"
    assert body["title"] == "Customer Data Quality"

    assert (
        body["workspace_type"]
        == "data_engineering"
    )

    assert body["workspace_id"] is not None
    assert body["mentor_session_id"] is not None

    assert (
        body["checkpoint"]["completed_items"]
        == []
    )

    assert body["usage_context"] == "work"

    assert (
        body["organization_id"]
        == "company-001"
    )

    assert (
        body["data_sensitivity"]
        == "internal"
    )


def test_list_workspaces(tmp_path):
    prepare_database(tmp_path)

    client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Data Quality",
            "workspace_type": "data_engineering",
        },
    )

    client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "SQL Practice",
            "workspace_type": "practice",
        },
    )

    response = client.get(
        "/workspaces/learner-001"
    )

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 2


def test_get_workspace(tmp_path):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Data Quality",
            "workspace_type": "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    response = client.get(
        f"/workspaces/learner-001/{workspace_id}"
    )

    assert response.status_code == 200

    body = response.json()

    assert (
        body["workspace_id"]
        == workspace_id
    )


def test_get_workspace_returns_404_for_wrong_learner(
    tmp_path,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Data Quality",
            "workspace_type": "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    response = client.get(
        f"/workspaces/wrong-learner/{workspace_id}"
    )

    assert response.status_code == 404

def test_update_workspace_checkpoint(tmp_path):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Data Quality",
            "workspace_type": "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    response = client.put(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/checkpoint"
        ),
        json={
            "checkpoint": {
                "completed_items": [
                    "Duplicate kayıtlar temizlendi.",
                    "Duplicate validation başarılı.",
                ],
                "current_focus": (
                    "age kolonundaki null değerler"
                ),
                "blocked_reason": (
                    "Imputation yöntemi seçilmedi."
                ),
                "last_error": (
                    "Null sayısı azalmadı."
                ),
                "next_actions": [
                    "age dağılımını incele",
                    "transformation seç",
                    "sonucu validate et",
                ],
            }
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert (
        body["checkpoint"]["current_focus"]
        == "age kolonundaki null değerler"
    )

    assert (
        body["checkpoint"]["last_error"]
        == "Null sayısı azalmadı."
    )


def test_resume_workspace_returns_checkpoint(
    tmp_path,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Data Quality",
            "workspace_type": "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    client.put(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/checkpoint"
        ),
        json={
            "checkpoint": {
                "completed_items": [
                    "Duplicate temizlendi."
                ],
                "current_focus": (
                    "age null değerleri"
                ),
                "blocked_reason": None,
                "last_error": (
                    "Null sayısı azalmadı."
                ),
                "next_actions": [
                    "age dağılımını incele",
                    "transformation uygula",
                ],
            }
        },
    )

    response = client.get(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/resume"
        )
    )

    assert response.status_code == 200

    body = response.json()

    assert (
        body["title"]
        == "Customer Data Quality"
    )

    assert (
        body["checkpoint"]["current_focus"]
        == "age null değerleri"
    )

    assert (
        body["next_action"]
        == "age dağılımını incele"
    )

def test_update_workspace_status_to_completed(
    tmp_path,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Data Quality",
            "workspace_type": "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    response = client.put(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/status"
        ),
        json={
            "status": "completed",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "completed"

    stored_workspace = database.get_workspace(
        workspace_id=workspace_id,
        learner_id="learner-001",
    )

    assert stored_workspace is not None
    assert stored_workspace.status == "completed"


def test_profile_workspace_data_does_not_send_sample_rows_to_ai(
    tmp_path,
    monkeypatch,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Private Dataset Test",
        
            "usage_context": "personal",
            "data_sensitivity": "public",
        
            "workspace_type": "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    captured_profile = {}

    def fake_generate_data_recommendations(
        profile: dict,
    ):
        captured_profile.update(profile)

        return DataQualityAnalysis(
            findings=[]
        )

    monkeypatch.setattr(
        workspace_routes,
        "generate_data_recommendations",
        fake_generate_data_recommendations,
    )

    monkeypatch.setattr(
        workspace_routes,
        "save_workspace_dataset",
        lambda workspace_id, content: None,
    )

    csv_content = (
        b"customer_id,name,age\n"
        b"1001,Alice,31\n"
        b"1002,Bob,29\n"
    )

    response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/data/profile"
        ),
        files={
            "file": (
                "private.csv",
                csv_content,
                "text/csv",
            )
        },
    )

    assert response.status_code == 200

    assert "sample_rows" not in captured_profile

    assert captured_profile["row_count"] == 2

    body = response.json()

    assert "sample_rows" not in body["profile"]

    assert (
        body["external_ai_allowed"]
        is True
    )

    assert (
        body["analysis_source"]
        == "local_and_ai"
    )
def test_personal_workspace_has_no_organization(
    tmp_path,
):
    prepare_database(tmp_path)

    response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Personal Practice",
            "usage_context": "personal",
            "data_sensitivity": "internal",
            "workspace_type": "practice",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["usage_context"] == "personal"

    assert body["organization_id"] is None


def test_confidential_workspace_uses_local_analysis_without_ai(
    tmp_path,
    monkeypatch,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id":
                "learner-001",

            "title":
                "Confidential Company Data",

            "usage_context":
                "work",

            "organization_id":
                "company-001",

            "data_sensitivity":
                "confidential",

            "workspace_type":
                "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()[
            "workspace_id"
        ]
    )


    ai_called = False

    def fake_generate_data_recommendations(
        profile: dict,
    ):
        nonlocal ai_called

        ai_called = True

        return DataQualityAnalysis(
            findings=[]
        )


    monkeypatch.setattr(
        workspace_routes,
        "generate_data_recommendations",
        fake_generate_data_recommendations,
    )

    monkeypatch.setattr(
        workspace_routes,
        "save_workspace_dataset",
        lambda workspace_id, content: None,
    )


    csv_content = (
        b"id,age,city\n"
        b"1,20,Amsterdam\n"
        b"2,,Rotterdam\n"
        b"2,,Rotterdam\n"
    )


    response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/data/profile"
        ),
        files={
            "file": (
                "confidential.csv",
                csv_content,
                "text/csv",
            )
        },
    )


    assert response.status_code == 200

    body = response.json()


    # External AI kesinlikle çağrılmamalı.
    assert ai_called is False

    assert (
        body["external_ai_allowed"]
        is False
    )

    assert (
        body["ai_processing_status"]
        == "blocked"
    )

    assert (
        body["analysis_source"]
        == "local"
    )


    finding_types = {
        finding["issue_type"]
        for finding
        in body["analysis"]["findings"]
    }

    assert (
        "missing_values"
        in finding_types
    )

    assert (
        "duplicate_rows"
        in finding_types
    )


    stored_workspace = (
        database.get_workspace(
            workspace_id=workspace_id,
            learner_id="learner-001",
        )
    )

    assert stored_workspace is not None

    assert (
        stored_workspace
        .dataset_analysis_source
        == "local"
    )

    assert (
        stored_workspace
        .dataset_ai_processing_status
        == "blocked"
    )