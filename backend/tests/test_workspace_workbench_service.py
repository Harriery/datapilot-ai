from backend.app.models import (
    DataQualityFinding,
    WorkspaceWorkbenchOperation,
    WorkspaceWorkbenchOperationCreateRequest,
    WorkspacePipelineAction,
)

from backend.app.workspace_workbench_service import (
    add_user_workbench_operation,
    build_workbench_operations_from_findings,
    complete_workbench_operation,
    sync_data_quality_workbench_operations,
)


def test_build_workbench_operations_from_findings():
    findings = [
        DataQualityFinding(
            issue_type="duplicate_rows",
            column=None,
            severity="medium",
            observation=(
                "1 duplicate row detected."
            ),
            suggested_action=(
                "Review duplicate records."
            ),
        ),
        DataQualityFinding(
            issue_type="missing_values",
            column="age",
            severity="medium",
            observation=(
                "Missing values detected in age."
            ),
            suggested_action=(
                "Review missing values."
            ),
        ),
    ]

    operations = (
        build_workbench_operations_from_findings(
            findings=findings,
        )
    )

    assert len(operations) == 2

    first = operations[0]

    assert first.operation_id == (
        "quality-1-duplicate_rows-dataset"
    )

    assert first.title == (
        "Handle duplicate rows"
    )

    assert first.operation_type == "clean"
    assert first.origin == "data_quality"
    assert first.status == "active"

    assert first.source_columns == []

    second = operations[1]

    assert second.operation_id == (
        "quality-2-missing_values-age"
    )

    assert second.title == (
        "Handle missing values in age"
    )

    assert second.operation_type == "clean"
    assert second.origin == "data_quality"
    assert second.status == "pending"

    assert second.source_columns == [
        "age",
    ]


def test_workbench_operations_do_not_invent_code():
    finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation=(
            "Missing values detected in age."
        ),
        suggested_action=(
            "Review missing values."
        ),
    )

    operations = (
        build_workbench_operations_from_findings(
            findings=[finding],
        )
    )

    assert len(operations) == 1

    operation = operations[0]

    assert operation.code is None
    assert operation.expected_columns == []

    assert (
        "median"
        not in operation.goal.lower()
    )

def test_add_user_workbench_operation_becomes_active_when_empty():
    operations: list[
        WorkspaceWorkbenchOperation
    ] = []

    request = (
        WorkspaceWorkbenchOperationCreateRequest(
            title="  Split full_name  ",
            goal=(
                "  Create first_name and "
                "last_name columns.  "
            ),
            operation_type="transform",
            source_columns=["full_name"],
            expected_columns=[
                "first_name",
                "last_name",
            ],
        )
    )

    operation = add_user_workbench_operation(
        existing_operations=operations,
        request=request,
    )

    assert len(operations) == 1

    assert operation.operation_id.startswith(
        "user-"
    )

    assert operation.title == "Split full_name"

    assert operation.goal == (
        "Create first_name and "
        "last_name columns."
    )

    assert operation.operation_type == (
        "transform"
    )

    assert operation.origin == "user"
    assert operation.status == "active"

    assert operation.source_columns == [
        "full_name",
    ]

    assert operation.expected_columns == [
        "first_name",
        "last_name",
    ]

    assert operation.code is None
    assert operation.result_version_id is None

    assert operations[0] is operation


def test_add_user_workbench_operation_stays_pending_when_active_exists():
    operations = [
        WorkspaceWorkbenchOperation(
            operation_id=(
                "quality-1-missing_values-age"
            ),
            title=(
                "Handle missing values in age"
            ),
            goal=(
                "Resolve missing values in age."
            ),
            operation_type="clean",
            origin="data_quality",
            status="active",
            source_columns=["age"],
        )
    ]

    request = (
        WorkspaceWorkbenchOperationCreateRequest(
            title="Extract postcode",
            goal=(
                "Create postcode from address."
            ),
            operation_type="transform",
            source_columns=["address"],
            expected_columns=["postcode"],
        )
    )

    operation = add_user_workbench_operation(
        existing_operations=operations,
        request=request,
    )

    assert len(operations) == 2

    assert operations[0].status == "active"

    assert operation.origin == "user"
    assert operation.status == "pending"

    assert operation.title == (
        "Extract postcode"
    )

    assert operation.source_columns == [
        "address",
    ]

    assert operation.expected_columns == [
        "postcode",
    ]

def test_sync_quality_operations_preserves_active_user_operation():
    existing_operations = [
        WorkspaceWorkbenchOperation(
            operation_id="user-split-name",
            title="Split full_name",
            goal=(
                "Create first_name and "
                "last_name columns."
            ),
            operation_type="transform",
            origin="user",
            status="active",
            source_columns=["full_name"],
            expected_columns=[
                "first_name",
                "last_name",
            ],
        ),
    ]

    findings = [
        DataQualityFinding(
            issue_type="duplicate_rows",
            column=None,
            severity="medium",
            observation=(
                "1 duplicate row detected."
            ),
            suggested_action=(
                "Review duplicate records."
            ),
        ),
        DataQualityFinding(
            issue_type="missing_values",
            column="age",
            severity="medium",
            observation=(
                "Missing values detected in age."
            ),
            suggested_action=(
                "Review missing values."
            ),
        ),
    ]

    (
        operations,
        active_operation_id,
    ) = sync_data_quality_workbench_operations(
        existing_operations=existing_operations,
        findings=findings,
    )

    assert len(operations) == 3

    user_operation = next(
        operation
        for operation in operations
        if operation.origin == "user"
    )

    assert (
        user_operation.operation_id
        == "user-split-name"
    )

    assert user_operation.status == "active"

    quality_operations = [
        operation
        for operation in operations
        if operation.origin == "data_quality"
    ]

    assert len(quality_operations) == 2

    assert all(
        operation.status == "pending"
        for operation in quality_operations
    )

    assert (
        active_operation_id
        == "user-split-name"
    )

    active_operations = [
        operation
        for operation in operations
        if operation.status == "active"
    ]

    assert len(active_operations) == 1


def test_sync_quality_operations_replaces_old_quality_tasks():
    existing_operations = [
        WorkspaceWorkbenchOperation(
            operation_id=(
                "quality-old-missing-age"
            ),
            title=(
                "Old missing age task"
            ),
            goal=(
                "Old quality task."
            ),
            operation_type="clean",
            origin="data_quality",
            status="active",
            source_columns=["age"],
        ),
        WorkspaceWorkbenchOperation(
            operation_id="user-postcode",
            title="Extract postcode",
            goal=(
                "Create postcode from address."
            ),
            operation_type="transform",
            origin="user",
            status="pending",
            source_columns=["address"],
            expected_columns=["postcode"],
        ),
    ]

    findings = [
        DataQualityFinding(
            issue_type="duplicate_rows",
            column=None,
            severity="medium",
            observation=(
                "Duplicate rows detected."
            ),
            suggested_action=(
                "Review duplicate records."
            ),
        ),
    ]

    (
        operations,
        active_operation_id,
    ) = sync_data_quality_workbench_operations(
        existing_operations=existing_operations,
        findings=findings,
    )

    assert len(operations) == 2

    operation_ids = {
        operation.operation_id
        for operation in operations
    }

    assert (
        "quality-old-missing-age"
        not in operation_ids
    )

    assert (
        "user-postcode"
        in operation_ids
    )

    quality_operation = next(
        operation
        for operation in operations
        if operation.origin == "data_quality"
    )

    assert (
        quality_operation.operation_id
        == "quality-1-duplicate_rows-dataset"
    )

    assert quality_operation.status == "active"

    user_operation = next(
        operation
        for operation in operations
        if operation.origin == "user"
    )

    assert user_operation.status == "pending"

    assert (
        active_operation_id
        == quality_operation.operation_id
    )

    active_operations = [
        operation
        for operation in operations
        if operation.status == "active"
    ]

    assert len(active_operations) == 1


def test_completed_workbench_operation_persists_pipeline_action():
    operation = WorkspaceWorkbenchOperation(
        operation_id="user-rename",
        title="Rename city",
        goal="Rename the city column.",
        operation_type="schema",
        origin="user",
        status="active",
        source_columns=["city"],
        expected_columns=["location"],
    )

    pipeline_action = (
        WorkspacePipelineAction(
            action="rename",
            column="city",
            new_name="location",
        )
    )

    (
        completed,
        next_operation_id,
    ) = complete_workbench_operation(
        operations=[operation],
        operation_id="user-rename",
        code=(
            'df = df.rename('
            'columns={"city": "location"})'
        ),
        rollback_version_number=1,
        pipeline_action=pipeline_action,
    )

    assert completed.status == "completed"

    assert (
        completed.pipeline_action
        == pipeline_action
    )

    assert (
        completed.rollback_version_number
        == 1
    )

    assert next_operation_id is None
