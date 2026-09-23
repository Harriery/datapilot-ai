from backend.app.models import (
    PersonalProjectAnalysisPlan,
    PersonalProjectAnalysisResult,
    PersonalProjectDataModelStudio,
    PersonalProjectKPIDefinition,
)


def _normalize_code_part(
    value: str,
) -> str:
    return (
        value
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def _build_candidates_for_measure(
    measure: str,
    dimension: str | None = None,
) -> list[PersonalProjectKPIDefinition]:

    measure_code = _normalize_code_part(
        measure
    )

    candidates: list[
        PersonalProjectKPIDefinition
    ] = [
        PersonalProjectKPIDefinition(
            code=f"average_{measure_code}",
            title=f"Average {measure}",
            measure=measure,
            aggregation="mean",
            dimension=None,
            description=(
                f"Average value of {measure} "
                "across the validated dataset."
            ),
            source="local",
        ),
        PersonalProjectKPIDefinition(
            code=f"count_{measure_code}",
            title=f"Count of {measure}",
            measure=measure,
            aggregation="count",
            dimension=None,
            description=(
                f"Number of non-missing "
                f"{measure} values."
            ),
            source="local",
        ),
        PersonalProjectKPIDefinition(
            code=f"minimum_{measure_code}",
            title=f"Minimum {measure}",
            measure=measure,
            aggregation="min",
            dimension=None,
            description=(
                f"Minimum observed value "
                f"of {measure}."
            ),
            source="local",
        ),
        PersonalProjectKPIDefinition(
            code=f"maximum_{measure_code}",
            title=f"Maximum {measure}",
            measure=measure,
            aggregation="max",
            dimension=None,
            description=(
                f"Maximum observed value "
                f"of {measure}."
            ),
            source="local",
        ),
    ]

    if dimension is not None:
        dimension_code = _normalize_code_part(
            dimension
        )

        candidates.append(
            PersonalProjectKPIDefinition(
                code=(
                    f"average_{measure_code}"
                    f"_by_{dimension_code}"
                ),
                title=(
                    f"Average {measure} "
                    f"by {dimension}"
                ),
                measure=measure,
                aggregation="mean",
                dimension=dimension,
                description=(
                    f"Compare average {measure} "
                    f"across {dimension} groups."
                ),
                source="local",
            )
        )

    return candidates


def build_personal_kpi_candidates_from_plan(
    analysis_plan: PersonalProjectAnalysisPlan,
) -> list[PersonalProjectKPIDefinition]:
    """
    Build deterministic KPI suggestions from validated
    dataset discovery metadata.

    The KPI stage therefore no longer depends on running
    Analysis first. The first discovered dimension is used
    as a lightweight grouped suggestion until the dedicated
    KPI Builder is implemented.
    """

    first_dimension = (
        analysis_plan.dimension_candidates[0]
        if analysis_plan.dimension_candidates
        else None
    )

    candidates_by_code: dict[
        str,
        PersonalProjectKPIDefinition,
    ] = {}

    numeric_candidates = (
        analysis_plan.numeric_candidates
        or analysis_plan.measure_candidates
    )

    for measure in numeric_candidates:
        for candidate in _build_candidates_for_measure(
            measure=measure,
            dimension=first_dimension,
        ):
            candidates_by_code[
                candidate.code
            ] = candidate

    return list(
        candidates_by_code.values()
    )


def build_personal_kpi_candidates(
    analysis_result: PersonalProjectAnalysisResult,
) -> list[PersonalProjectKPIDefinition]:
    """
    Backward-compatible helper for callers that already
    have an analysis result.
    """

    return _build_candidates_for_measure(
        measure=analysis_result.measure,
        dimension=analysis_result.dimension,
    )



def build_personal_kpi_candidates_from_studio(
    studio: PersonalProjectDataModelStudio,
) -> list[PersonalProjectKPIDefinition]:
    fact_tables = [
        table
        for table in studio.tables
        if table.table_type == "fact"
    ]

    candidates: list[
        PersonalProjectKPIDefinition
    ] = []

    for fact_table in fact_tables:
        measure_columns = [
            column
            for column in fact_table.columns
            if column.role == "measure"
        ]

        dimension_relationships = [
            relationship
            for relationship in studio.relationships
            if (
                relationship.active
                and relationship.from_table
                == fact_table.name
            )
        ]

        first_dimension = (
            dimension_relationships[0]
            if dimension_relationships
            else None
        )

        for column in measure_columns:
            measure_name = column.name

            for aggregation in (
                "sum",
                "mean",
                "count",
                "min",
                "max",
            ):
                aggregation_label = {
                    "sum": "Total",
                    "mean": "Average",
                    "count": "Count",
                    "min": "Minimum",
                    "max": "Maximum",
                }[
                    aggregation
                ]

                code = (
                    f"{aggregation}_{_normalize_code_part(fact_table.name)}_"
                    f"{_normalize_code_part(measure_name)}"
                )

                candidates.append(
                    PersonalProjectKPIDefinition(
                        code=code,
                        title=(
                            f"{aggregation_label} "
                            f"{measure_name}"
                        ),
                        fact_table=(
                            fact_table.name
                        ),
                        measure=measure_name,
                        aggregation=aggregation,
                        dimension_table=None,
                        dimension=None,
                        filter_value=None,
                        formula_mode=(
                            "safe_aggregation"
                        ),
                        formula=(
                            f"{aggregation.upper()}"
                            f"({fact_table.name}.{measure_name})"
                        ),
                        description=(
                            f"{aggregation_label} of "
                            f"{measure_name} from "
                            f"{fact_table.name}."
                        ),
                        source="local",
                    )
                )

            if first_dimension is not None:
                code = (
                    f"mean_{_normalize_code_part(fact_table.name)}_"
                    f"{_normalize_code_part(measure_name)}"
                    f"_by_{_normalize_code_part(first_dimension.to_table)}"
                )

                candidates.append(
                    PersonalProjectKPIDefinition(
                        code=code,
                        title=(
                            f"Average {measure_name} "
                            f"by {first_dimension.to_table}"
                        ),
                        fact_table=(
                            fact_table.name
                        ),
                        measure=measure_name,
                        aggregation="mean",
                        dimension_table=(
                            first_dimension.to_table
                        ),
                        dimension=(
                            first_dimension.to_column
                        ),
                        filter_value=None,
                        formula_mode=(
                            "safe_aggregation"
                        ),
                        formula=(
                            f"MEAN({fact_table.name}.{measure_name}) "
                            f"BY {first_dimension.to_table}."
                            f"{first_dimension.to_column}"
                        ),
                        description=(
                            f"Average {measure_name} grouped by "
                            f"{first_dimension.to_table}."
                        ),
                        source="local",
                    )
                )

    return candidates


def validate_personal_kpi_definitions(
    studio: PersonalProjectDataModelStudio,
    definitions: list[
        PersonalProjectKPIDefinition
    ],
) -> list[
    PersonalProjectKPIDefinition
]:
    tables_by_name = {
        table.name: table
        for table in studio.tables
    }

    seen_codes: set[str] = set()

    validated: list[
        PersonalProjectKPIDefinition
    ] = []

    for definition in definitions:
        if definition.code in seen_codes:
            raise ValueError(
                f"Duplicate KPI code: {definition.code}"
            )

        seen_codes.add(
            definition.code
        )

        if (
            definition.formula_mode
            not in {
                None,
                "safe_aggregation",
            }
        ):
            raise ValueError(
                "Unsupported KPI formula mode."
            )

        if not definition.fact_table:
            raise ValueError(
                "KPI fact_table is required."
            )

        fact_table = tables_by_name.get(
            definition.fact_table
        )

        if (
            fact_table is None
            or fact_table.table_type
            != "fact"
        ):
            raise ValueError(
                (
                    "KPI fact table not found: "
                    f"{definition.fact_table}"
                )
            )

        if not definition.measure:
            raise ValueError(
                "KPI measure column is required."
            )

        measure_column = next(
            (
                column
                for column in fact_table.columns
                if column.name
                == definition.measure
            ),
            None,
        )

        if (
            measure_column is None
            or measure_column.role
            != "measure"
        ):
            raise ValueError(
                (
                    "KPI measure column must use "
                    "measure role in the fact table: "
                    f"{definition.measure}"
                )
            )

        if definition.aggregation is None:
            raise ValueError(
                "KPI aggregation is required."
            )

        if definition.dimension_table:
            dimension_table = (
                tables_by_name.get(
                    definition.dimension_table
                )
            )

            if dimension_table is None:
                raise ValueError(
                    (
                        "KPI dimension table not found: "
                        f"{definition.dimension_table}"
                    )
                )

            if definition.dimension:
                if not any(
                    column.name
                    == definition.dimension
                    for column
                    in dimension_table.columns
                ):
                    raise ValueError(
                        (
                            "KPI dimension column not found: "
                            f"{definition.dimension}"
                        )
                    )

        formula = (
            f"{definition.aggregation.upper()}"
            f"({definition.fact_table}.{definition.measure})"
        )

        if (
            definition.dimension_table
            and definition.dimension
        ):
            formula += (
                f" BY {definition.dimension_table}."
                f"{definition.dimension}"
            )

        if definition.filter_value is not None:
            formula += (
                f" FILTER={definition.filter_value}"
            )

        validated.append(
            definition.model_copy(
                update={
                    "formula_mode":
                        "safe_aggregation",
                    "formula":
                        formula,
                }
            )
        )

    return validated
