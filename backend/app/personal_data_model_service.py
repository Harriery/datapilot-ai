from pathlib import Path

from backend.app.models import (
    PersonalProjectAnalysisPlan,
    PersonalProjectKPIDefinition,
    PersonalProjectDataModelMeasure,
    PersonalProjectDataModelPlan,
)


def _normalize_name(
    value: str,
) -> str:
    return (
        value
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def _build_base_table_name(
    dataset_filename: str | None,
) -> str:

    if not dataset_filename:
        return "fact_dataset"

    stem = Path(
        dataset_filename
    ).stem

    normalized = _normalize_name(
        stem
    )

    return f"fact_{normalized}"


def build_personal_data_model_plan(
    dataset_filename: str | None,
    analysis_plan: PersonalProjectAnalysisPlan,
) -> PersonalProjectDataModelPlan:

    dimensions = list(
        dict.fromkeys(
            analysis_plan.dimension_candidates
        )
    )

    measures: list[
        PersonalProjectDataModelMeasure
    ] = []

    numeric_candidates = (
        analysis_plan.numeric_candidates
        or analysis_plan.measure_candidates
    )

    for measure in (
        numeric_candidates
    ):
        normalized = _normalize_name(
            measure
        )

        measures.append(
            PersonalProjectDataModelMeasure(
                code=f"measure_{normalized}",
                title=measure,
                column=measure,
                aggregation=None,
                dimension=None,
            )
        )

    time_dimension = (
        analysis_plan.time_candidates[0]
        if analysis_plan.time_candidates
        else None
    )

    recommended_dimension_tables = [
        f"dim_{_normalize_name(dimension)}"
        for dimension in dimensions
    ]

    discovery = analysis_plan.model_discovery

    if (
        discovery is not None
        and discovery.dimension_table_candidates
    ):
        recommended_dimension_tables = list(
            dict.fromkeys(
                discovery.dimension_table_candidates
            )
        )

    if time_dimension is not None:
        time_table = (
            f"dim_{_normalize_name(time_dimension)}"
        )

        if (
            time_table
            not in recommended_dimension_tables
        ):
            recommended_dimension_tables.append(
                time_table
            )

    model_type = (
        "star_schema_candidate"
        if (
            dimensions
            or time_dimension is not None
        )
        else "single_table"
    )

    return PersonalProjectDataModelPlan(
        model_type=model_type,

        base_table=(
            discovery.fact_table_candidate
            if discovery is not None
            else _build_base_table_name(dataset_filename)
        ),

        grain=(
            discovery.grain
            if discovery is not None
            else "One row per validated source record."
        ),

        dimensions=dimensions,

        time_dimension=time_dimension,

        measures=measures,

        recommended_dimension_tables=(
            recommended_dimension_tables
        ),

        source="local",
    )
