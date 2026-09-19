from unittest.mock import patch

from backend.app.models import (
    Workspace,
    WorkspaceCheckpoint,
    WorkspaceValidationResponse,
    DataEngineeringTask,
    DataEngineeringTaskStep,
    DataQualityFinding,
)

from backend.app.task_summary_service import (
    get_task_summary,
)


def create_active_task() -> DataEngineeringTask:
    finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="Missing age values found.",
        suggested_action="Investigate missing values.",
    )

    step = DataEngineeringTaskStep(
        step_number=1,
        title="Investigate missing age values",
        finding=finding,
        status="active",
    )

    return DataEngineeringTask(
        task_id="task-active",
        title="Clean customer data",
        steps=[step],
        current_step_number=1,
        status="active",
    )


def test_task_summary_builds_todo_active_blocked_and_completed():
    todo_workspace = Workspace(
        workspace_id="workspace-todo",
        learner_id="learner-001",
        title="Todo Workspace",
        task_brief="Inspect customer data",
        workspace_type="data_engineering",
    )

    active_workspace = Workspace(
        workspace_id="workspace-active",
        learner_id="learner-001",
        title="Active Workspace",
        current_task_id="task-active",
        checkpoint=WorkspaceCheckpoint(
            current_focus="Investigate missing age values",
            next_actions=[
                "Validate cleaned dataset"
            ],
        ),
        workspace_type="data_engineering",
    )

    blocked_workspace = Workspace(
        workspace_id="workspace-blocked",
        learner_id="learner-001",
        title="Blocked Workspace",
        checkpoint=WorkspaceCheckpoint(
            blocked_reason="Waiting for business rule",
            current_focus="Confirm customer ID rule",
        ),
        workspace_type="data_engineering",
    )

    completed_workspace = Workspace(
        workspace_id="workspace-completed",
        learner_id="learner-001",
        title="Completed Workspace",
        status="completed",
        validation_result=WorkspaceValidationResponse(
            passed=True,
            source_row_count=5,
            working_row_count=4,
            checks=[],
        ),
        checkpoint=WorkspaceCheckpoint(
            completed_items=[
                "Validation passed",
                "Final review completed",
                "Handoff completed",
            ],
            current_focus="Workspace completed",
        ),
        workspace_type="data_engineering",
    )

    workspaces = [
        todo_workspace,
        active_workspace,
        blocked_workspace,
        completed_workspace,
    ]

    active_task = create_active_task()

    def fake_get_task(
        task_id: str,
        learner_id: str,
    ):
        if task_id == "task-active":
            return active_task

        return None

    with patch(
        "backend.app.task_summary_service."
        "database.get_workspaces_by_learner",
        return_value=workspaces,
    ), patch(
        "backend.app.task_summary_service."
        "database.get_data_engineering_task",
        side_effect=fake_get_task,
    ):
        result = get_task_summary(
            learner_id="learner-001"
        )

    assert len(result.tasks) == 4

    statuses = {
        item.workspace_id: item.status
        for item in result.tasks
    }

    assert statuses["workspace-todo"] == "todo"
    assert statuses["workspace-active"] == "active"
    assert statuses["workspace-blocked"] == "blocked"
    assert statuses["workspace-completed"] == "completed"

    active_item = next(
        item
        for item in result.tasks
        if item.workspace_id == "workspace-active"
    )

    assert (
        active_item.current_step
        == "Investigate missing age values"
    )

    assert (
        active_item.next_action
        == "Validate cleaned dataset"
    )

    completed_item = next(
        item
        for item in result.tasks
        if item.workspace_id == "workspace-completed"
    )

    assert completed_item.validation_passed is True
    assert completed_item.review_completed is True
    assert completed_item.handoff_completed is True