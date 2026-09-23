from pathlib import Path

import pandas as pd

from backend.app.models import (
    PersonalProjectAnalysisPlan,
    PersonalProjectAnalysisResult,
    PersonalProjectColumnIntelligence,
    PersonalProjectModelDiscovery,
)

TIME_COLUMN_NAMES = {
    "year", "date", "datetime", "timestamp",
    "month", "quarter", "week", "day",
}
IDENTIFIER_COLUMN_NAMES = {"id", "uuid", "identifier"}
ENTITY_IDENTITY_COLUMN_NAMES = {
    "name", "first_name", "last_name", "full_name",
    "email", "phone", "telephone",
}


def _normalize_column_name(column: str) -> str:
    return (
        column.strip().lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def _is_time_column(column: str) -> bool:
    normalized = _normalize_column_name(column)
    return (
        normalized in TIME_COLUMN_NAMES
        or any(normalized.endswith(f"_{name}") for name in TIME_COLUMN_NAMES)
    )


def _is_identifier_column(column: str) -> bool:
    normalized = _normalize_column_name(column)
    return (
        normalized in IDENTIFIER_COLUMN_NAMES
        or normalized.endswith("_id")
    )


def _is_entity_identity_column(column: str) -> bool:
    return _normalize_column_name(column) in ENTITY_IDENTITY_COLUMN_NAMES


def _fact_table_name(dataset_filename: str | None) -> str:
    if not dataset_filename:
        return "fact_dataset"
    return f"fact_{_normalize_column_name(Path(dataset_filename).stem)}"


def build_personal_analysis_plan(
    profile: dict,
    dataset_filename: str | None = None,
) -> PersonalProjectAnalysisPlan:
    columns = profile.get("columns", [])
    row_count = int(profile.get("row_count", 0) or 0)
    numeric_columns = set(profile.get("numeric_columns", []))
    data_types = profile.get("data_types", {})
    null_counts = profile.get("null_counts", {})
    distinct_counts = profile.get("distinct_counts", {})
    examples = profile.get("column_examples", {})
    numeric_summary = profile.get("numeric_summary", {})

    time_candidates = [
        column for column in columns
        if _is_time_column(column)
    ]

    numeric_candidates = [
        column for column in columns
        if (
            column in numeric_columns
            and column not in time_candidates
            and not _is_identifier_column(column)
        )
    ]

    dimension_candidates = [
        column for column in columns
        if (
            column not in numeric_candidates
            and column not in time_candidates
            and not _is_identifier_column(column)
            and not _is_entity_identity_column(column)
        )
    ]

    key_candidates = [
        column for column in columns
        if (
            _is_identifier_column(column)
            and row_count > 0
            and int(null_counts.get(column, 0) or 0) == 0
            and int(distinct_counts.get(column, 0) or 0) == row_count
        )
    ]

    column_intelligence = []
    for column in columns:
        null_count = int(null_counts.get(column, 0) or 0)
        distinct_count = int(distinct_counts.get(column, 0) or 0)
        roles = []
        reasoning = []

        if column in key_candidates:
            roles.append("key")
            reasoning.append("Identifier-like name with unique, non-null values.")
        if column in time_candidates:
            roles.append("time")
            reasoning.append("Column name indicates a time or date field.")
        if column in numeric_candidates:
            roles.append("numeric")
            reasoning.append("Numeric field that can support aggregations.")
        if column in dimension_candidates:
            roles.append("dimension")
            reasoning.append("Descriptive field suitable for grouping.")
        if not reasoning:
            reasoning.append("No strong analytical role detected automatically.")

        stats = numeric_summary.get(column, {})
        confidence = (
            "high"
            if column in key_candidates or column in time_candidates
            else "medium"
            if column in numeric_candidates or column in dimension_candidates
            else "low"
        )

        column_intelligence.append(
            PersonalProjectColumnIntelligence(
                name=column,
                data_type=str(data_types.get(column, "unknown")),
                null_count=null_count,
                null_percentage=(
                    round((null_count / row_count) * 100, 2)
                    if row_count else 0.0
                ),
                distinct_count=distinct_count,
                cardinality_ratio=(
                    round(distinct_count / row_count, 4)
                    if row_count else 0.0
                ),
                examples=[str(value) for value in examples.get(column, [])],
                minimum=stats.get("min"),
                maximum=stats.get("max"),
                role_candidates=roles,
                confidence=confidence,
                reasoning=reasoning,
            )
        )

    dimension_tables = [
        f"dim_{_normalize_column_name(column)}"
        for column in dimension_candidates + time_candidates
    ]

    grain = (
        f"One row per {key_candidates[0]}."
        if key_candidates
        else "One row per validated source record."
    )

    discovery_reasoning = [
        (
            f"{key_candidates[0]} is a strong row-level key candidate."
            if key_candidates
            else "No reliable unique identifier was detected."
        )
    ]
    if numeric_candidates:
        discovery_reasoning.append(
            f"{len(numeric_candidates)} numeric field(s) can support future measures."
        )
    if dimension_candidates or time_candidates:
        discovery_reasoning.append(
            "Descriptive/time fields suggest a star-schema candidate."
        )

    discovery = PersonalProjectModelDiscovery(
        grain=grain,
        fact_table_candidate=_fact_table_name(dataset_filename),
        dimension_table_candidates=list(dict.fromkeys(dimension_tables)),
        confidence=(
            "high"
            if key_candidates and numeric_candidates
            else "medium"
            if numeric_candidates or dimension_candidates or time_candidates
            else "low"
        ),
        reasoning=discovery_reasoning,
    )

    suggested_questions = []
    first_numeric = numeric_candidates[0] if numeric_candidates else None
    first_dimension = dimension_candidates[0] if dimension_candidates else None
    first_time = time_candidates[0] if time_candidates else None

    if first_numeric and first_time:
        suggested_questions.append(
            f"How does {first_numeric} change over {first_time}?"
        )
    if first_numeric and first_dimension:
        suggested_questions.append(
            f"How does {first_numeric} vary by {first_dimension}?"
        )
    if first_numeric and first_dimension and first_time:
        suggested_questions.append(
            f"How does {first_numeric} change over {first_time} across {first_dimension}?"
        )

    return PersonalProjectAnalysisPlan(
        measure_candidates=numeric_candidates,
        numeric_candidates=numeric_candidates,
        key_candidates=key_candidates,
        dimension_candidates=dimension_candidates,
        time_candidates=time_candidates,
        column_intelligence=column_intelligence,
        model_discovery=discovery,
        suggested_questions=suggested_questions,
        source="local",
    )


def build_personal_analysis_result(
    df: pd.DataFrame,
    measure: str,
    dimension: str | None = None,
) -> PersonalProjectAnalysisResult:

    if measure not in df.columns:
        raise ValueError(
            f"Measure column not found: {measure}"
        )

    if not pd.api.types.is_numeric_dtype(
        df[measure]
    ):
        raise ValueError(
            f"Measure must be numeric: {measure}"
        )

    if (
        dimension is not None
        and dimension not in df.columns
    ):
        raise ValueError(
            f"Dimension column not found: {dimension}"
        )

    measure_series = (
        df[measure]
        .dropna()
    )

    overall = {
        "count": int(
            measure_series.count()
        ),
        "mean": (
            float(measure_series.mean())
            if not measure_series.empty
            else None
        ),
        "min": (
            float(measure_series.min())
            if not measure_series.empty
            else None
        ),
        "max": (
            float(measure_series.max())
            if not measure_series.empty
            else None
        ),
    }

    grouped_results: list[dict] = []

    if dimension is not None:

        grouped = df.groupby(
            dimension,
            dropna=False,
        )[measure]

        for (
            dimension_value,
            group,
        ) in grouped:

            clean_group = (
                group.dropna()
            )

            if pd.isna(
                dimension_value
            ):
                safe_dimension_value = None
            else:
                safe_dimension_value = (
                    dimension_value
                )

            grouped_results.append(
                {
                    "value":
                        safe_dimension_value,

                    "count":
                        int(
                            clean_group.count()
                        ),

                    "mean":
                        (
                            float(
                                clean_group.mean()
                            )
                            if not clean_group.empty
                            else None
                        ),

                    "min":
                        (
                            float(
                                clean_group.min()
                            )
                            if not clean_group.empty
                            else None
                        ),

                    "max":
                        (
                            float(
                                clean_group.max()
                            )
                            if not clean_group.empty
                            else None
                        ),
                }
            )

    return PersonalProjectAnalysisResult(
        measure=measure,
        dimension=dimension,
        overall=overall,
        grouped_results=(
            grouped_results
        ),
        source="local",
    )