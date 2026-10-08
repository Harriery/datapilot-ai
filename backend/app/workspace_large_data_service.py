from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from backend.app.models import (
    DataQualityAnalysis,
    DataQualityFinding,
    WorkspaceWorkbenchOperation,
)
from backend.app.local_data_quality_service import (
    analyze_dataframe_locally,
)


SMART_SAMPLE_CANDIDATES = (
    5_000,
    10_000,
    20_000,
)

REPRESENTATION_THRESHOLD = 95.0
RARE_COVERAGE_THRESHOLD = 90.0


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _lit(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _path_literal(path: Path) -> str:
    return _lit(str(path.resolve()))


def _source_sql(path: Path) -> str:
    return (
        "read_csv_auto("
        f"{_path_literal(path)}, "
        "header=true, sample_size=-1"
        ")"
    )


def _relation_profile(
    connection: duckdb.DuckDBPyConnection,
    relation_sql: str,
) -> dict:
    describe_rows = connection.execute(
        f"DESCRIBE SELECT * FROM {relation_sql}"
    ).fetchall()

    columns = [
        str(row[0])
        for row in describe_rows
    ]
    data_types = {
        str(row[0]): str(row[1])
        for row in describe_rows
    }

    row_count = int(
        connection.execute(
            f"SELECT COUNT(*) FROM {relation_sql}"
        ).fetchone()[0]
    )

    null_counts: dict[str, int] = {}
    distinct_counts: dict[str, int] = {}
    column_examples: dict[str, list[str]] = {}
    numeric_columns: list[str] = []
    numeric_summary: dict[str, dict] = {}
    categorical_distributions: dict[
        str, list[dict]
    ] = {}
    datetime_summary: dict[str, dict] = {}

    numeric_prefixes = (
        "TINYINT",
        "SMALLINT",
        "INTEGER",
        "BIGINT",
        "HUGEINT",
        "UTINYINT",
        "USMALLINT",
        "UINTEGER",
        "UBIGINT",
        "FLOAT",
        "DOUBLE",
        "DECIMAL",
    )

    for column in columns:
        quoted = _q(column)

        null_count = int(
            connection.execute(
                (
                    "SELECT COUNT(*) FILTER "
                    f"(WHERE {quoted} IS NULL) "
                    f"FROM {relation_sql}"
                )
            ).fetchone()[0]
        )
        null_counts[column] = null_count

        distinct_count = int(
            connection.execute(
                (
                    "SELECT COUNT(DISTINCT "
                    f"{quoted}) FROM {relation_sql}"
                )
            ).fetchone()[0]
        )
        distinct_counts[column] = distinct_count

        examples = connection.execute(
            (
                f"SELECT DISTINCT {quoted} "
                f"FROM {relation_sql} "
                f"WHERE {quoted} IS NOT NULL "
                "LIMIT 3"
            )
        ).fetchall()
        column_examples[column] = [
            str(row[0])
            for row in examples
        ]

        duck_type = data_types[
            column
        ].upper()

        if duck_type.startswith(
            numeric_prefixes
        ):
            numeric_columns.append(
                column
            )
            result = connection.execute(
                (
                    "SELECT "
                    f"COUNT({quoted}), "
                    f"AVG({quoted}), "
                    f"MIN({quoted}), "
                    f"MAX({quoted}), "
                    f"quantile_cont({quoted}, 0.25), "
                    f"quantile_cont({quoted}, 0.50), "
                    f"quantile_cont({quoted}, 0.75), "
                    f"quantile_cont({quoted}, 0.95) "
                    f"FROM {relation_sql}"
                )
            ).fetchone()

            numeric_summary[column] = {
                "count": int(
                    result[0] or 0
                ),
                "mean": (
                    float(result[1])
                    if result[1]
                    is not None
                    else None
                ),
                "min": (
                    float(result[2])
                    if result[2]
                    is not None
                    else None
                ),
                "max": (
                    float(result[3])
                    if result[3]
                    is not None
                    else None
                ),
                "p25": (
                    float(result[4])
                    if result[4]
                    is not None
                    else None
                ),
                "p50": (
                    float(result[5])
                    if result[5]
                    is not None
                    else None
                ),
                "p75": (
                    float(result[6])
                    if result[6]
                    is not None
                    else None
                ),
                "p95": (
                    float(result[7])
                    if result[7]
                    is not None
                    else None
                ),
            }

        if (
            "DATE" in duck_type
            or "TIMESTAMP" in duck_type
        ):
            result = connection.execute(
                (
                    "SELECT "
                    f"MIN({quoted}), "
                    f"MAX({quoted}) "
                    f"FROM {relation_sql}"
                )
            ).fetchone()

            datetime_summary[
                column
            ] = {
                "min": (
                    str(result[0])
                    if result[0]
                    is not None
                    else None
                ),
                "max": (
                    str(result[1])
                    if result[1]
                    is not None
                    else None
                ),
            }

        if (
            1 < distinct_count <= 100
            and not duck_type.startswith(
                numeric_prefixes
            )
        ):
            rows = connection.execute(
                (
                    "SELECT "
                    f"{quoted}, COUNT(*) AS n "
                    f"FROM {relation_sql} "
                    f"WHERE {quoted} IS NOT NULL "
                    f"GROUP BY {quoted} "
                    "ORDER BY n DESC"
                )
            ).fetchall()

            categorical_distributions[
                column
            ] = [
                {
                    "value": str(row[0]),
                    "count": int(row[1]),
                }
                for row in rows
            ]

    duplicate_count = int(
        connection.execute(
            (
                "SELECT COALESCE(SUM(n - 1), 0) "
                "FROM ("
                "SELECT COUNT(*) AS n "
                f"FROM {relation_sql} "
                "GROUP BY ALL "
                "HAVING COUNT(*) > 1"
                ") duplicates"
            )
        ).fetchone()[0]
    )

    return {
        "row_count": row_count,
        "column_count": len(
            columns
        ),
        "columns": columns,
        "data_types": data_types,
        "null_counts": null_counts,
        "distinct_counts":
            distinct_counts,
        "column_examples":
            column_examples,
        "duplicate_count":
            duplicate_count,
        "sample_rows": [],
        "numeric_columns":
            numeric_columns,
        "numeric_summary":
            numeric_summary,
        "datetime_summary":
            datetime_summary,
        "categorical_distributions":
            categorical_distributions,
        "profile_scope": "full_dataset",
        "profile_engine": "duckdb",
    }


def build_full_data_profile(
    source_path: Path,
) -> dict:
    if not source_path.exists():
        raise FileNotFoundError(
            "Workspace source datası bulunamadı."
        )

    with duckdb.connect() as connection:
        return _relation_profile(
            connection,
            _source_sql(
                source_path
            ),
        )


def _reservoir_sample(
    connection: duckdb.DuckDBPyConnection,
    relation_sql: str,
    size: int,
    seed: int,
) -> pd.DataFrame:
    return connection.execute(
        (
            f"SELECT * FROM {relation_sql} "
            "USING SAMPLE "
            f"reservoir({size} ROWS) "
            f"REPEATABLE ({seed})"
        )
    ).df()


def _missing_similarity(
    sample: pd.DataFrame,
    profile: dict,
) -> float:
    full_rows = max(
        int(profile["row_count"]),
        1,
    )

    differences = []

    for column in profile[
        "columns"
    ]:
        full_rate = (
            profile[
                "null_counts"
            ].get(
                column,
                0,
            )
            / full_rows
        )

        if column not in sample:
            differences.append(1.0)
            continue

        sample_rate = float(
            sample[column]
            .isna()
            .mean()
        )

        differences.append(
            abs(
                full_rate
                - sample_rate
            )
        )

    if not differences:
        return 100.0

    return round(
        max(
            0.0,
            100.0
            * (
                1.0
                - sum(differences)
                / len(differences)
            ),
        ),
        2,
    )


def _categorical_scores(
    sample: pd.DataFrame,
    profile: dict,
) -> tuple[
    float,
    float,
]:
    distribution_scores = []
    rare_hits = 0
    rare_total = 0

    full_rows = max(
        int(profile["row_count"]),
        1,
    )

    for (
        column,
        full_items,
    ) in profile.get(
        "categorical_distributions",
        {},
    ).items():
        if (
            column not in sample
            or not full_items
        ):
            continue

        sample_counts = (
            sample[column]
            .dropna()
            .astype(str)
            .value_counts()
            .to_dict()
        )

        sample_rows = max(
            int(
                sample[
                    column
                ].notna().sum()
            ),
            1,
        )

        full_non_null_rows = max(
            full_rows
            - int(
                profile[
                    "null_counts"
                ].get(
                    column,
                    0,
                )
            ),
            1,
        )

        total_variation = 0.0

        for item in full_items:
            value = str(
                item["value"]
            )
            full_probability = (
                int(item["count"])
                / full_non_null_rows
            )
            sample_probability = (
                int(
                    sample_counts.get(
                        value,
                        0,
                    )
                )
                / sample_rows
            )

            total_variation += abs(
                full_probability
                - sample_probability
            )

            if (
                full_probability <= 0.01
                and int(
                    item["count"]
                ) >= 2
            ):
                rare_total += 1
                if (
                    sample_counts.get(
                        value,
                        0,
                    )
                    > 0
                ):
                    rare_hits += 1

        score = max(
            0.0,
            100.0
            * (
                1.0
                - min(
                    1.0,
                    total_variation
                    / 2.0,
                )
            ),
        )
        distribution_scores.append(
            score
        )

    distribution_score = (
        sum(
            distribution_scores
        )
        / len(
            distribution_scores
        )
        if distribution_scores
        else 100.0
    )

    rare_score = (
        100.0
        * rare_hits
        / rare_total
        if rare_total
        else 100.0
    )

    return (
        round(
            distribution_score,
            2,
        ),
        round(
            rare_score,
            2,
        ),
    )


def _numeric_similarity(
    sample: pd.DataFrame,
    profile: dict,
) -> float:
    scores = []

    for column in profile.get(
        "numeric_columns",
        [],
    ):
        if column not in sample:
            continue

        full = profile[
            "numeric_summary"
        ].get(
            column,
            {},
        )

        numeric = pd.to_numeric(
            sample[column],
            errors="coerce",
        ).dropna()

        if numeric.empty:
            continue

        sample_quantiles = {
            "p25": float(
                numeric.quantile(
                    0.25
                )
            ),
            "p50": float(
                numeric.quantile(
                    0.50
                )
            ),
            "p75": float(
                numeric.quantile(
                    0.75
                )
            ),
            "p95": float(
                numeric.quantile(
                    0.95
                )
            ),
        }

        minimum = full.get(
            "min"
        )
        maximum = full.get(
            "max"
        )

        scale = (
            abs(
                float(maximum)
                - float(minimum)
            )
            if (
                minimum
                is not None
                and maximum
                is not None
            )
            else 0.0
        )

        if scale == 0:
            scores.append(100.0)
            continue

        differences = []

        for key in (
            "p25",
            "p50",
            "p75",
            "p95",
        ):
            full_value = full.get(
                key
            )

            if full_value is None:
                continue

            differences.append(
                min(
                    1.0,
                    abs(
                        sample_quantiles[
                            key
                        ]
                        - float(
                            full_value
                        )
                    )
                    / scale,
                )
            )

        if differences:
            scores.append(
                100.0
                * (
                    1.0
                    - sum(
                        differences
                    )
                    / len(
                        differences
                    )
                )
            )

    if not scores:
        return 100.0

    return round(
        sum(scores)
        / len(scores),
        2,
    )


def _datetime_similarity(
    sample: pd.DataFrame,
    profile: dict,
) -> float:
    scores = []

    for (
        column,
        summary,
    ) in profile.get(
        "datetime_summary",
        {},
    ).items():
        if column not in sample:
            continue

        full_min = pd.to_datetime(
            summary.get("min"),
            errors="coerce",
        )
        full_max = pd.to_datetime(
            summary.get("max"),
            errors="coerce",
        )

        values = pd.to_datetime(
            sample[column],
            errors="coerce",
        ).dropna()

        if (
            pd.isna(full_min)
            or pd.isna(full_max)
            or values.empty
        ):
            continue

        full_span = (
            full_max
            - full_min
        ).total_seconds()

        if full_span <= 0:
            scores.append(100.0)
            continue

        sample_min = values.min()
        sample_max = values.max()

        sample_span = max(
            0.0,
            (
                sample_max
                - sample_min
            ).total_seconds(),
        )

        span_coverage = min(
            1.0,
            sample_span
            / full_span,
        )

        start_error = min(
            1.0,
            abs(
                (
                    sample_min
                    - full_min
                ).total_seconds()
            )
            / full_span,
        )

        end_error = min(
            1.0,
            abs(
                (
                    full_max
                    - sample_max
                ).total_seconds()
            )
            / full_span,
        )

        edge_score = max(
            0.0,
            1.0
            - (
                start_error
                + end_error
            )
            / 2.0,
        )

        scores.append(
            100.0
            * (
                span_coverage
                * 0.6
                + edge_score
                * 0.4
            )
        )

    if not scores:
        return 100.0

    return round(
        sum(scores)
        / len(scores),
        2,
    )


def evaluate_sample(
    sample: pd.DataFrame,
    profile: dict,
) -> dict:
    missing_score = (
        _missing_similarity(
            sample,
            profile,
        )
    )

    (
        categorical_score,
        rare_score,
    ) = _categorical_scores(
        sample,
        profile,
    )

    numeric_score = (
        _numeric_similarity(
            sample,
            profile,
        )
    )

    datetime_score = (
        _datetime_similarity(
            sample,
            profile,
        )
    )

    overall = (
        missing_score * 0.20
        + categorical_score * 0.25
        + numeric_score * 0.20
        + datetime_score * 0.15
        + rare_score * 0.20
    )

    sufficient = (
        overall
        >= REPRESENTATION_THRESHOLD
        and rare_score
        >= RARE_COVERAGE_THRESHOLD
        and min(
            missing_score,
            categorical_score,
            numeric_score,
            datetime_score,
        )
        >= 90.0
    )

    return {
        "sample_size": len(
            sample
        ),
        "missingness_similarity":
            missing_score,
        "categorical_distribution_similarity":
            categorical_score,
        "numeric_distribution_similarity":
            numeric_score,
        "datetime_coverage_similarity":
            datetime_score,
        "rare_group_coverage":
            rare_score,
        "overall_score": round(
            overall,
            2,
        ),
        "sufficient":
            sufficient,
    }


def _build_rare_targeted_rows(
    source_path: Path,
    profile: dict,
    limit: int,
    seed: int,
) -> pd.DataFrame:
    if limit <= 0:
        return pd.DataFrame()

    row_count = max(
        int(profile["row_count"]),
        1,
    )

    predicates: list[str] = []

    for (
        column,
        items,
    ) in profile.get(
        "categorical_distributions",
        {},
    ).items():
        rare_values = [
            str(item["value"])
            for item in items
            if (
                int(item["count"]) >= 2
                and (
                    int(item["count"])
                    / row_count
                )
                <= 0.01
            )
        ]

        if not rare_values:
            continue

        values_sql = ", ".join(
            _lit(value)
            for value in rare_values[
                :50
            ]
        )

        predicates.append(
            (
                "CAST("
                f"{_q(column)} "
                "AS VARCHAR) IN ("
                f"{values_sql}"
                ")"
            )
        )

        if len(predicates) >= 6:
            break

    if not predicates:
        return pd.DataFrame()

    predicate_sql = (
        " OR ".join(
            predicates
        )
    )

    with duckdb.connect() as connection:
        relation_sql = (
            _source_sql(
                source_path
            )
        )

        return connection.execute(
            (
                "SELECT * FROM ("
                f"SELECT * FROM {relation_sql} "
                f"WHERE {predicate_sql}"
                ") rare_rows "
                "USING SAMPLE "
                f"reservoir({limit} ROWS) "
                f"REPEATABLE ({seed})"
            )
        ).df()


def build_smart_development_sample(
    source_path: Path,
    profile: dict,
    candidate_sizes: tuple[
        int,
        ...,
    ] = SMART_SAMPLE_CANDIDATES,
    seed: int = 42,
) -> tuple[
    pd.DataFrame,
    dict,
]:
    source_row_count = int(
        profile["row_count"]
    )

    bounded_sizes = tuple(
        sorted(
            {
                int(size)
                for size in candidate_sizes
                if (
                    int(size) > 0
                    and int(size)
                    < source_row_count
                )
            }
        )
    )

    if not bounded_sizes:
        with duckdb.connect() as connection:
            full = connection.execute(
                (
                    "SELECT * FROM "
                    + _source_sql(
                        source_path
                    )
                )
            ).df()

        full_evaluation = (
            evaluate_sample(
                full,
                profile,
            )
        )

        report = {
            "candidate_evaluations": [
                {
                    **full_evaluation,
                    "sample_size":
                        len(full),
                }
            ],
            "selected_size":
                len(full),
            "selected_strategy":
                "full_dataset",
            "selected_evaluation":
                full_evaluation,
            "threshold":
                REPRESENTATION_THRESHOLD,
            "rare_coverage_threshold":
                RARE_COVERAGE_THRESHOLD,
            "reason":
                (
                    "Dataset is smaller than "
                    "the smart-sampling candidates."
                ),
            "full_data_preflight_required":
                False,
        }

        return (
            full,
            report,
        )

    largest = max(
        bounded_sizes
    )

    with duckdb.connect() as connection:
        relation_sql = (
            _source_sql(
                source_path
            )
        )

        pool = _reservoir_sample(
            connection,
            relation_sql,
            largest,
            seed,
        )

    pool = (
        pool.sample(
            frac=1.0,
            random_state=seed,
        )
        .reset_index(
            drop=True
        )
    )

    # Evaluate every requested candidate. We deliberately do not stop
    # after the first passing size: the UI should be able to compare
    # 5k, 10k and 20k even when 5k already looks acceptable.
    evaluations: list[dict] = []
    candidates: dict[
        int,
        pd.DataFrame,
    ] = {}

    for size in bounded_sizes:
        candidate = (
            pool.head(
                size
            )
            .copy()
            .reset_index(
                drop=True
            )
        )

        result = evaluate_sample(
            candidate,
            profile,
        )
        result[
            "sample_size"
        ] = size

        candidates[
            size
        ] = candidate
        evaluations.append(
            result
        )

    sufficient_sizes = [
        int(item["sample_size"])
        for item in evaluations
        if item["sufficient"]
    ]

    selected_size = (
        min(sufficient_sizes)
        if sufficient_sizes
        else largest
    )

    selected = (
        candidates[
            selected_size
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )

    selected_eval = (
        evaluate_sample(
            selected,
            profile,
        )
    )

    strategy = (
        "smart_representative"
        if selected_eval[
            "sufficient"
        ]
        else "smart_best_available"
    )

    refinement = None

    # If even the largest normal candidate misses the thresholds, try a
    # hybrid refinement instead of blindly asking for a larger sample.
    # Keep most rows representative and reserve up to 10% for rare groups.
    if not selected_eval[
        "sufficient"
    ]:
        targeted_limit = min(
            max(
                int(
                    selected_size
                    * 0.10
                ),
                1,
            ),
            2_000,
        )

        targeted = (
            _build_rare_targeted_rows(
                source_path=source_path,
                profile=profile,
                limit=targeted_limit,
                seed=seed + 1,
            )
        )

        if not targeted.empty:
            base_size = max(
                selected_size
                - len(targeted),
                0,
            )

            hybrid = pd.concat(
                [
                    targeted,
                    selected.head(
                        base_size
                    ),
                ],
                ignore_index=True,
            )

            hybrid = (
                hybrid.sample(
                    frac=1.0,
                    random_state=seed,
                )
                .head(
                    selected_size
                )
                .reset_index(
                    drop=True
                )
            )

            hybrid_eval = (
                evaluate_sample(
                    hybrid,
                    profile,
                )
            )

            refinement = {
                "strategy":
                    "rare_group_hybrid",
                "targeted_rows":
                    len(targeted),
                "before":
                    selected_eval,
                "after":
                    hybrid_eval,
            }

            # Use refinement only if it improves overall quality or turns
            # the candidate into a sufficient one.
            if (
                hybrid_eval[
                    "sufficient"
                ]
                or hybrid_eval[
                    "overall_score"
                ]
                > selected_eval[
                    "overall_score"
                ]
            ):
                selected = hybrid
                selected_eval = (
                    hybrid_eval
                )
                strategy = (
                    "smart_hybrid"
                )

    reason = (
        (
            f"{selected_size:,} rows is the "
            "smallest candidate that met the "
            "representation thresholds."
        )
        if (
            strategy
            == "smart_representative"
        )
        else (
            (
                f"{selected_size:,} rows needed "
                "rare-group refinement; the hybrid "
                "sample improved representation."
            )
            if strategy
            == "smart_hybrid"
            else (
                "No candidate met every threshold. "
                "The largest measured candidate is "
                "kept; full-data preflight remains "
                "mandatory before full apply."
            )
        )
    )

    report = {
        "candidate_evaluations":
            evaluations,
        "selected_size":
            selected_size,
        "selected_strategy":
            strategy,
        "selected_evaluation":
            selected_eval,
        "threshold":
            REPRESENTATION_THRESHOLD,
        "rare_coverage_threshold":
            RARE_COVERAGE_THRESHOLD,
        "reason":
            reason,
        "refinement":
            refinement,
        "full_data_preflight_required":
            True,
    }

    return (
        selected,
        report,
    )


def build_full_quality_analysis(
    profile: dict,
    development_sample: pd.DataFrame,
) -> DataQualityAnalysis:
    sample_analysis = (
        analyze_dataframe_locally(
            development_sample
        )
    )

    findings = [
        finding
        for finding
        in sample_analysis.findings
        if finding.issue_type
        not in {
            "missing_values",
            "duplicate_rows",
        }
    ]

    row_count = max(
        int(
            profile[
                "row_count"
            ]
        ),
        1,
    )

    for column in profile[
        "columns"
    ]:
        missing_count = int(
            profile[
                "null_counts"
            ].get(
                column,
                0,
            )
        )

        if missing_count == 0:
            continue

        missing_percent = round(
            missing_count
            / row_count
            * 100,
            2,
        )

        findings.append(
            DataQualityFinding(
                issue_type=(
                    "missing_values"
                ),
                column=column,
                severity=(
                    "high"
                    if missing_percent
                    >= 50
                    else "medium"
                ),
                observation=(
                    f"{missing_count} missing "
                    f"values found "
                    f"({missing_percent}%)."
                ),
                suggested_action=(
                    "Inspect affected rows and "
                    "confirm the business rule "
                    "before dropping or filling."
                ),
            )
        )

    duplicate_count = int(
        profile.get(
            "duplicate_count",
            0,
        )
    )

    if duplicate_count > 0:
        duplicate_percent = round(
            duplicate_count
            / row_count
            * 100,
            2,
        )

        findings.append(
            DataQualityFinding(
                issue_type=(
                    "duplicate_rows"
                ),
                column=None,
                severity=(
                    "high"
                    if duplicate_percent
                    >= 20
                    else "medium"
                ),
                observation=(
                    f"{duplicate_count} duplicate "
                    f"rows found "
                    f"({duplicate_percent}%)."
                ),
                suggested_action=(
                    "Inspect duplicate rows and "
                    "confirm whether they are true "
                    "duplicates before removing."
                ),
            )
        )

    return DataQualityAnalysis(
        findings=findings
    )


def _validate_replayable_operations(
    operations: list[
        WorkspaceWorkbenchOperation
    ],
) -> list[
    WorkspaceWorkbenchOperation
]:
    unfinished = [
        operation.title
        for operation in operations
        if operation.status
        != "completed"
    ]

    if unfinished:
        raise ValueError(
            (
                "Full-data preflight requires "
                "completed Workbench operations: "
                + ", ".join(
                    unfinished
                )
            )
        )

    non_replayable = [
        operation.title
        for operation in operations
        if (
            operation.status
            == "completed"
            and operation.pipeline_action
            is None
            and operation.decision
            != "accepted_as_is"
        )
    ]

    if non_replayable:
        raise ValueError(
            (
                "These operations do not contain "
                "structured pipeline metadata: "
                + ", ".join(
                    non_replayable
                )
            )
        )

    return [
        operation
        for operation in operations
        if operation.pipeline_action
        is not None
    ]


def run_full_data_preflight(
    source_path: Path,
    operations: list[
        WorkspaceWorkbenchOperation
    ],
) -> dict:
    replayable = (
        _validate_replayable_operations(
            operations
        )
    )

    checks = []

    with duckdb.connect() as connection:
        source_sql = (
            _source_sql(
                source_path
            )
        )

        connection.execute(
            (
                "CREATE OR REPLACE TEMP VIEW "
                "preflight_0 AS "
                f"SELECT * FROM {source_sql}"
            )
        )

        current_view = "preflight_0"

        columns = [
            str(row[0])
            for row in connection.execute(
                (
                    "DESCRIBE SELECT * "
                    f"FROM {current_view}"
                )
            ).fetchall()
        ]

        row_count = int(
            connection.execute(
                (
                    "SELECT COUNT(*) "
                    f"FROM {current_view}"
                )
            ).fetchone()[0]
        )

        for index, operation in enumerate(
            replayable,
            start=1,
        ):
            action = (
                operation.pipeline_action
            )

            assert action is not None

            required = {
                action.column
            }

            if (
                action.mapping_source_column
            ):
                required.add(
                    action.mapping_source_column
                )

            for replacement in (
                action.replacements
            ):
                for condition in (
                    replacement.conditions
                ):
                    required.add(
                        condition.column
                    )

            missing = sorted(
                required
                - set(columns)
            )

            affected_rows = None
            diagnostics: dict = {}

            if not missing:
                quoted = _q(
                    action.column
                )

                if (
                    action.action
                    == "fill_missing"
                ):
                    affected_rows = int(
                        connection.execute(
                            (
                                "SELECT COUNT(*) "
                                f"FROM {current_view} "
                                f"WHERE {quoted} "
                                "IS NULL"
                            )
                        ).fetchone()[0]
                    )

                    if (
                        action.fill_strategy
                        == "mapping"
                        and action.mapping_source_column
                    ):
                        source_column = _q(
                            action.mapping_source_column
                        )

                        mapping_stats = (
                            connection.execute(
                                (
                                    "SELECT "
                                    "COUNT(*) FILTER "
                                    "(WHERE distinct_targets = 1) "
                                    "AS safe_groups, "
                                    "COUNT(*) FILTER "
                                    "(WHERE distinct_targets > 1) "
                                    "AS ambiguous_groups "
                                    "FROM ("
                                    "SELECT "
                                    f"{source_column}, "
                                    "COUNT(DISTINCT "
                                    f"{quoted}) AS "
                                    "distinct_targets "
                                    f"FROM {current_view} "
                                    f"WHERE {quoted} "
                                    "IS NOT NULL AND "
                                    f"{source_column} "
                                    "IS NOT NULL "
                                    f"GROUP BY {source_column}"
                                    ") mapping_groups"
                                )
                            ).fetchone()
                        )

                        diagnostics[
                            "safe_mapping_groups"
                        ] = int(
                            mapping_stats[0]
                            or 0
                        )
                        diagnostics[
                            "ambiguous_mapping_groups"
                        ] = int(
                            mapping_stats[1]
                            or 0
                        )

                elif (
                    action.action
                    == "replace_values"
                ):
                    if action.replacements:
                        affected_rows = 0

                        for replacement in (
                            action.replacements
                        ):
                            conditions = [
                                (
                                    f"{quoted} IS NOT "
                                    "DISTINCT FROM "
                                    f"{_lit(replacement.old_value)}"
                                )
                            ]

                            for condition in (
                                replacement.conditions
                            ):
                                conditions.append(
                                    (
                                        f"{_q(condition.column)} "
                                        "IS NOT DISTINCT FROM "
                                        f"{_lit(condition.value)}"
                                    )
                                )

                            count = int(
                                connection.execute(
                                    (
                                        "SELECT COUNT(*) "
                                        f"FROM {current_view} "
                                        "WHERE "
                                        + " AND ".join(
                                            conditions
                                        )
                                    )
                                ).fetchone()[0]
                            )
                            affected_rows += count

                    else:
                        affected_rows = int(
                            connection.execute(
                                (
                                    "SELECT COUNT(*) "
                                    f"FROM {current_view} "
                                    f"WHERE {quoted} "
                                    "IS NOT DISTINCT FROM "
                                    f"{_lit(action.old_value)}"
                                )
                            ).fetchone()[0]
                        )

                elif (
                    action.action
                    in {
                        "rename",
                        "remove",
                        "change_type",
                        "derived",
                    }
                ):
                    affected_rows = row_count

            check = {
                "operation_id":
                    operation.operation_id,
                "title":
                    operation.title,
                "action":
                    action.action,
                "passed":
                    len(missing) == 0,
                "missing_columns":
                    missing,
                "affected_rows":
                    affected_rows,
            }

            if diagnostics:
                check[
                    "diagnostics"
                ] = diagnostics

            checks.append(
                check
            )

            if missing:
                continue

            # Keep preflight schema sequential. This matters when a later
            # operation refers to a column created/renamed earlier.
            next_view = (
                f"preflight_{index}"
            )

            if (
                action.action
                == "rename"
                and action.new_name
            ):
                select_sql = (
                    _select_except(
                        columns,
                        action.column,
                        _q(
                            action.column
                        ),
                        action.new_name,
                    )
                )
                columns = [
                    (
                        action.new_name
                        if column
                        == action.column
                        else column
                    )
                    for column in columns
                ]

            elif action.action == "remove":
                columns = [
                    column
                    for column in columns
                    if column
                    != action.column
                ]
                select_sql = ", ".join(
                    _q(column)
                    for column in columns
                )

            elif (
                action.action
                == "derived"
                and action.derived_name
                and action.derived_operation
            ):
                source = _q(
                    action.column
                )

                if (
                    action.derived_operation
                    == "copy"
                ):
                    derived = source
                elif (
                    action.derived_operation
                    == "uppercase"
                ):
                    derived = (
                        f"UPPER(CAST({source} "
                        "AS VARCHAR))"
                    )
                elif (
                    action.derived_operation
                    == "lowercase"
                ):
                    derived = (
                        f"LOWER(CAST({source} "
                        "AS VARCHAR))"
                    )
                elif (
                    action.derived_operation
                    == "add"
                    and action.derived_value
                    is not None
                ):
                    derived = (
                        f"{source} + "
                        f"{_lit(action.derived_value)}"
                    )
                elif (
                    action.derived_operation
                    == "multiply"
                    and action.derived_value
                    is not None
                ):
                    derived = (
                        f"{source} * "
                        f"{_lit(action.derived_value)}"
                    )
                else:
                    derived = source

                select_sql = (
                    "*, "
                    f"{derived} AS "
                    f"{_q(action.derived_name)}"
                )

                if (
                    action.derived_name
                    not in columns
                ):
                    columns.append(
                        action.derived_name
                    )

            else:
                # Value-only transforms do not need to be materialized
                # during preflight; their full-data affected counts above
                # are the evidence we need before full execution.
                continue

            connection.execute(
                (
                    "CREATE OR REPLACE TEMP VIEW "
                    f"{next_view} AS "
                    f"SELECT {select_sql} "
                    f"FROM {current_view} AS src"
                )
            )

            current_view = (
                next_view
            )

    passed = all(
        check["passed"]
        for check in checks
    )

    return {
        "passed": passed,
        "source_row_count":
            row_count,
        "checks": checks,
        "engine": "duckdb",
    }


def _select_except(
    columns: list[str],
    replacement_column: str,
    replacement_expression: str,
    replacement_alias: str | None = None,
) -> str:
    expressions = []

    for column in columns:
        if column == replacement_column:
            alias = (
                replacement_alias
                or column
            )
            expressions.append(
                (
                    f"{replacement_expression} "
                    f"AS {_q(alias)}"
                )
            )
        else:
            expressions.append(
                _q(column)
            )

    return ", ".join(
        expressions
    )


def apply_full_pipeline_to_silver(
    source_path: Path,
    silver_path: Path,
    operations: list[
        WorkspaceWorkbenchOperation
    ],
) -> dict:
    replayable = (
        _validate_replayable_operations(
            operations
        )
    )

    silver_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = (
        silver_path.parent
        / "cleaned.tmp.parquet"
    )

    with duckdb.connect() as connection:
        relation_sql = (
            _source_sql(
                source_path
            )
        )

        columns = [
            str(row[0])
            for row in connection.execute(
                (
                    "DESCRIBE SELECT * "
                    f"FROM {relation_sql}"
                )
            ).fetchall()
        ]

        connection.execute(
            (
                "CREATE OR REPLACE TEMP VIEW "
                "pipeline_0 AS "
                f"SELECT * FROM {relation_sql}"
            )
        )

        current_view = (
            "pipeline_0"
        )

        applied_ids = []

        for index, operation in enumerate(
            replayable,
            start=1,
        ):
            action = (
                operation.pipeline_action
            )
            assert action is not None

            if action.column not in columns:
                raise ValueError(
                    (
                        "Pipeline column not found "
                        f"during full apply: "
                        f"{action.column}"
                    )
                )

            next_view = (
                f"pipeline_{index}"
            )

            if action.action == "rename":
                if not action.new_name:
                    raise ValueError(
                        "Rename requires new_name."
                    )

                select_sql = (
                    _select_except(
                        columns,
                        action.column,
                        _q(
                            action.column
                        ),
                        action.new_name,
                    )
                )
                columns = [
                    (
                        action.new_name
                        if column
                        == action.column
                        else column
                    )
                    for column in columns
                ]

            elif action.action == "remove":
                remaining = [
                    column
                    for column in columns
                    if column
                    != action.column
                ]

                if not remaining:
                    raise ValueError(
                        "Pipeline cannot remove "
                        "the final column."
                    )

                select_sql = ", ".join(
                    _q(column)
                    for column in remaining
                )
                columns = remaining

            elif action.action == "change_type":
                casts = {
                    "string":
                        "VARCHAR",
                    "integer":
                        "BIGINT",
                    "float":
                        "DOUBLE",
                    "datetime":
                        "TIMESTAMP",
                }

                if (
                    action.data_type
                    not in casts
                ):
                    raise ValueError(
                        "Unsupported target type."
                    )

                expression = (
                    "TRY_CAST("
                    f"{_q(action.column)} "
                    f"AS {casts[action.data_type]}"
                    ")"
                )

                select_sql = (
                    _select_except(
                        columns,
                        action.column,
                        expression,
                    )
                )

            elif action.action == "fill_missing":
                column = _q(
                    action.column
                )

                if (
                    action.fill_strategy
                    == "value"
                ):
                    fill_expression = (
                        _lit(
                            action.fill_value
                        )
                    )

                elif (
                    action.fill_strategy
                    == "zero"
                ):
                    fill_expression = "0"

                elif (
                    action.fill_strategy
                    == "mean"
                ):
                    fill_expression = (
                        f"AVG({column}) OVER ()"
                    )

                elif (
                    action.fill_strategy
                    == "median"
                ):
                    fill_expression = (
                        f"median({column}) OVER ()"
                    )

                elif (
                    action.fill_strategy
                    == "mode"
                ):
                    fill_expression = (
                        "("
                        f"SELECT mode({column}) "
                        f"FROM {current_view}"
                        ")"
                    )

                elif (
                    action.fill_strategy
                    == "mapping"
                ):
                    if not action.mapping_source_column:
                        raise ValueError(
                            "Mapping fill requires "
                            "mapping_source_column."
                        )

                    mapping_source = _q(
                        action.mapping_source_column
                    )

                    if (
                        action.mapping_source_column
                        not in columns
                    ):
                        raise ValueError(
                            (
                                "Mapping source column "
                                "not found during full "
                                "apply: "
                                f"{action.mapping_source_column}"
                            )
                        )

                    expression = (
                        "CASE WHEN "
                        f"src.{column} IS NULL "
                        "THEN ("
                        "SELECT CASE "
                        "WHEN COUNT(DISTINCT "
                        f"m.{column}) = 1 "
                        f"THEN MIN(m.{column}) "
                        "ELSE NULL END "
                        f"FROM {current_view} AS m "
                        "WHERE "
                        f"m.{mapping_source} "
                        "IS NOT DISTINCT FROM "
                        f"src.{mapping_source} "
                        f"AND m.{column} IS NOT NULL"
                        ") ELSE "
                        f"src.{column} END"
                    )

                    select_sql = (
                        _select_except(
                            columns,
                            action.column,
                            expression,
                        )
                    )

                    fill_expression = None

                else:
                    raise ValueError(
                        (
                            "Unsupported fill strategy "
                            "during large-data apply: "
                            f"{action.fill_strategy}"
                        )
                    )

                if (
                    action.fill_strategy
                    != "mapping"
                ):
                    expression = (
                        f"COALESCE({column}, "
                        f"{fill_expression})"
                    )

                    select_sql = (
                        _select_except(
                            columns,
                            action.column,
                            expression,
                        )
                    )

            elif action.action == "replace_values":
                column = _q(
                    action.column
                )

                if action.replacements:
                    cases = []

                    for replacement in (
                        action.replacements
                    ):
                        conditions = [
                            (
                                f"{column} IS NOT "
                                "DISTINCT FROM "
                                f"{_lit(replacement.old_value)}"
                            )
                        ]

                        for condition in (
                            replacement.conditions
                        ):
                            conditions.append(
                                (
                                    f"{_q(condition.column)} "
                                    "IS NOT DISTINCT FROM "
                                    f"{_lit(condition.value)}"
                                )
                            )

                        cases.append(
                            (
                                "WHEN "
                                + " AND ".join(
                                    conditions
                                )
                                + " THEN "
                                + _lit(
                                    replacement.new_value
                                )
                            )
                        )

                    expression = (
                        "CASE "
                        + " ".join(
                            cases
                        )
                        + f" ELSE {column} END"
                    )

                else:
                    expression = (
                        "CASE WHEN "
                        f"{column} IS NOT DISTINCT "
                        f"FROM {_lit(action.old_value)} "
                        f"THEN {_lit(action.new_value)} "
                        f"ELSE {column} END"
                    )

                select_sql = (
                    _select_except(
                        columns,
                        action.column,
                        expression,
                    )
                )

            elif action.action == "derived":
                if (
                    not action.derived_name
                    or not action.derived_operation
                ):
                    raise ValueError(
                        "Derived action is incomplete."
                    )

                source = _q(
                    action.column
                )

                if (
                    action.derived_operation
                    == "copy"
                ):
                    derived = source
                elif (
                    action.derived_operation
                    == "uppercase"
                ):
                    derived = (
                        f"UPPER(CAST({source} "
                        "AS VARCHAR))"
                    )
                elif (
                    action.derived_operation
                    == "lowercase"
                ):
                    derived = (
                        f"LOWER(CAST({source} "
                        "AS VARCHAR))"
                    )
                elif (
                    action.derived_operation
                    == "add"
                ):
                    derived = (
                        f"{source} + "
                        f"{_lit(action.derived_value)}"
                    )
                elif (
                    action.derived_operation
                    == "multiply"
                ):
                    derived = (
                        f"{source} * "
                        f"{_lit(action.derived_value)}"
                    )
                else:
                    raise ValueError(
                        "Unsupported derived operation."
                    )

                select_sql = (
                    "*, "
                    f"{derived} AS "
                    f"{_q(action.derived_name)}"
                )

                if (
                    action.derived_name
                    not in columns
                ):
                    columns.append(
                        action.derived_name
                    )

            else:
                raise ValueError(
                    (
                        "Unsupported large-data "
                        f"pipeline action: "
                        f"{action.action}"
                    )
                )

            connection.execute(
                (
                    "CREATE OR REPLACE TEMP VIEW "
                    f"{next_view} AS "
                    f"SELECT {select_sql} "
                    f"FROM {current_view}"
                )
            )

            current_view = (
                next_view
            )

            applied_ids.append(
                operation.operation_id
            )

        row_count = int(
            connection.execute(
                (
                    "SELECT COUNT(*) "
                    f"FROM {current_view}"
                )
            ).fetchone()[0]
        )

        if row_count == 0:
            raise ValueError(
                "Pipeline removed every row."
            )

        connection.execute(
            (
                "COPY (SELECT * FROM "
                f"{current_view}) TO "
                f"{_path_literal(temporary_path)} "
                "(FORMAT PARQUET, "
                "COMPRESSION ZSTD)"
            )
        )

    temporary_path.replace(
        silver_path
    )

    return {
        "working_row_count":
            row_count,
        "applied_operation_ids":
            applied_ids,
        "applied_operation_count":
            len(applied_ids),
        "silver_path":
            str(silver_path),
        "engine":
            "duckdb",
    }


def profile_parquet(
    parquet_path: Path,
) -> dict:
    if not parquet_path.exists():
        raise FileNotFoundError(
            "Silver dataset bulunamadı."
        )

    with duckdb.connect() as connection:
        return _relation_profile(
            connection,
            (
                "read_parquet("
                f"{_path_literal(parquet_path)}"
                ")"
            ),
        )
