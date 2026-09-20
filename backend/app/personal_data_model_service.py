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
    kpi_definitions: list[
        PersonalProjectKPIDefinition
    ],
) -> PersonalProjectDataModelPlan:

    dimensions: list[str] = []

    measures: list[
        PersonalProjectDataModelMeasure
    ] = []

    for kpi in kpi_definitions:

        if (
            kpi.dimension
            and kpi.dimension
            not in dimensions
        ):
            dimensions.append(
                kpi.dimension
            )

        measures.append(
            PersonalProjectDataModelMeasure(
                code=kpi.code,
                title=kpi.title,
                column=kpi.measure,
                aggregation=kpi.aggregation,
                dimension=kpi.dimension,
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
            _build_base_table_name(
                dataset_filename
            )
        ),

        grain=(
            "One row per validated source record."
        ),

        dimensions=dimensions,

        time_dimension=time_dimension,

        measures=measures,

        recommended_dimension_tables=(
            recommended_dimension_tables
        ),

        source="local",
    )