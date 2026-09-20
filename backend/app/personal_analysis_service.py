from backend.app.models import (
    PersonalProjectAnalysisPlan,
)

import pandas as pd

from backend.app.models import (
    PersonalProjectAnalysisPlan,
    PersonalProjectAnalysisResult,
)

TIME_COLUMN_NAMES = {
    "year",
    "date",
    "datetime",
    "timestamp",
    "month",
    "quarter",
    "week",
    "day",
}

IDENTIFIER_COLUMN_NAMES = {
    "id",
    "uuid",
    "identifier",
}

ENTITY_IDENTITY_COLUMN_NAMES = {
    "name",
    "first_name",
    "last_name",
    "full_name",
    "email",
    "phone",
    "telephone",
}

def _is_entity_identity_column(
    column: str,
) -> bool:
    normalized = _normalize_column_name(
        column
    )

    return normalized in (
        ENTITY_IDENTITY_COLUMN_NAMES
    )

def _normalize_column_name(
    column: str,
) -> str:
    return (
        column
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def _is_time_column(
    column: str,
) -> bool:
    normalized = _normalize_column_name(
        column
    )

    if normalized in TIME_COLUMN_NAMES:
        return True

    return any(
        normalized.endswith(
            f"_{name}"
        )
        for name in TIME_COLUMN_NAMES
    )


def _is_identifier_column(
    column: str,
) -> bool:
    normalized = _normalize_column_name(
        column
    )

    if normalized in IDENTIFIER_COLUMN_NAMES:
        return True

    return normalized.endswith("_id")


def build_personal_analysis_plan(
    profile: dict,
) -> PersonalProjectAnalysisPlan:

    columns = profile.get(
        "columns",
        [],
    )

    numeric_columns = set(
        profile.get(
            "numeric_columns",
            [],
        )
    )

    time_candidates: list[str] = []
    measure_candidates: list[str] = []
    dimension_candidates: list[str] = []

    # ----------------------------------------------
    # TIME CANDIDATES
    # ----------------------------------------------

    for column in columns:

        if _is_time_column(column):
            time_candidates.append(
                column
            )

    # ----------------------------------------------
    # MEASURE CANDIDATES
    # ----------------------------------------------

    for column in columns:

        if column not in numeric_columns:
            continue

        if column in time_candidates:
            continue

        if _is_identifier_column(
            column
        ):
            continue

        measure_candidates.append(
            column
        )

    # ----------------------------------------------
    # DIMENSION CANDIDATES
    # ----------------------------------------------

    for column in columns:

        if column in measure_candidates:
            continue

        if column in time_candidates:
            continue

        if _is_identifier_column(
            column
        ):
            continue
        if _is_entity_identity_column(
            column
        ):
            continue

        dimension_candidates.append(
            column
        )

    # ----------------------------------------------
    # SUGGESTED QUESTIONS
    # ----------------------------------------------

    suggested_questions: list[str] = []

    first_measure = (
        measure_candidates[0]
        if measure_candidates
        else None
    )

    first_dimension = (
        dimension_candidates[0]
        if dimension_candidates
        else None
    )

    first_time = (
        time_candidates[0]
        if time_candidates
        else None
    )

    if (
        first_measure
        and first_time
    ):
        suggested_questions.append(
            (
                f"How does {first_measure} "
                f"change over {first_time}?"
            )
        )

    if (
        first_measure
        and first_dimension
    ):
        suggested_questions.append(
            (
                f"How does {first_measure} "
                f"vary by {first_dimension}?"
            )
        )

    if (
        first_measure
        and first_dimension
        and first_time
    ):
        suggested_questions.append(
            (
                f"How does {first_measure} "
                f"change over {first_time} "
                f"across {first_dimension}?"
            )
        )

    return PersonalProjectAnalysisPlan(
        measure_candidates=(
            measure_candidates
        ),
        dimension_candidates=(
            dimension_candidates
        ),
        time_candidates=(
            time_candidates
        ),
        suggested_questions=(
            suggested_questions
        ),
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