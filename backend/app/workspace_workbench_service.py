from uuid import uuid4

from backend.app.models import (
    DataQualityFinding,
    WorkspaceWorkbenchOperation,
    WorkspaceWorkbenchOperationCreateRequest,
)

def _normalize_issue_type(
    issue_type: str,
) -> str:
    return (
        issue_type
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def _build_operation_id(
    index: int,
    finding: DataQualityFinding,
) -> str:
    issue_type = _normalize_issue_type(
        finding.issue_type
    )

    column = (
        finding.column
        if finding.column
        else "dataset"
    )

    normalized_column = (
        column
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )

    return (
        f"quality-{index}-"
        f"{issue_type}-"
        f"{normalized_column}"
    )


def _build_title(
    finding: DataQualityFinding,
) -> str:
    issue_type = _normalize_issue_type(
        finding.issue_type
    )

    if issue_type == "duplicate_rows":
        return "Handle duplicate rows"

    if issue_type == "missing_values":
        if finding.column:
            return (
                f"Handle missing values "
                f"in {finding.column}"
            )

        return "Handle missing values"

    readable_issue = (
        issue_type
        .replace("_", " ")
        .strip()
    )

    if finding.column:
        return (
            f"Review {readable_issue} "
            f"in {finding.column}"
        )

    return f"Review {readable_issue}"


def _build_goal(
    finding: DataQualityFinding,
) -> str:
    issue_type = _normalize_issue_type(
        finding.issue_type
    )

    if issue_type == "duplicate_rows":
        return (
            "Resolve the detected duplicate "
            "records without introducing "
            "unintended row changes."
        )

    if issue_type == "missing_values":
        if finding.column:
            return (
                f"Resolve missing values in "
                f"{finding.column} using an "
                "appropriate transformation."
            )

        return (
            "Resolve the detected missing "
            "values using an appropriate "
            "transformation."
        )

    if finding.column:
        return (
            f"Resolve the detected "
            f"{issue_type.replace('_', ' ')} "
            f"issue in {finding.column}."
        )

    return (
        f"Resolve the detected "
        f"{issue_type.replace('_', ' ')} "
        f"data-quality issue."
    )


def build_workbench_operations_from_findings(
    findings: list[DataQualityFinding],
) -> list[WorkspaceWorkbenchOperation]:

    operations: list[
        WorkspaceWorkbenchOperation
    ] = []

    for index, finding in enumerate(
        findings,
        start=1,
    ):
        source_columns = (
            [finding.column]
            if finding.column
            else []
        )

        operations.append(
            WorkspaceWorkbenchOperation(
                operation_id=(
                    _build_operation_id(
                        index=index,
                        finding=finding,
                    )
                ),
                title=_build_title(
                    finding
                ),
                goal=_build_goal(
                    finding
                ),
                operation_type="clean",
                origin="data_quality",
                status="pending",
                source_columns=(
                    source_columns
                ),
                expected_columns=[],
            )
        )

    if operations:
        operations[0].status = "active"

    return operations


def add_user_workbench_operation(
    existing_operations: list[
        WorkspaceWorkbenchOperation
    ],
    request: WorkspaceWorkbenchOperationCreateRequest,
) -> WorkspaceWorkbenchOperation:

    has_active_operation = any(
        operation.status == "active"
        for operation in existing_operations
    )

    operation = WorkspaceWorkbenchOperation(
        operation_id=(
            f"user-{uuid4().hex[:12]}"
        ),
        title=request.title.strip(),
        goal=request.goal.strip(),
        operation_type=request.operation_type,
        origin="user",
        status=(
            "pending"
            if has_active_operation
            else "active"
        ),
        source_columns=request.source_columns,
        expected_columns=request.expected_columns,
    )

    existing_operations.append(operation)

    return operation

def sync_data_quality_workbench_operations(
    existing_operations: list[
        WorkspaceWorkbenchOperation
    ],
    findings: list[DataQualityFinding],
) -> tuple[
    list[WorkspaceWorkbenchOperation],
    str | None,
]:
    non_quality_operations = [
        operation
        for operation in existing_operations
        if operation.origin != "data_quality"
    ]

    quality_operations = (
        build_workbench_operations_from_findings(
            findings=findings,
        )
    )

    existing_active_operation = next(
        (
            operation
            for operation in non_quality_operations
            if operation.status == "active"
        ),
        None,
    )

    if existing_active_operation:
        for operation in quality_operations:
            operation.status = "pending"

        active_operation_id = (
            existing_active_operation.operation_id
        )

    elif quality_operations:
        active_operation_id = (
            quality_operations[0].operation_id
        )

    else:
        pending_operation = next(
            (
                operation
                for operation
                in non_quality_operations
                if operation.status == "pending"
            ),
            None,
        )

        if pending_operation:
            pending_operation.status = "active"
            active_operation_id = (
                pending_operation.operation_id
            )
        else:
            active_operation_id = None

    operations = (
        quality_operations
        + non_quality_operations
    )

    return (
        operations,
        active_operation_id,
    )