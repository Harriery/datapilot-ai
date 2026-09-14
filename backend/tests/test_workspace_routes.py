from fastapi.testclient import TestClient

import backend.app.database as database

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