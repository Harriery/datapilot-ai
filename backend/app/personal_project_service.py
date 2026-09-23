from typing import Literal

from backend.app.models import (
    ProjectDeliverable,
    Workspace,
)

PERSONAL_PROJECT_DELIVERABLES = {
    "data_engineering": [
        ("data_profile", "Dataset profile"),
        ("clean_dataset", "Clean dataset"),
        (
            "transformation_pipeline",
            "Transformation pipeline",
        ),
        (
            "validation_report",
            "Validation report",
        ),
        (
            "documentation",
            "Project documentation",
        ),
    ],

    "data_analysis": [
        ("data_profile", "Dataset profile"),
        ("clean_dataset", "Clean dataset"),
        ("analysis", "Data analysis"),
        (
            "visualizations",
            "Analysis visualizations",
        ),
        (
            "insight_summary",
            "Insight summary",
        ),
        (
            "documentation",
            "Project documentation",
        ),
    ],

    "bi_dashboard": [
        ("data_profile", "Dataset profile"),
        ("clean_dataset", "Clean dataset"),
        ("data_model", "Data model"),
        (
            "kpi_definitions",
            "KPI definitions",
        ),
        (
            "bi_ready_dataset",
            "BI model",
        ),
        ("analysis", "Data analysis"),
        ("dashboard", "Dashboard"),
        (
            "insight_summary",
            "Insight summary",
        ),
        (
            "documentation",
            "Project documentation",
        ),
    ],

    "data_quality": [
        ("data_profile", "Dataset profile"),
        (
            "quality_review",
            "Data quality review",
        ),
        ("clean_dataset", "Clean dataset"),
        (
            "validation_report",
            "Validation report",
        ),
        (
            "quality_report",
            "Data quality report",
        ),
        (
            "documentation",
            "Project documentation",
        ),
    ],

    "portfolio": [
        ("data_profile", "Dataset profile"),
        ("clean_dataset", "Clean dataset"),
        (
            "transformation_pipeline",
            "Transformation pipeline",
        ),
        ("analysis", "Data analysis"),
        (
            "visualizations",
            "Visualizations / dashboard",
        ),
        (
            "insight_summary",
            "Insight summary",
        ),
        (
            "documentation",
            "Project documentation",
        ),
        (
            "portfolio_readme",
            "Portfolio README",
        ),
    ],
}


def build_personal_project_deliverables(
    project_type: str | None,
) -> list[ProjectDeliverable]:

    if project_type is None:
        return []

    template = (
        PERSONAL_PROJECT_DELIVERABLES.get(
            project_type
        )
    )

    if template is None:
        return []

    return [
        ProjectDeliverable(
            code=code,
            title=title,
        )
        for code, title in template
    ]

def reconcile_personal_project_deliverables(
    workspace: Workspace,
) -> bool:
    """
    Align persisted personal-project deliverables with the
    current template without losing completed work.

    This keeps existing local workspaces usable when the
    product workflow order changes.
    """

    if (
        workspace.usage_context != "personal"
        or workspace.project_type is None
    ):
        return False

    template = PERSONAL_PROJECT_DELIVERABLES.get(
        workspace.project_type
    )

    if template is None:
        return False

    existing_by_code = {
        deliverable.code: deliverable
        for deliverable in workspace.project_deliverables
    }

    had_in_progress = any(
        deliverable.status == "in_progress"
        for deliverable in workspace.project_deliverables
    )

    reconciled: list[ProjectDeliverable] = []

    for code, title in template:
        existing = existing_by_code.get(code)

        reconciled.append(
            ProjectDeliverable(
                code=code,
                title=title,
                status=(
                    existing.status
                    if existing is not None
                    else "pending"
                ),
                required=(
                    existing.required
                    if existing is not None
                    else True
                ),
            )
        )

    # If an older workflow had an active step, move the
    # active marker to the earliest unfinished step in the
    # new order. Completed work remains completed.
    if had_in_progress:
        active_assigned = False

        for deliverable in reconciled:
            if deliverable.status == "completed":
                continue

            if not active_assigned:
                deliverable.status = "in_progress"
                active_assigned = True
            else:
                deliverable.status = "pending"

    previous_state = [
        item.model_dump()
        for item in workspace.project_deliverables
    ]

    next_state = [
        item.model_dump()
        for item in reconciled
    ]

    if previous_state == next_state:
        return False

    workspace.project_deliverables = reconciled

    return True


def update_personal_project_deliverable(
    workspace: Workspace,
    code: str,
    status: Literal[
        "pending",
        "in_progress",
        "completed",
    ],
) -> bool:

    if workspace.usage_context != "personal":
        return False

    for deliverable in workspace.project_deliverables:

        if deliverable.code == code:
            deliverable.status = status
            return True

    return False

def complete_and_advance_personal_project_deliverable(
    workspace: Workspace,
    code: str,
) -> bool:

    if workspace.usage_context != "personal":
        return False

    reconcile_personal_project_deliverables(
        workspace
    )

    completed_index = None

    for index, deliverable in enumerate(
        workspace.project_deliverables
    ):
        if deliverable.code == code:

            if deliverable.status == "completed":
                return False
        
            deliverable.status = "completed"
            completed_index = index
            break

    if completed_index is None:
        return False

    for deliverable in (
        workspace.project_deliverables[
            completed_index + 1:
        ]
    ):
        if deliverable.status == "pending":
            deliverable.status = "in_progress"
            break

    return True