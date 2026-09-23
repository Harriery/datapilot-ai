import pandas as pd
import pytest

from backend.app.models import (
    WorkspacePipelineAction,
    WorkspaceWorkbenchOperation,
)

from backend.app.workspace_pipeline_service import (
    apply_pipeline_action,
    apply_replayable_workbench_pipeline,
)


def test_apply_pipeline_action_rename():
    df = pd.DataFrame(
        {
            "city": [
                "Den Haag",
                "Rotterdam",
            ],
        }
    )

    result = apply_pipeline_action(
        df,
        WorkspacePipelineAction(
            action="rename",
            column="city",
            new_name="location",
        ),
    )

    assert result.columns.tolist() == [
        "location",
    ]

    assert result["location"].tolist() == [
        "Den Haag",
        "Rotterdam",
    ]


def test_apply_pipeline_action_fill_and_derived():
    df = pd.DataFrame(
        {
            "price": [
                100.0,
                None,
                300.0,
            ],
        }
    )

    filled = apply_pipeline_action(
        df,
        WorkspacePipelineAction(
            action="fill_missing",
            column="price",
            fill_strategy="median",
        ),
    )

    result = apply_pipeline_action(
        filled,
        WorkspacePipelineAction(
            action="derived",
            column="price",
            derived_name="price_with_tax",
            derived_operation="multiply",
            derived_value=1.2,
        ),
    )

    assert result["price"].tolist() == [
        100.0,
        200.0,
        300.0,
    ]

    assert result[
        "price_with_tax"
    ].tolist() == [
        120.0,
        240.0,
        360.0,
    ]


def test_pipeline_replay_blocks_non_replayable_operation():
    df = pd.DataFrame(
        {
            "city": [
                "Den Haag",
            ],
        }
    )

    operations = [
        WorkspaceWorkbenchOperation(
            operation_id="custom-1",
            title="Custom cleanup",
            goal="Run custom code.",
            operation_type="custom",
            origin="user",
            status="completed",
            source_columns=["city"],
            expected_columns=["city"],
            code='df["city"] = df["city"]',
            pipeline_action=None,
        ),
    ]

    with pytest.raises(
        ValueError,
        match="güvenli replay",
    ):
        apply_replayable_workbench_pipeline(
            source_df=df,
            operations=operations,
        )


def test_pipeline_replay_applies_completed_structured_operations_in_order():
    df = pd.DataFrame(
        {
            "city": [
                "den haag",
                "rotterdam",
            ],
        }
    )

    operations = [
        WorkspaceWorkbenchOperation(
            operation_id="rename-city",
            title="Rename city",
            goal="Rename city.",
            operation_type="schema",
            origin="user",
            status="completed",
            source_columns=["city"],
            expected_columns=["location"],
            code="generated",
            pipeline_action=(
                WorkspacePipelineAction(
                    action="rename",
                    column="city",
                    new_name="location",
                )
            ),
        ),
        WorkspaceWorkbenchOperation(
            operation_id="upper-location",
            title="Create display location",
            goal="Create uppercase location.",
            operation_type="enrichment",
            origin="user",
            status="completed",
            source_columns=["location"],
            expected_columns=[
                "location",
                "location_display",
            ],
            code="generated",
            pipeline_action=(
                WorkspacePipelineAction(
                    action="derived",
                    column="location",
                    derived_name="location_display",
                    derived_operation="uppercase",
                )
            ),
        ),
    ]

    result, operation_ids = (
        apply_replayable_workbench_pipeline(
            source_df=df,
            operations=operations,
        )
    )

    assert operation_ids == [
        "rename-city",
        "upper-location",
    ]

    assert result.columns.tolist() == [
        "location",
        "location_display",
    ]

    assert result[
        "location_display"
    ].tolist() == [
        "DEN HAAG",
        "ROTTERDAM",
    ]
