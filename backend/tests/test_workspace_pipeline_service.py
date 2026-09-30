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


def test_pipeline_replay_allows_accepted_as_is_quality_reviews():
    df = pd.DataFrame(
        {
            "value": [1, 2, 3],
        }
    )

    operations = [
        WorkspaceWorkbenchOperation(
            operation_id="accepted-review",
            title="Review suspicious values",
            goal="Review values without changing data.",
            operation_type="clean",
            origin="data_quality",
            status="completed",
            source_columns=["value"],
            expected_columns=[],
            code=None,
            pipeline_action=None,
            decision="accepted_as_is",
            decision_reason="Values were reviewed and are valid.",
        ),
        WorkspaceWorkbenchOperation(
            operation_id="replace-value",
            title="Replace value",
            goal="Replace one invalid value.",
            operation_type="clean",
            origin="data_quality",
            status="completed",
            source_columns=["value"],
            expected_columns=["value"],
            code="generated",
            pipeline_action=WorkspacePipelineAction(
                action="replace_values",
                column="value",
                old_value=3,
                new_value=30,
            ),
        ),
    ]

    result, operation_ids = apply_replayable_workbench_pipeline(
        source_df=df,
        operations=operations,
    )

    assert result["value"].tolist() == [1, 2, 30]
    assert operation_ids == ["replace-value"]


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



def test_apply_pipeline_action_mapping_fill_uses_only_unambiguous_mappings():
    df = pd.DataFrame(
        {
            "suburb": ["A", "A", "B", "B", "B", "C", "C", "D"],
            "council": ["X", None, "Y", "Z", None, "W", None, None],
        }
    )

    result = apply_pipeline_action(
        df,
        WorkspacePipelineAction(
            action="fill_missing",
            column="council",
            fill_strategy="mapping",
            mapping_source_column="suburb",
            mapping_only_unambiguous=True,
        ),
    )

    # A and C each have one known target, so their missing values are filled.
    assert result.loc[1, "council"] == "X"
    assert result.loc[6, "council"] == "W"

    # B maps to both Y and Z, so the ambiguous missing value stays missing.
    assert pd.isna(result.loc[4, "council"])

    # D has no known target at all, so it also stays missing.
    assert pd.isna(result.loc[7, "council"])


def test_mapping_fill_is_replayable_on_full_dataset():
    df = pd.DataFrame(
        {
            "suburb": ["A", "A", "B", "B"],
            "council": ["X", None, "Y", None],
        }
    )

    operations = [
        WorkspaceWorkbenchOperation(
            operation_id="map-council",
            title="Fill council from suburb",
            goal="Use safe mappings.",
            operation_type="clean",
            origin="user",
            status="completed",
            source_columns=["council", "suburb"],
            expected_columns=["council"],
            code="generated",
            pipeline_action=WorkspacePipelineAction(
                action="fill_missing",
                column="council",
                fill_strategy="mapping",
                mapping_source_column="suburb",
            ),
        ),
    ]

    result, operation_ids = apply_replayable_workbench_pipeline(
        source_df=df,
        operations=operations,
    )

    assert operation_ids == ["map-council"]
    assert result["council"].tolist() == ["X", "X", "Y", "Y"]



def test_apply_pipeline_action_batch_replace_values():
    df = pd.DataFrame(
        {
            "seller": ["Castran", "CASTRAN", "Re", "RE", "Nelson"],
        }
    )

    result = apply_pipeline_action(
        df,
        WorkspacePipelineAction(
            action="replace_values",
            column="seller",
            replacements=[
                {
                    "old_value": "CASTRAN",
                    "new_value": "Castran",
                },
                {
                    "old_value": "RE",
                    "new_value": "Re",
                },
            ],
        ),
    )

    assert result["seller"].tolist() == [
        "Castran",
        "Castran",
        "Re",
        "Re",
        "Nelson",
    ]



def test_apply_pipeline_action_conditional_replacements():
    df = pd.DataFrame(
        {
            "year": [1850, 1850, 1850, 1970],
            "suburb": [
                "Fitzroy",
                "Prahran",
                "St Kilda",
                "Richmond",
            ],
            "address": [
                "11 Henry St",
                "602/220 Commercial Rd",
                "51/167 Fitzroy St",
                "1 Example St",
            ],
        }
    )

    result = apply_pipeline_action(
        df,
        WorkspacePipelineAction(
            action="replace_values",
            column="year",
            replacements=[
                {
                    "old_value": 1850,
                    "new_value": 1900,
                    "conditions": [
                        {
                            "column": "suburb",
                            "value": "Fitzroy",
                        },
                        {
                            "column": "address",
                            "value": "11 Henry St",
                        },
                    ],
                },
                {
                    "old_value": 1850,
                    "new_value": 1915,
                    "conditions": [
                        {
                            "column": "suburb",
                            "value": "Prahran",
                        },
                        {
                            "column": "address",
                            "value": "602/220 Commercial Rd",
                        },
                    ],
                },
            ],
        ),
    )

    assert result["year"].tolist() == [
        1900,
        1915,
        1850,
        1970,
    ]


def test_conditional_replace_requires_condition_column():
    df = pd.DataFrame(
        {
            "year": [1850],
        }
    )

    with pytest.raises(
        ValueError,
        match="Pipeline column bulunamadı: suburb",
    ):
        apply_pipeline_action(
            df,
            WorkspacePipelineAction(
                action="replace_values",
                column="year",
                replacements=[
                    {
                        "old_value": 1850,
                        "new_value": 1900,
                        "conditions": [
                            {
                                "column": "suburb",
                                "value": "Fitzroy",
                            },
                        ],
                    },
                ],
            ),
        )
