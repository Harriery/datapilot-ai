import backend.app.database as database

from backend.app.models import (
    TaskSummaryItem,
    TaskSummaryResponse,
)


def get_task_summary(
    learner_id: str,
) -> TaskSummaryResponse:
    workspaces = (
        database.get_workspaces_by_learner(
            learner_id=learner_id
        )
    )

    task_items: list[TaskSummaryItem] = []

    for workspace in workspaces:
        task = None

        if workspace.current_task_id:
            task = (
                database.get_data_engineering_task(
                    task_id=workspace.current_task_id,
                    learner_id=learner_id,
                )
            )

        completed_items = (
            workspace.checkpoint.completed_items
        )

        review_completed = (
            "Final review completed"
            in completed_items
        )

        handoff_completed = (
            "Handoff completed"
            in completed_items
        )

        validation_passed = bool(
            workspace.validation_result
            and workspace.validation_result.passed
        )

        if (
            workspace.status == "completed"
            or handoff_completed
        ):
            status = "completed"

        elif workspace.checkpoint.blocked_reason:
            status = "blocked"

        elif (
            workspace.current_task_id
            or workspace.dataset_filename
            or completed_items
        ):
            status = "active"

        else:
            status = "todo"

        current_step = None

        if task:
            active_step = next(
                (
                    step
                    for step in task.steps
                    if step.status == "active"
                ),
                None,
            )

            if active_step:
                current_step = active_step.title

        if current_step is None:
            current_step = (
                workspace.checkpoint.current_focus
            )

        next_action = (
            workspace.checkpoint.next_actions[0]
            if workspace.checkpoint.next_actions
            else None
        )

        task_title = (
            task.title
            if task
            else workspace.task_brief
            or workspace.title
        )

        task_items.append(
            TaskSummaryItem(
                workspace_id=workspace.workspace_id,
                workspace_title=workspace.title,
                task_id=(
                    task.task_id
                    if task
                    else None
                ),
                task_title=task_title,
                status=status,
                current_step=current_step,
                next_action=next_action,
                validation_passed=validation_passed,
                review_completed=review_completed,
                handoff_completed=handoff_completed,
                usage_context=workspace.usage_context,
            )
        )

    return TaskSummaryResponse(
        learner_id=learner_id,
        tasks=task_items,
    )