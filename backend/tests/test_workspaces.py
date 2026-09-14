import backend.app.database as database

from backend.app.models import (
    Workspace,
    WorkspaceCheckpoint,
)


def create_test_workspace() -> Workspace:
    return Workspace(
        workspace_id="workspace-001",
        learner_id="learner-001",
        title="Customer Data Quality",
        workspace_type="data_engineering",
        current_task_id="task-001",
        mentor_session_id="session-001",
        checkpoint=WorkspaceCheckpoint(
            completed_items=[
                "Duplicate kayıtlar temizlendi.",
            ],
            current_focus=(
                "age kolonundaki null değerler"
            ),
            blocked_reason=(
                "Imputation yöntemi henüz seçilmedi."
            ),
            last_error=(
                "Null sayısı azalmadı."
            ),
            next_actions=[
                "age dağılımını incele",
                "transformation seç",
                "sonucu validate et",
            ],
        ),
    )


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


def test_save_and_get_workspace(tmp_path):
    prepare_database(tmp_path)

    workspace = create_test_workspace()

    database.save_workspace(
        workspace=workspace,
    )

    loaded_workspace = database.get_workspace(
        workspace_id="workspace-001",
        learner_id="learner-001",
    )

    assert loaded_workspace is not None

    assert (
        loaded_workspace.workspace_id
        == "workspace-001"
    )

    assert (
        loaded_workspace.title
        == "Customer Data Quality"
    )

    assert (
        loaded_workspace.checkpoint.current_focus
        == "age kolonundaki null değerler"
    )

    assert (
        loaded_workspace.checkpoint.next_actions[0]
        == "age dağılımını incele"
    )


def test_get_workspace_returns_none_for_wrong_learner(
    tmp_path,
):
    prepare_database(tmp_path)

    workspace = create_test_workspace()

    database.save_workspace(
        workspace=workspace,
    )

    loaded_workspace = database.get_workspace(
        workspace_id="workspace-001",
        learner_id="different-learner",
    )

    assert loaded_workspace is None


def test_get_workspaces_by_learner(tmp_path):
    prepare_database(tmp_path)

    first_workspace = create_test_workspace()

    second_workspace = Workspace(
        workspace_id="workspace-002",
        learner_id="learner-001",
        title="SQL Practice",
        workspace_type="practice",
    )

    database.save_workspace(
        workspace=first_workspace,
    )

    database.save_workspace(
        workspace=second_workspace,
    )

    workspaces = (
        database.get_workspaces_by_learner(
            learner_id="learner-001"
        )
    )

    assert len(workspaces) == 2

    workspace_ids = {
        workspace.workspace_id
        for workspace in workspaces
    }

    assert workspace_ids == {
        "workspace-001",
        "workspace-002",
    }