from __future__ import annotations

from backend.app.mentor_execution_diagnosis_service import (
    diagnose_notebook_execution,
)
from backend.app.mentor_action_planner_service import (
    plan_guided_next_action,
)
from backend.app.mentor_learner_model_service import (
    build_learner_snapshot,
)
from backend.app.mentor_playbook_service import (
    get_playbook_context,
)
from backend.app.mentor_product_registry import (
    resolve_product_context,
)
from backend.app.mentor_supervisor_service import (
    build_issue_supervisor_context,
)
from backend.app.mentor_guided_workflow_service import (
    resolve_guided_workflow_state,
)
from backend.app.models import (
    DataQualityFinding,
    Workspace,
    WorkspaceLearningLoop,
)


def build_trusted_notebook_state(
    *,
    workspace: Workspace,
    ui_context: dict | None,
) -> dict | None:
    selected_id = (
        (ui_context or {}).get(
            "selected_notebook_id"
        )
    )

    if not isinstance(selected_id, str):
        return None

    notebook = next(
        (
            item
            for item in workspace.notebooks
            if item.notebook_id == selected_id
        ),
        None,
    )

    if notebook is None:
        return None

    executed_cells = [
        cell
        for cell in notebook.cells
        if isinstance(
            cell.last_execution,
            dict,
        )
    ]

    latest_cell = None
    if executed_cells:
        latest = max(
            executed_cells,
            key=lambda cell: str(
                (
                    cell.last_execution
                    or {}
                ).get(
                    "executed_at",
                    "",
                )
            ),
        )
        latest_cell = {
            "cell_id": latest.cell_id,
            "code": latest.code[-4000:],
            "last_execution": latest.last_execution,
        }

    return {
        "notebook_id": notebook.notebook_id,
        "name": notebook.name,
        "dataset_kind": notebook.dataset_kind,
        "processed_dataset_id":
            notebook.processed_dataset_id,
        "cell_count": len(notebook.cells),
        "latest_cell": latest_cell,
    }


def build_guided_mentor_context(
    *,
    learner_id: str,
    workspace: Workspace,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    ui_context: dict | None,
    learner_message: str = "",
) -> dict:
    trusted_ui = dict(
        ui_context
        if isinstance(ui_context, dict)
        else {}
    )

    notebook_state = build_trusted_notebook_state(
        workspace=workspace,
        ui_context=trusted_ui,
    )

    if notebook_state is not None:
        trusted_ui[
            "selected_notebook_state"
        ] = notebook_state
        trusted_ui[
            "selected_notebook_dataset_kind"
        ] = notebook_state[
            "dataset_kind"
        ]

    profile = (
        workspace.dataset_profile
        if isinstance(workspace.dataset_profile, dict)
        else {}
    )
    profile_context = {
        "row_count": profile.get("row_count"),
        "columns": list(profile.get("columns") or [])[:80],
        "data_types": dict(profile.get("data_types") or {}),
        "distinct_counts": dict(profile.get("distinct_counts") or {}),
        "null_counts": dict(profile.get("null_counts") or {}),
    }

    execution_diagnosis = (
        diagnose_notebook_execution(
            loop=loop,
            finding=finding,
            ui_context=trusted_ui,
        )
    )

    live_state = {
        "active_workspace_stage":
            trusted_ui.get(
                "active_workspace_stage"
            ),
        "active_prepare_stage":
            trusted_ui.get(
                "active_prepare_stage"
            ),
        "workbench_view":
            trusted_ui.get(
                "workbench_view"
            ),
        "selected_notebook":
            notebook_state,
        "notebook_count":
            len(workspace.notebooks),
        "source_preview_inspection":
            trusted_ui.get(
                "source_preview_inspection"
            ),
    }

    workflow = resolve_guided_workflow_state(
        loop=loop,
        finding=finding,
        profile=profile_context,
        live_state=live_state,
        execution_diagnosis=execution_diagnosis,
    )

    supervisor = build_issue_supervisor_context(
        loop=loop,
        finding=finding,
        profile=profile_context,
        execution_diagnosis=execution_diagnosis,
    )

    context = {
        "product": resolve_product_context(
            trusted_ui
        ),
        "profile": profile_context,
        "project_context": {
            "goal": workspace.task_brief,
            "desired_outcome": workspace.desired_outcome,
            "project_type": workspace.project_type,
            "mentor_setup": workspace.mentor_setup.model_dump() if workspace.mentor_setup else None,
        },
        "active_investigation": dict(
            loop.active_investigation
            if isinstance(loop.active_investigation, dict)
            else {}
        ),
        "playbook": get_playbook_context(
            finding.issue_type,
            loop.current_phase,
        ),
        "supervisor": supervisor,
        "workflow": workflow,
        "execution_diagnosis":
            execution_diagnosis,
        "learner": build_learner_snapshot(
            learner_id=learner_id,
            skill_name=loop.skill_name,
        ),
        "live_state": live_state,
    }

    context["next_action"] = (
        plan_guided_next_action(
            learner_message=learner_message,
            loop=loop,
            finding=finding,
            mentor_context=context,
        )
    )
    context["active_investigation"] = dict(
        loop.active_investigation
        if isinstance(loop.active_investigation, dict)
        else {}
    )

    return context
