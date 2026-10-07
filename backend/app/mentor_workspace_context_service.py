from __future__ import annotations

import backend.app.database as database

from backend.app.mentor_context_service import (
    build_trusted_notebook_state,
)
from backend.app.mentor_execution_diagnosis_service import (
    diagnose_generic_notebook_execution,
)
from backend.app.mentor_product_registry import (
    retrieve_product_context,
)
from backend.app.models import Workspace


def _dump(value):
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def _paths(product_context: dict) -> set[str]:
    paths: set[str] = set()

    current = product_context.get("current")
    if isinstance(current, dict):
        path = current.get("path")
        if isinstance(path, str):
            paths.add(path)

    for item in product_context.get("referenced", []):
        if isinstance(item, dict):
            path = item.get("path")
            if isinstance(path, str):
                paths.add(path)

    return paths


def _has_prefix(
    paths: set[str],
    *prefixes: str,
) -> bool:
    return any(
        any(
            path == prefix
            or path.startswith(prefix + ".")
            for prefix in prefixes
        )
        for path in paths
    )


def build_relevant_workspace_artifacts(
    *,
    workspace: Workspace,
    product_context: dict,
    selected_notebook_state: dict | None,
) -> dict:
    """
    Retrieve only artifacts required by the current/referenced product stages.
    This prevents every Mentor turn from carrying the whole workspace.
    """
    paths = _paths(product_context)
    artifacts: dict = {}

    if _has_prefix(paths, "source", "prepare.profile"):
        artifacts["dataset_profile"] = _dump(
            workspace.dataset_profile
        )
        artifacts["dataset_analysis"] = _dump(
            workspace.dataset_analysis
        )

    if _has_prefix(paths, "prepare.workbench"):
        artifacts["workbench_operations"] = [
            _dump(item)
            for item in (workspace.workbench_operations or [])
        ]
        artifacts["notebooks"] = [
            {
                "notebook_id": item.notebook_id,
                "name": item.name,
                "dataset_kind": item.dataset_kind,
                "cell_count": len(item.cells),
            }
            for item in (workspace.notebooks or [])
        ]
        artifacts["selected_notebook"] = (
            selected_notebook_state
        )
        artifacts["processed_datasets"] = [
            _dump(item)
            for item in (workspace.processed_datasets or [])
        ]

    if _has_prefix(paths, "prepare.validate"):
        artifacts["validation_result"] = _dump(
            workspace.validation_result
        )
        artifacts["processed_datasets"] = [
            _dump(item)
            for item in (workspace.processed_datasets or [])
        ]

    if _has_prefix(paths, "prepare.understand"):
        artifacts["validation_result"] = _dump(
            workspace.validation_result
        )
        artifacts["analysis_plan"] = _dump(
            workspace.analysis_plan
        )

    if _has_prefix(paths, "data_model"):
        artifacts["analysis_plan"] = _dump(
            workspace.analysis_plan
        )
        artifacts["data_model_plan"] = _dump(
            workspace.data_model_plan
        )
        artifacts["data_model_studio"] = _dump(
            workspace.data_model_studio
        )

    if _has_prefix(paths, "kpis", "bi_dataset"):
        artifacts["data_model_studio"] = _dump(
            workspace.data_model_studio
        )
        artifacts["kpi_candidates"] = [
            _dump(item)
            for item in (workspace.kpi_candidates or [])
        ]
        artifacts["kpi_definitions"] = [
            _dump(item)
            for item in (workspace.kpi_definitions or [])
        ]

    if _has_prefix(paths, "analysis"):
        artifacts["kpi_definitions"] = [
            _dump(item)
            for item in (workspace.kpi_definitions or [])
        ]
        artifacts["analysis_plan"] = _dump(
            workspace.analysis_plan
        )
        artifacts["analysis_result"] = _dump(
            workspace.analysis_result
        )
        artifacts["analysis_results"] = [
            _dump(item)
            for item in (workspace.analysis_results or [])[-10:]
        ]

    if _has_prefix(paths, "dashboard", "insights"):
        artifacts["kpi_definitions"] = [
            _dump(item)
            for item in (workspace.kpi_definitions or [])
        ]
        artifacts["analysis_results"] = [
            _dump(item)
            for item in (workspace.analysis_results or [])[-10:]
        ]
        artifacts["dashboard_config"] = _dump(
            workspace.dashboard_config
        )

    if _has_prefix(paths, "docs"):
        artifacts.update({
            "validation_result": _dump(
                workspace.validation_result
            ),
            "data_model_studio": _dump(
                workspace.data_model_studio
            ),
            "kpi_definitions": [
                _dump(item)
                for item in (workspace.kpi_definitions or [])
            ],
            "analysis_results": [
                _dump(item)
                for item in (workspace.analysis_results or [])[-10:]
            ],
            "dashboard_config": _dump(
                workspace.dashboard_config
            ),
        })

    return artifacts


def build_chat_mentor_workspace_context(
    *,
    workspace: Workspace,
    learner_id: str,
    ui_context: dict | None,
    message: str,
    current_task: dict | None,
    current_step: dict | None,
) -> dict:
    product_context = retrieve_product_context(
        ui_context=ui_context,
        message=message,
    )

    selected_notebook_state = (
        build_trusted_notebook_state(
            workspace=workspace,
            ui_context=ui_context,
        )
    )

    execution_context = (
        diagnose_generic_notebook_execution(
            selected_notebook_state
        )
    )

    artifacts = build_relevant_workspace_artifacts(
        workspace=workspace,
        product_context=product_context,
        selected_notebook_state=selected_notebook_state,
    )

    return {
        "workspace_id": workspace.workspace_id,
        "title": workspace.title,
        "workspace_type": workspace.workspace_type,
        "status": workspace.status,
        "current_task_id": workspace.current_task_id,
        "current_task": current_task,
        "current_step": current_step,
        "checkpoint": workspace.checkpoint.model_dump(),
        "task_brief": workspace.task_brief,
        "desired_outcome": workspace.desired_outcome,
        "project_type": workspace.project_type,
        "dataset_filename": workspace.dataset_filename,
        "development_sample_size": workspace.development_sample_size,
        "active_processed_dataset_id":
            workspace.active_processed_dataset_id,
        "ui_context": ui_context or {},
        "mentor_product_context": product_context,
        "mentor_execution_context": execution_context,
        "artifacts": artifacts,
        "learner_skills": [
            dict(item)
            for item in database.get_skill_states_by_learner(
                learner_id
            )
        ],
    }
