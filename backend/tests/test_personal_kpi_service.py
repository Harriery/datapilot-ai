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
        "sum_fact_sales_amount",
        "mean_fact_sales_amount",
        "count_fact_sales_amount",
        "min_fact_sales_amount",
        "max_fact_sales_amount",
        "mean_fact_sales_amount_by_dim_region",
    ]

    grouped = result[-1]

    assert grouped.fact_table == "fact_sales"
    assert grouped.measure == "amount"
    assert grouped.dimension_table == "dim_region"
    assert grouped.dimension == "region"

    assert (
        grouped.formula
        == "MEAN(fact_sales.amount) BY dim_region.region"
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
