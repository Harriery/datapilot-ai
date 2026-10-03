import pytest

from backend.app.models import (
    PersonalProjectAnalysisPlan,
    PersonalProjectAnalysisResult,
    PersonalProjectDataModelColumn,
    PersonalProjectDataModelRelationship,
    PersonalProjectDataModelStudio,
    PersonalProjectDataModelTable,
    PersonalProjectKPIDefinition,
)

from backend.app.personal_kpi_service import (
    build_personal_kpi_candidates,
    build_personal_kpi_candidates_from_plan,
    build_personal_kpi_candidates_from_studio,
    validate_personal_kpi_definitions,
)


def test_build_personal_kpi_candidates_for_age_by_city():
    analysis_result = (
        PersonalProjectAnalysisResult(
            measure="age",
            dimension="city",
            overall={
                "count": 4,
                "mean": 29.5,
                "min": 28.0,
                "max": 31.0,
            },
            grouped_results=[],
            source="local",
        )
    )

    result = build_personal_kpi_candidates(
        analysis_result
    )

    assert len(result) == 5

    codes = [
        item.code
        for item in result
    ]

    assert codes == [
        "average_age",
        "count_age",
        "minimum_age",
        "maximum_age",
        "average_age_by_city",
    ]

    grouped_candidate = result[-1]

    assert (
        grouped_candidate.title
        == "Average age by city"
    )

    assert (
        grouped_candidate.measure
        == "age"
    )

    assert (
        grouped_candidate.aggregation
        == "mean"
    )

    assert (
        grouped_candidate.dimension
        == "city"
    )

    assert (
        grouped_candidate.source
        == "local"
    )


def test_build_personal_kpi_candidates_from_discovery_plan():
    analysis_plan = (
        PersonalProjectAnalysisPlan(
            measure_candidates=[
                "price",
                "surface_area",
            ],
            dimension_candidates=[
                "region",
                "property_type",
            ],
            time_candidates=[
                "sale_date",
            ],
            suggested_questions=[],
            source="local",
        )
    )

    result = (
        build_personal_kpi_candidates_from_plan(
            analysis_plan
        )
    )

    codes = [
        item.code
        for item in result
    ]

    assert codes == [
        "average_price",
        "count_price",
        "minimum_price",
        "maximum_price",
        "average_price_by_region",
        "average_surface_area",
        "count_surface_area",
        "minimum_surface_area",
        "maximum_surface_area",
        "average_surface_area_by_region",
    ]



def _build_test_model_studio():
    return PersonalProjectDataModelStudio(
        tables=[
            PersonalProjectDataModelTable(
                name="fact_sales",
                table_type="fact",
                columns=[
                    PersonalProjectDataModelColumn(
                        name="region_id",
                        source_column="region",
                        role="foreign_key",
                    ),
                    PersonalProjectDataModelColumn(
                        name="amount",
                        source_column="amount",
                        role="measure",
                    ),
                ],
            ),
            PersonalProjectDataModelTable(
                name="dim_region",
                table_type="dimension",
                columns=[
                    PersonalProjectDataModelColumn(
                        name="region",
                        source_column="region",
                        role="key",
                    ),
                ],
            ),
        ],
        relationships=[
            PersonalProjectDataModelRelationship(
                from_table="fact_sales",
                from_column="region_id",
                to_table="dim_region",
                to_column="region",
                cardinality="many_to_one",
                active=True,
            ),
        ],
        source="user",
    )


def test_build_personal_kpi_candidates_from_studio():
    result = (
        build_personal_kpi_candidates_from_studio(
            _build_test_model_studio()
        )
    )

    assert [
        item.code
        for item in result
    ] == [
        "row_count_fact_sales",
        "sum_fact_sales_amount",
        "mean_fact_sales_amount",
        (
            "sum_fact_sales_amount_"
            "by_dim_region_region"
        ),
    ]

    row_count = result[0]

    assert row_count.measure is None
    assert row_count.formula_mode == "row_count"
    assert (
        row_count.formula
        == "COUNT_ROWS(fact_sales)"
    )

    grouped = result[-1]

    assert grouped.fact_table == "fact_sales"
    assert grouped.measure == "amount"
    assert grouped.dimension_table == "dim_region"
    assert grouped.dimension == "region"

    assert (
        grouped.formula
        == "SUM(fact_sales.amount) BY dim_region.region"
    )


def test_validate_personal_kpi_definitions_builds_safe_formula():
    definitions = (
        validate_personal_kpi_definitions(
            studio=_build_test_model_studio(),
            definitions=[
                PersonalProjectKPIDefinition(
                    code="revenue_by_region",
                    title="Revenue by region",
                    fact_table="fact_sales",
                    measure="amount",
                    aggregation="sum",
                    dimension_table="dim_region",
                    dimension="region",
                    filter_value="West",
                    formula_mode="safe_aggregation",
                    formula=None,
                    description="Revenue grouped by region.",
                    source="user",
                ),
            ],
        )
    )

    assert len(definitions) == 1

    assert (
        definitions[0].formula
        == (
            "SUM(fact_sales.amount) "
            "BY dim_region.region "
            "FILTER=West"
        )
    )


def test_validate_personal_kpi_definitions_rejects_non_measure_column():
    with pytest.raises(
        ValueError,
        match="measure role",
    ):
        validate_personal_kpi_definitions(
            studio=_build_test_model_studio(),
            definitions=[
                PersonalProjectKPIDefinition(
                    code="invalid",
                    title="Invalid KPI",
                    fact_table="fact_sales",
                    measure="region_id",
                    aggregation="count",
                    description="Invalid.",
                    source="user",
                ),
            ],
        )



def test_validate_personal_kpi_definitions_supports_row_count():
    definitions = (
        validate_personal_kpi_definitions(
            studio=_build_test_model_studio(),
            definitions=[
                PersonalProjectKPIDefinition(
                    code="record_count",
                    title="Record Count",
                    fact_table="fact_sales",
                    measure=None,
                    aggregation="count",
                    dimension_table=None,
                    dimension=None,
                    filter_value=None,
                    formula_mode="row_count",
                    formula=None,
                    description="Rows in the fact table.",
                    source="user",
                ),
            ],
        )
    )

    assert len(definitions) == 1
    assert definitions[0].measure is None

    assert (
        definitions[0].formula
        == "COUNT_ROWS(fact_sales)"
    )


def test_kpi_suggestions_prefer_natural_key_over_secondary_attribute():
    studio = PersonalProjectDataModelStudio(
        tables=[
            PersonalProjectDataModelTable(
                name="fact_orders",
                table_type="fact",
                columns=[
                    PersonalProjectDataModelColumn(
                        name="region_id",
                        source_column="region",
                        role="foreign_key",
                    ),
                    PersonalProjectDataModelColumn(
                        name="price",
                        source_column="price",
                        role="measure",
                    ),
                ],
            ),
            PersonalProjectDataModelTable(
                name="dim_region",
                table_type="dimension",
                columns=[
                    PersonalProjectDataModelColumn(
                        name="region",
                        source_column="region",
                        role="key",
                    ),
                    PersonalProjectDataModelColumn(
                        name="region_code",
                        source_column="region_code",
                        role="attribute",
                    ),
                ],
            ),
        ],
        relationships=[
            PersonalProjectDataModelRelationship(
                from_table="fact_orders",
                from_column="region_id",
                to_table="dim_region",
                to_column="region",
                cardinality="many_to_one",
                active=True,
            ),
        ],
        source="user",
    )

    result = build_personal_kpi_candidates_from_studio(
        studio
    )

    grouped = [
        item
        for item in result
        if item.dimension_table == "dim_region"
    ]

    assert len(grouped) == 1
    assert grouped[0].aggregation == "mean"
    assert grouped[0].dimension == "region"
    assert (
        grouped[0].title
        == "Average price by region"
    )


def test_secondary_measures_only_get_primary_aggregation_suggestion():
    studio = PersonalProjectDataModelStudio(
        tables=[
            PersonalProjectDataModelTable(
                name="fact_metrics",
                table_type="fact",
                columns=[
                    PersonalProjectDataModelColumn(
                        name="price",
                        source_column="price",
                        role="measure",
                    ),
                    PersonalProjectDataModelColumn(
                        name="distance",
                        source_column="distance",
                        role="measure",
                    ),
                ],
            ),
        ],
        relationships=[],
        source="user",
    )

    result = build_personal_kpi_candidates_from_studio(
        studio
    )

    distance_items = [
        item
        for item in result
        if item.measure == "distance"
    ]

    assert [
        item.aggregation
        for item in distance_items
    ] == ["mean"]


def test_validate_personal_kpi_definitions_supports_custom_formula():
    definitions = validate_personal_kpi_definitions(
        studio=_build_test_model_studio(),
        definitions=[
            PersonalProjectKPIDefinition(
                code="custom_margin",
                title="Custom margin",
                fact_table="fact_sales",
                measure=None,
                aggregation=None,
                dimension_table=None,
                dimension=None,
                filter_value=None,
                formula_mode="custom",
                formula=(
                    "SAFE_DIVIDE("
                    "SUM(fact_sales.amount), "
                    "COUNT_ROWS(fact_sales))"
                ),
                description="Custom semantic KPI.",
                source="user",
            ),
        ],
    )

    assert len(definitions) == 1
    assert definitions[0].formula_mode == "custom"
    assert definitions[0].measure is None
    assert definitions[0].aggregation is None
    assert (
        definitions[0].formula
        == (
            "SAFE_DIVIDE("
            "SUM(fact_sales.amount), "
            "COUNT_ROWS(fact_sales))"
        )
    )


def test_validate_personal_kpi_definitions_rejects_empty_custom_formula():
    with pytest.raises(
        ValueError,
        match="Custom KPI formula is required",
    ):
        validate_personal_kpi_definitions(
            studio=_build_test_model_studio(),
            definitions=[
                PersonalProjectKPIDefinition(
                    code="empty_custom",
                    title="Empty custom",
                    fact_table="fact_sales",
                    measure=None,
                    aggregation=None,
                    formula_mode="custom",
                    formula="   ",
                    description="Invalid custom KPI.",
                    source="user",
                ),
            ],
        )


def test_custom_kpi_formula_rejects_unknown_function():
    with pytest.raises(
        ValueError,
        match="Unsupported custom KPI function",
    ):
        validate_personal_kpi_definitions(
            studio=_build_test_model_studio(),
            definitions=[
                PersonalProjectKPIDefinition(
                    code="bad_function",
                    title="Bad function",
                    fact_table="fact_sales",
                    measure=None,
                    aggregation=None,
                    formula_mode="custom",
                    formula=(
                        "MEDIAN("
                        "fact_sales.amount)"
                    ),
                    description="Invalid custom KPI.",
                    source="user",
                ),
            ],
        )


def test_custom_kpi_formula_rejects_unknown_column():
    with pytest.raises(
        ValueError,
        match="unknown column",
    ):
        validate_personal_kpi_definitions(
            studio=_build_test_model_studio(),
            definitions=[
                PersonalProjectKPIDefinition(
                    code="bad_column",
                    title="Bad column",
                    fact_table="fact_sales",
                    measure=None,
                    aggregation=None,
                    formula_mode="custom",
                    formula=(
                        "SUM("
                        "fact_sales.missing_amount)"
                    ),
                    description="Invalid custom KPI.",
                    source="user",
                ),
            ],
        )


def test_custom_kpi_formula_rejects_unknown_table():
    with pytest.raises(
        ValueError,
        match="unknown table",
    ):
        validate_personal_kpi_definitions(
            studio=_build_test_model_studio(),
            definitions=[
                PersonalProjectKPIDefinition(
                    code="bad_table",
                    title="Bad table",
                    fact_table="fact_sales",
                    measure=None,
                    aggregation=None,
                    formula_mode="custom",
                    formula=(
                        "COUNT_ROWS("
                        "fact_missing)"
                    ),
                    description="Invalid custom KPI.",
                    source="user",
                ),
            ],
        )


def test_custom_kpi_formula_supports_nested_safe_divide():
    definitions = validate_personal_kpi_definitions(
        studio=_build_test_model_studio(),
        definitions=[
            PersonalProjectKPIDefinition(
                code="average_amount",
                title="Average amount",
                fact_table="fact_sales",
                measure=None,
                aggregation=None,
                formula_mode="custom",
                formula=(
                    "SAFE_DIVIDE("
                    "SUM(fact_sales.amount),"
                    "COUNT(fact_sales.amount)"
                    ")"
                ),
                description="Custom semantic KPI.",
                source="user",
            ),
        ],
    )

    assert (
        definitions[0].formula
        == (
            "SAFE_DIVIDE("
            "SUM(fact_sales.amount),"
            "COUNT(fact_sales.amount)"
            ")"
        )
    )
