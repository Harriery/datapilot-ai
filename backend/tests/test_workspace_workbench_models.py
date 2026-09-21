from backend.app.models import (
    WorkspaceWorkbenchOperation,
    WorkspaceWorkbenchPreview,
)


def test_workspace_workbench_operation_supports_general_transformations():
    operation = WorkspaceWorkbenchOperation(
        operation_id="op-001",
        title="Split full name",
        goal=(
            "Create first_name and last_name "
            "from full_name."
        ),
        operation_type="transform",
        origin="project_requirement",
        source_columns=[
            "full_name",
        ],
        expected_columns=[
            "first_name",
            "last_name",
        ],
    )

    assert operation.operation_id == "op-001"
    assert operation.status == "pending"

    assert (
        operation.operation_type
        == "transform"
    )

    assert (
        operation.origin
        == "project_requirement"
    )

    assert operation.source_columns == [
        "full_name",
    ]

    assert operation.expected_columns == [
        "first_name",
        "last_name",
    ]

    assert operation.code is None
    assert operation.result_version_id is None


def test_workspace_workbench_preview_is_temporary_result():
    preview = WorkspaceWorkbenchPreview(
        operation_id="op-001",
        code=(
            'df[["first_name", "last_name"]] = '
            'df["full_name"].str.split('
            '" ", n=1, expand=True)'
        ),
        before_row_count=100,
        after_row_count=100,
        before_columns=[
            "customer_id",
            "full_name",
        ],
        after_columns=[
            "customer_id",
            "full_name",
            "first_name",
            "last_name",
        ],
        sample_rows=[
            {
                "customer_id": 1,
                "full_name": "Yasin Utk",
                "first_name": "Yasin",
                "last_name": "Utk",
            }
        ],
    )

    assert preview.operation_id == "op-001"

    assert preview.before_row_count == 100
    assert preview.after_row_count == 100

    assert "first_name" in preview.after_columns
    assert "last_name" in preview.after_columns

    assert preview.source == "local"