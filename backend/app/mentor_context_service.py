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
    learner_message: str = "",
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

    # Notebook evidence is persisted by the app; this is a READ-ONLY snapshot.
    # Recent executions and saved review notes should survive chat history
    # truncation. Never treat an execution result as full-dataset validation.
    executed_cells = [
        (index, cell)
        for index, cell in enumerate(notebook.cells)
        if isinstance(cell.last_execution, dict)
    ]
    executed_cells.sort(
        key=lambda pair: (
            str(pair[1].last_execution.get("executed_at") or ""),
            pair[0],
        )
    )

    def _cell_snapshot(cell):
        return {
            "cell_id": cell.cell_id,
            "code": cell.code[-1600:],
            "section_title": getattr(cell, "section_title", None),
            "code_truncated": len(cell.code) > 1600,
            "last_execution": cell.last_execution,
        }

    latest_cell = (
        _cell_snapshot(executed_cells[-1][1])
        if executed_cells else None
    )
    # Prefer executed cells that explicitly mention fields in the learner's
    # current question; the last N cells alone can miss an earlier finding.
    # This is retrieval, not a dataset-specific rule or a new computation.
    import re
    terms = {
        token.casefold()
        for token in re.findall(r"\b[A-Za-z][A-Za-z0-9_]{2,}\b", learner_message)
    }
    known_columns = set()
    profile = getattr(workspace, "dataset_profile", None) or {}
    if isinstance(profile, dict):
        known_columns = {
            str(column).casefold()
            for column in (profile.get("columns") or [])
        }
    requested_fields = terms & known_columns
    if not requested_fields:
        # Not every workspace has a populated profile; quoted/exact names
        # from executable notebook code are still useful retrieval keys.
        used_fields = set()
        for _, cell in executed_cells:
            used_fields.update(
                match.casefold() for match in re.findall(
                    r"""['"]([A-Za-z_][A-Za-z0-9_]*)['"]""",
                    cell.code,
                )
            )
        requested_fields = terms & used_fields
    ranked = list(reversed(executed_cells))
    related = [
        pair for pair in ranked
        if any(re.search(r"(?<!\w)" + re.escape(field) + r"(?!\w)",
                         pair[1].code, re.IGNORECASE)
               for field in requested_fields)
    ]
    selected_pairs = []
    chosen_ids = set()
    # One best visible observation for each requested column, then other
    # related cells, then recent context; preserve chronological ordering.
    for field in sorted(requested_fields):
        for pair in related:
            if pair[1].cell_id in chosen_ids:
                continue
            if re.search(r"(?<!\w)" + re.escape(field) + r"(?!\w)",
                         pair[1].code, re.IGNORECASE):
                selected_pairs.append(pair)
                chosen_ids.add(pair[1].cell_id)
                break
    for pair in related + ranked:
        if len(selected_pairs) >= 8:
            break
        if pair[1].cell_id not in chosen_ids:
            selected_pairs.append(pair)
            chosen_ids.add(pair[1].cell_id)
    recent_cells = [_cell_snapshot(cell) for _, cell in selected_pairs[:8]]

    # Quality Checks are optional for pre-feature Notebook objects.
    checks = list(getattr(notebook, "quality_checks", None) or [])
    checks.sort(key=lambda check: str(
        check.get("observed_at", "") if isinstance(check, dict)
        else getattr(check, "observed_at", "")
    ), reverse=True)
    if requested_fields:
        def _check_relevance(check):
            item = check if isinstance(check, dict) else (
                check.model_dump() if hasattr(check, "model_dump") else {}
            )
            text = " ".join(str(item.get(key) or "") for key in (
                "title", "note", "result_summary",
            )).casefold()
            return sum(field in text for field in requested_fields)
        checks.sort(key=_check_relevance, reverse=True)
    recorded_checks = []
    for check in checks[:5]:
        item = (
            check if isinstance(check, dict)
            else check.model_dump() if hasattr(check, "model_dump")
            else {}
        )
        recorded_checks.append({
            key: item.get(key)
            for key in (
                "check_id", "title", "section_title", "note",
                "result_summary", "status", "sample_row_count",
                "total_row_count", "dataset_kind", "observed_at",
            )
            if item.get(key) is not None
        })

    from backend.app.notebook_scope_service import notebook_input_version
    configured = (getattr(workspace, "development_sample_size", None)
                  or getattr(workspace, "development_sample_row_count", None)
                  or getattr(workspace, "development_sample_max_size", None) or 1000)
    return {
        "current_input_version": notebook_input_version(
            getattr(workspace, "workspace_id", None), notebook, configured,
        ),
        "notebook_id": notebook.notebook_id,
        "name": notebook.name,
        "dataset_kind": notebook.dataset_kind,
        "processed_dataset_id": notebook.processed_dataset_id,
        "cell_count": len(notebook.cells),
        "configured_development_rows": getattr(workspace, "development_sample_size", None),
        "scope_rule": (
            "Configured rows are a selection, not proof of execution scope. "
            "Use last_execution.input_row_count for loaded input at execution; "
            "row_count is output rows, not input rows. Legacy executions without "
            "input_row_count have unknown scope. recorded means saved, not passed."
        ),
        "latest_cell": latest_cell,
        "recent_cells": recent_cells,
        "quality_checks": recorded_checks,
        "evidence_scope": (
            "Persisted Notebook executions and user-recorded Quality Checks; "
            "these are observations, not independent full-data verification."
        ),
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
        "column_count": len(profile.get("columns") or []),
        "duplicate_count": profile.get("duplicate_count"),
        "duplicate_count_verified": profile.get("duplicate_count_verified", False),
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
            "active_development_rows": workspace.development_sample_row_count,
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
