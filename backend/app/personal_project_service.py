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
        ("analysis", "Data analysis"),
        ("data_model", "Data model"),
        (
            "kpi_definitions",
            "KPI definitions",
        ),
        
        (
            "bi_ready_dataset",
            "Power BI-ready dataset",
        ),
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