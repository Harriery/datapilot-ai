from backend.app.models import (
    PersonalProjectAnalysisPlan,
    PersonalProjectAnalysisResult,
    PersonalProjectDataModelStudio,
    PersonalProjectDataModelTable,
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



def _measure_aggregation_profile(
    measure_name: str,
) -> tuple[str, ...]:
    """
    Pick a small, conservative aggregation set from
    reusable semantic name patterns.

    Numeric does not automatically mean every aggregation
    is useful. The goal is to avoid noisy KPI suggestions.
    """

    normalized = _normalize_code_part(
        measure_name
    )

    tokens = set(
        normalized.split("_")
    )

    average_first_tokens = {
        "price",
        "rate",
        "ratio",
        "percentage",
        "percent",
        "score",
        "distance",
        "area",
        "size",
        "age",
        "duration",
        "temperature",
        "weight",
        "height",
    }

    additive_tokens = {
        "amount",
        "revenue",
        "income",
        "expense",
        "cost",
        "profit",
        "sales",
        "turnover",
        "balance",
        "quantity",
        "qty",
        "units",
        "volume",
    }

    if tokens & additive_tokens:
        return (
            "sum",
            "mean",
        )

    if tokens & average_first_tokens:
        return (
            "mean",
            "min",
            "max",
        )

    return (
        "mean",
        "min",
        "max",
    )


def _aggregation_label(
    aggregation: str,
) -> str:
    return {
        "sum": "Total",
        "mean": "Average",
        "count": "Count",
        "min": "Minimum",
        "max": "Maximum",
    }[aggregation]


def _measure_priority(
    measure_name: str,
) -> tuple[int, str]:
    normalized = _normalize_code_part(
        measure_name
    )

    tokens = set(
        normalized.split("_")
    )

    primary_tokens = {
        "price",
        "revenue",
        "sales",
        "amount",
        "profit",
        "income",
        "cost",
        "expense",
        "turnover",
    }

    return (
        0
        if tokens & primary_tokens
        else 1,
        normalized,
    )


def _preferred_dimension_column(
    table: PersonalProjectDataModelTable,
) -> str | None:
    """
    Prefer a readable semantic attribute instead of a
    technical key when the model contains one.
    """

    for column in table.columns:
        if (
            column.derivation is not None
            and column.derivation.type
            == "mapping"
        ):
            return column.name

    for column in table.columns:
        if (
            column.derivation is not None
            and column.derivation.type
            == "date_part"
            and column.derivation.operation
            in {
                "year",
                "quarter",
                "month",
                "month_name",
            }
        ):
            return column.name

    for column in table.columns:
        if column.role in {
            "attribute",
            "dimension",
            "time",
        }:
            return column.name

    for column in table.columns:
        if column.role == "key":
            return column.name

    return None


def _dimension_priority(
    table: PersonalProjectDataModelTable,
) -> tuple[int, str]:
    """
    Rank dimensions using model semantics only.

    Mapping labels and date dimensions are especially useful
    for dashboard breakdowns. Composite-key detail dimensions
    are intentionally ranked later.
    """

    has_mapping = any(
        column.derivation is not None
        and column.derivation.type
        == "mapping"
        for column in table.columns
    )

    has_date_part = any(
        column.derivation is not None
        and column.derivation.type
        == "date_part"
        for column in table.columns
    )

    has_composite_key = any(
        column.role == "key"
        and column.derivation
        is not None
        and column.derivation.type
        == "multi_column"
        for column in table.columns
    )

    if has_mapping:
        rank = 0
    elif has_date_part:
        rank = 1
    elif has_composite_key:
        rank = 4
    elif len(table.columns) > 1:
        rank = 2
    else:
        rank = 3

    return (
        rank,
        _normalize_code_part(
            table.name
        ),
    )


def build_personal_kpi_candidates_from_studio(
    studio: PersonalProjectDataModelStudio,
) -> list[PersonalProjectKPIDefinition]:
    """
    Build KPI suggestions from the CURRENT logical model.

    The algorithm is dataset-agnostic:
    - fact tables and measures come from model roles;
    - aggregations use conservative semantic patterns;
    - active relationships provide breakdown dimensions;
    - readable derived labels are preferred;
    - only the primary business measure gets grouped
      suggestions to avoid suggestion explosion.
    """

    tables_by_name = {
        table.name: table
        for table in studio.tables
    }

    candidates: list[
        PersonalProjectKPIDefinition
    ] = []

    for fact_table in studio.tables:
        if fact_table.table_type != "fact":
            continue

        fact_code = _normalize_code_part(
            fact_table.name
        )

        candidates.append(
            PersonalProjectKPIDefinition(
                code=(
                    f"row_count_{fact_code}"
                ),
                title="Record Count",
                fact_table=fact_table.name,
                measure=None,
                aggregation="count",
                dimension_table=None,
                dimension=None,
                filter_value=None,
                formula_mode="row_count",
                formula=(
                    f"COUNT_ROWS("
                    f"{fact_table.name})"
                ),
                description=(
                    "Number of rows at the "
                    f"{fact_table.name} grain."
                ),
                source="local",
            )
        )

        measure_columns = sorted(
            [
                column
                for column in fact_table.columns
                if column.role == "measure"
            ],
            key=lambda column:
                _measure_priority(
                    column.name
                ),
        )

        relationships = [
            relationship
            for relationship
            in studio.relationships
            if (
                relationship.active
                and relationship.from_table
                == fact_table.name
                and relationship.to_table
                in tables_by_name
            )
        ]

        dimension_options: list[
            tuple[
                PersonalProjectDataModelTable,
                str,
            ]
        ] = []

        for relationship in relationships:
            dimension_table = (
                tables_by_name[
                    relationship.to_table
                ]
            )

            preferred_column = (
                _preferred_dimension_column(
                    dimension_table
                )
            )

            if preferred_column is None:
                continue

            dimension_options.append(
                (
                    dimension_table,
                    preferred_column,
                )
            )

        dimension_options.sort(
            key=lambda item:
                _dimension_priority(
                    item[0]
                )
        )

        # Four breakdowns keeps suggestions useful but compact.
        dimension_options = (
            dimension_options[:4]
        )

        for index, column in enumerate(
            measure_columns
        ):
            measure_name = column.name

            aggregations = (
                _measure_aggregation_profile(
                    measure_name
                )
            )

            for aggregation in aggregations:
                label = (
                    _aggregation_label(
                        aggregation
                    )
                )

                code = (
                    f"{aggregation}_"
                    f"{fact_code}_"
                    f"{_normalize_code_part(measure_name)}"
                )

                candidates.append(
                    PersonalProjectKPIDefinition(
                        code=code,
                        title=(
                            f"{label} "
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
                            f"({fact_table.name}."
                            f"{measure_name})"
                        ),
                        description=(
                            f"{label} "
                            f"{measure_name} from "
                            f"{fact_table.name}."
                        ),
                        source="local",
                    )
                )

            # Only the highest-priority business measure gets
            # grouped suggestions. This avoids 30-50 near-
            # duplicate cards on wide datasets.
            if index != 0:
                continue

            primary_aggregation = (
                aggregations[0]
            )

            primary_label = (
                _aggregation_label(
                    primary_aggregation
                )
            )

            for (
                dimension_table,
                dimension_column,
            ) in dimension_options:
                code = (
                    f"{primary_aggregation}_"
                    f"{fact_code}_"
                    f"{_normalize_code_part(measure_name)}"
                    "_by_"
                    f"{_normalize_code_part(dimension_table.name)}"
                    "_"
                    f"{_normalize_code_part(dimension_column)}"
                )

                candidates.append(
                    PersonalProjectKPIDefinition(
                        code=code,
                        title=(
                            f"{primary_label} "
                            f"{measure_name} by "
                            f"{dimension_column}"
                        ),
                        fact_table=(
                            fact_table.name
                        ),
                        measure=measure_name,
                        aggregation=(
                            primary_aggregation
                        ),
                        dimension_table=(
                            dimension_table.name
                        ),
                        dimension=(
                            dimension_column
                        ),
                        filter_value=None,
                        formula_mode=(
                            "safe_aggregation"
                        ),
                        formula=(
                            f"{primary_aggregation.upper()}"
                            f"({fact_table.name}."
                            f"{measure_name}) BY "
                            f"{dimension_table.name}."
                            f"{dimension_column}"
                        ),
                        description=(
                            f"{primary_label} "
                            f"{measure_name} grouped "
                            f"by {dimension_column}."
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
                "row_count",
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

        if (
            definition.formula_mode
            == "row_count"
        ):
            validated.append(
                definition.model_copy(
                    update={
                        "measure": None,
                        "aggregation": "count",
                        "dimension_table": None,
                        "dimension": None,
                        "filter_value": None,
                        "formula": (
                            f"COUNT_ROWS("
                            f"{definition.fact_table})"
                        ),
                    }
                )
            )

            continue

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

            if not definition.dimension:
                raise ValueError(
                    (
                        "KPI dimension column is required "
                        "when dimension_table is selected."
                    )
                )

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

            connected = any(
                relationship.active
                and {
                    relationship.from_table,
                    relationship.to_table,
                }
                == {
                    definition.fact_table,
                    definition.dimension_table,
                }
                for relationship
                in studio.relationships
            )

            if not connected:
                raise ValueError(
                    (
                        "KPI dimension table is not "
                        "actively related to fact table: "
                        f"{definition.dimension_table}"
                    )
                )

        if (
            definition.filter_value
            is not None
            and (
                not definition.dimension_table
                or not definition.dimension
            )
        ):
            raise ValueError(
                (
                    "KPI filter context requires "
                    "a dimension table and column."
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
