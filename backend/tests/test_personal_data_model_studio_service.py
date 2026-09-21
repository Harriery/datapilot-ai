from backend.app.models import (
    PersonalProjectDataModelMeasure,
    PersonalProjectDataModelPlan,
)

from backend.app.personal_data_model_studio_service import (
    build_personal_data_model_studio,
)


def test_build_personal_data_model_studio():
    plan = PersonalProjectDataModelPlan(
        model_type="star_schema_candidate",
        base_table="fact_test_quality",
        grain="One row per validated source record.",
        dimensions=[
            "city",
        ],
        time_dimension=None,
        measures=[
            PersonalProjectDataModelMeasure(
                code="average_age",
                title="Average age",
                column="age",
                aggregation="mean",
                dimension=None,
            ),
            PersonalProjectDataModelMeasure(
                code="average_age_by_city",
                title="Average age by city",
                column="age",
                aggregation="mean",
                dimension="city",
            ),
        ],
        recommended_dimension_tables=[
            "dim_city",
        ],
        source="local",
    )

    studio = (
        build_personal_data_model_studio(
            data_model_plan=plan,
        )
    )

    assert studio.source == "local"

    assert len(studio.tables) == 2

    fact_table = studio.tables[0]

    assert (
        fact_table.name
        == "fact_test_quality"
    )

    assert fact_table.table_type == "fact"

    assert [
        column.name
        for column in fact_table.columns
    ] == [
        "city",
        "age",
    ]

    assert [
        column.role
        for column in fact_table.columns
    ] == [
        "foreign_key",
        "measure",
    ]

    dimension_table = studio.tables[1]

    assert (
        dimension_table.name
        == "dim_city"
    )

    assert (
        dimension_table.table_type
        == "dimension"
    )

    assert len(
        dimension_table.columns
    ) == 1

    assert (
        dimension_table.columns[0].name
        == "city"
    )

    assert (
        dimension_table.columns[0].role
        == "key"
    )

    assert len(
        studio.relationships
    ) == 1

    relationship = (
        studio.relationships[0]
    )

    assert (
        relationship.from_table
        == "fact_test_quality"
    )

    assert (
        relationship.from_column
        == "city"
    )

    assert (
        relationship.to_table
        == "dim_city"
    )

    assert (
        relationship.to_column
        == "city"
    )

    assert (
        relationship.cardinality
        == "many_to_one"
    )

    assert relationship.active is True