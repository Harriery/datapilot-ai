import pandas as pd

from backend.app.models import (
    WorkspacePipelineAction,
    WorkspaceWorkbenchOperation,
)
from backend.app.workspace_large_data_service import (
    apply_full_pipeline_to_silver,
    build_full_data_profile,
    build_smart_development_sample,
    profile_parquet,
    query_large_data_preview,
    run_full_data_preflight,
)


def _write_csv(
    tmp_path,
    df: pd.DataFrame,
    name: str = "source.csv",
):
    path = tmp_path / name
    df.to_csv(
        path,
        index=False,
    )
    return path


def _operation(
    operation_id: str,
    title: str,
    action: WorkspacePipelineAction,
) -> WorkspaceWorkbenchOperation:
    return WorkspaceWorkbenchOperation(
        operation_id=operation_id,
        title=title,
        goal=title,
        operation_type="clean",
        origin="user",
        status="completed",
        source_columns=[
            action.column
        ],
        expected_columns=[],
        code="structured",
        pipeline_action=action,
    )


def test_smart_sampling_measures_all_5k_10k_20k_candidates(
    tmp_path,
):
    row_count = 30_000

    df = pd.DataFrame(
        {
            "row_id": range(
                row_count
            ),
            "carrier": (
                ["AA"] * 12_000
                + ["DL"] * 9_000
                + ["UA"] * 8_700
                + ["RARE"] * 300
            ),
            "delay": [
                (index % 180) - 30
                for index in range(
                    row_count
                )
            ],
            "optional_value": [
                None
                if index % 20 == 0
                else index
                for index in range(
                    row_count
                )
            ],
        }
    )

    source_path = _write_csv(
        tmp_path,
        df,
    )

    profile = build_full_data_profile(
        source_path
    )

    sample, report = (
        build_smart_development_sample(
            source_path=source_path,
            profile=profile,
            candidate_sizes=(
                5_000,
                10_000,
                20_000,
            ),
            seed=42,
        )
    )

    assert [
        item["sample_size"]
        for item in report[
            "candidate_evaluations"
        ]
    ] == [
        5_000,
        10_000,
        20_000,
    ]

    assert report[
        "selected_size"
    ] in {
        5_000,
        10_000,
        20_000,
    }

    assert (
        len(sample)
        == report["selected_size"]
    )

    for item in report[
        "candidate_evaluations"
    ]:
        assert (
            0
            <= item["overall_score"]
            <= 100
        )
        assert (
            0
            <= item[
                "rare_group_coverage"
            ]
            <= 100
        )


def test_full_profile_uses_entire_csv(
    tmp_path,
):
    df = pd.DataFrame(
        {
            "category": [
                "A",
                "A",
                "B",
                "B",
            ],
            "value": [
                10.0,
                None,
                30.0,
                40.0,
            ],
        }
    )

    source_path = _write_csv(
        tmp_path,
        df,
    )

    profile = build_full_data_profile(
        source_path
    )

    assert profile[
        "row_count"
    ] == 4

    assert profile[
        "null_counts"
    ]["value"] == 1

    assert profile[
        "distinct_counts"
    ]["category"] == 2

    assert profile[
        "profile_scope"
    ] == "full_dataset"

    assert profile[
        "profile_engine"
    ] == "duckdb"



def test_full_profile_large_csv_stages_parquet_and_cleans_up(
    tmp_path,
    monkeypatch,
):
    from tempfile import TemporaryDirectory

    import backend.app.workspace_large_data_service as service

    source_path = _write_csv(
        tmp_path,
        pd.DataFrame(
            {
                "carrier": ["AA", "DL", "AA", None],
                "delay": [3, 12, None, 8],
            }
        ),
    )
    original_bytes = source_path.read_bytes()
    baseline = service.build_full_data_profile(source_path)

    # Exercise the exact large-file path with a small fixture.
    monkeypatch.setattr(
        service,
        "FULL_PROFILE_COLUMNAR_THRESHOLD_BYTES",
        1,
    )
    monkeypatch.setattr(
        service,
        "TemporaryDirectory",
        lambda prefix: TemporaryDirectory(prefix=prefix, dir=tmp_path),
    )

    staged = service.build_full_data_profile(source_path)
    assert staged["row_count"] == baseline["row_count"] == 4
    assert staged["null_counts"] == baseline["null_counts"]
    assert staged["distinct_counts"] == baseline["distinct_counts"]
    assert staged["data_types"] == baseline["data_types"]
    assert staged["numeric_summary"] == baseline["numeric_summary"]
    assert source_path.read_bytes() == original_bytes
    assert list(tmp_path.glob("datapilot-profile-*")) == []


def test_preflight_tracks_columns_after_rename(
    tmp_path,
):
    source_path = _write_csv(
        tmp_path,
        pd.DataFrame(
            {
                "city": [
                    "Den Haag",
                    None,
                    "Delft",
                ],
                "value": [
                    1,
                    2,
                    3,
                ],
            }
        ),
    )

    operations = [
        _operation(
            "rename-city",
            "Rename city",
            WorkspacePipelineAction(
                action="rename",
                column="city",
                new_name="location",
            ),
        ),
        _operation(
            "fill-location",
            "Fill location",
            WorkspacePipelineAction(
                action="fill_missing",
                column="location",
                fill_strategy="value",
                fill_value="Unknown",
            ),
        ),
    ]

    result = run_full_data_preflight(
        source_path=source_path,
        operations=operations,
    )

    assert result[
        "passed"
    ] is True

    assert result[
        "checks"
    ][1]["missing_columns"] == []

    assert result[
        "checks"
    ][1]["affected_rows"] == 1


def test_large_pipeline_mapping_fill_writes_silver_parquet(
    tmp_path,
):
    source_path = _write_csv(
        tmp_path,
        pd.DataFrame(
            {
                "group_code": [
                    "A",
                    "A",
                    "B",
                    "B",
                ],
                "label": [
                    "Alpha",
                    None,
                    "Beta",
                    None,
                ],
            }
        ),
    )

    silver_path = (
        tmp_path
        / "silver"
        / "cleaned.parquet"
    )

    operations = [
        _operation(
            "fill-label",
            "Fill label from group",
            WorkspacePipelineAction(
                action="fill_missing",
                column="label",
                fill_strategy="mapping",
                mapping_source_column=(
                    "group_code"
                ),
                mapping_only_unambiguous=True,
            ),
        ),
    ]

    preflight = run_full_data_preflight(
        source_path=source_path,
        operations=operations,
    )

    assert preflight[
        "passed"
    ] is True

    assert (
        preflight["checks"][0][
            "diagnostics"
        ][
            "ambiguous_mapping_groups"
        ]
        == 0
    )

    result = (
        apply_full_pipeline_to_silver(
            source_path=source_path,
            silver_path=silver_path,
            operations=operations,
        )
    )

    assert result[
        "working_row_count"
    ] == 4

    assert silver_path.exists()

    silver_profile = profile_parquet(
        silver_path
    )

    assert silver_profile[
        "null_counts"
    ]["label"] == 0


def test_large_preview_filters_without_loading_full_dataframe(
    tmp_path,
):
    source_path = _write_csv(
        tmp_path,
        pd.DataFrame(
            {
                "city": [
                    "Den Haag",
                    "Delft",
                    "Den Haag",
                    "Leiden",
                ],
                "delay": [
                    5,
                    25,
                    45,
                    10,
                ],
            }
        ),
    )

    result = query_large_data_preview(
        source_path=source_path,
        page=1,
        page_size=25,
        filters=[
            {
                "column": "city",
                "operator": "equals",
                "value": "Den Haag",
                "value_to": None,
            },
            {
                "column": "delay",
                "operator":
                    "greater_than",
                "value": "20",
                "value_to": None,
            },
        ],
        filter_logic="and",
    )

    assert result[
        "total_row_count"
    ] == 4

    assert result[
        "filtered_row_count"
    ] == 1

    assert result[
        "rows"
    ].iloc[0]["delay"] == 45

