import pytest

from backend.app.models import (
    PersonalProjectAnalysisPlan,
    PersonalProjectDataModelColumn,
    PersonalProjectDataModelStudio,
    PersonalProjectDataModelTable,
)

from backend.app.personal_data_model_service import (
    build_personal_data_model_plan,
)

from backend.app.personal_data_model_studio_service import (
    build_personal_data_model_studio,
    validate_personal_data_model_studio,
)


def test_build_personal_data_model_plan():
    analysis_plan = (
        PersonalProjectAnalysisPlan(
            measure_candidates=[
                "age",
            ],
            dimension_candidates=[
                "city",
            ],
            time_candidates=[],
            suggested_questions=[
                "How does age vary by city?",
            ],
            source="local",
        )
    )

    result = (
        build_personal_data_model_plan(
            dataset_filename=(
                "test_quality.csv"
            ),
            analysis_plan=analysis_plan,
        )
    )

    assert (
        result.model_type
        == "star_schema_candidate"
    )
    
    assert (
        result.base_table
        == "fact_test_quality"
    )

    assert (
        result.grain
        == (
            "One row per validated "
            "source record."
        )
    )

    assert (
        result.dimensions
        == ["city"]
    )

    assert (
        result.time_dimension
        is None
    )

    assert [
        measure.code
        for measure in result.measures
    ] == [
        "measure_age",
    ]

    assert (
        result.measures[0].column
        == "age"
    )

    assert (
        result.measures[0].aggregation
        is None
    )

    assert (
        result.recommended_dimension_tables
        == ["dim_city"]
    )

    assert result.source == "local"


def test_data_model_studio_initializes_canvas_positions():
    plan = build_personal_data_model_plan(
        dataset_filename="sales.csv",
        analysis_plan=(
            PersonalProjectAnalysisPlan(
                numeric_candidates=["amount"],
                measure_candidates=["amount"],
                dimension_candidates=["region"],
                source="local",
            )
        ),
    )

    studio = build_personal_data_model_studio(
        data_model_plan=plan
    )

    assert set(
        studio.node_positions
    ) == {
        "fact_sales",
        "dim_region",
    }


def test_data_model_studio_rejects_orphan_canvas_position():
    studio = PersonalProjectDataModelStudio(
        tables=[],
        relationships=[],
        node_positions={
            "missing_table": {
                "x": 10,
                "y": 20,
            }
        },
    )

    with pytest.raises(
        ValueError,
        match="unknown table",
    ):
        validate_personal_data_model_studio(
            studio
        )



def test_data_model_studio_accepts_semantic_date_derivation():
    studio = PersonalProjectDataModelStudio(
        tables=[
            PersonalProjectDataModelTable(
                name="dim_date",
                table_type="dimension",
                columns=[
                    PersonalProjectDataModelColumn(
                        name="Date",
                        source_column="Date",
                        role="key",
                    ),
                    PersonalProjectDataModelColumn(
                        name="Year",
                        source_column="Date",
                        role="attribute",
                        derivation={
                            "type": "date_part",
                            "operation": "year",
                            "source_columns": ["Date"],
                            "parameters": {},
                        },
                    ),
                ],
            )
        ],
        relationships=[],
    )

    result = validate_personal_data_model_studio(
        studio
    )

    derived = result.tables[0].columns[1]
    assert derived.derivation is not None
    assert derived.derivation.type == "date_part"
    assert derived.derivation.operation == "year"


def test_data_model_studio_rejects_unknown_date_derivation():
    studio = PersonalProjectDataModelStudio(
        tables=[
            PersonalProjectDataModelTable(
                name="dim_date",
                table_type="dimension",
                columns=[
                    PersonalProjectDataModelColumn(
                        name="BadDatePart",
                        source_column="Date",
                        role="attribute",
                        derivation={
                            "type": "date_part",
                            "operation": "century",
                            "source_columns": ["Date"],
                            "parameters": {},
                        },
                    ),
                ],
            )
        ],
        relationships=[],
    )

    with pytest.raises(
        ValueError,
        match="Unsupported date-part derivation",
    ):
        validate_personal_data_model_studio(
            studio
        )



def test_data_model_studio_accepts_multi_column_concatenate():
    studio = PersonalProjectDataModelStudio(
        tables=[
            PersonalProjectDataModelTable(
                name="dim_property_location",
                table_type="dimension",
                columns=[
                    PersonalProjectDataModelColumn(
                        name="LocationKey",
                        role="key",
                        derivation={
                            "type": "multi_column",
                            "operation": "concatenate",
                            "source_columns": [
                                "Address",
                                "Suburb",
                            ],
                            "parameters": {
                                "separator": " | ",
                            },
                        },
                    ),
                ],
            )
        ],
        relationships=[],
    )

    result = validate_personal_data_model_studio(
        studio
    )

    derived = result.tables[0].columns[0]
    assert derived.derivation is not None
    assert derived.derivation.type == "multi_column"
    assert (
        derived.derivation.source_columns
        == ["Address", "Suburb"]
    )
    assert (
        derived.derivation.parameters[
            "separator"
        ]
        == " | "
    )


def test_data_model_studio_rejects_multi_column_with_one_source():
    studio = PersonalProjectDataModelStudio(
        tables=[
            PersonalProjectDataModelTable(
                name="dim_property_location",
                table_type="dimension",
                columns=[
                    PersonalProjectDataModelColumn(
                        name="LocationKey",
                        role="key",
                        derivation={
                            "type": "multi_column",
                            "operation": "concatenate",
                            "source_columns": [
                                "Address",
                            ],
                            "parameters": {},
                        },
                    ),
                ],
            )
        ],
        relationships=[],
    )

    with pytest.raises(
        ValueError,
        match="at least two source columns",
    ):
        validate_personal_data_model_studio(
            studio
        )



def test_data_model_studio_accepts_text_derivation():
    studio = PersonalProjectDataModelStudio(
        tables=[
            PersonalProjectDataModelTable(
                name="dim_customer",
                table_type="dimension",
                columns=[
                    PersonalProjectDataModelColumn(
                        name="CleanName",
                        role="attribute",
                        derivation={
                            "type": "text",
                            "operation": "trim",
                            "source_columns": ["Name"],
                            "parameters": {},
                        },
                    ),
                ],
            )
        ],
        relationships=[],
    )

    result = validate_personal_data_model_studio(
        studio
    )

    assert (
        result.tables[0]
        .columns[0]
        .derivation
        .operation
        == "trim"
    )


def test_data_model_studio_accepts_numeric_arithmetic_derivation():
    studio = PersonalProjectDataModelStudio(
        tables=[
            PersonalProjectDataModelTable(
                name="fact_sales",
                table_type="fact",
                columns=[
                    PersonalProjectDataModelColumn(
                        name="Profit",
                        role="measure",
                        derivation={
                            "type": "numeric",
                            "operation": "subtract",
                            "source_columns": [
                                "Revenue",
                                "Cost",
                            ],
                            "parameters": {},
                        },
                    ),
                ],
            )
        ],
        relationships=[],
    )

    result = validate_personal_data_model_studio(
        studio
    )

    assert (
        result.tables[0]
        .columns[0]
        .derivation
        .source_columns
        == ["Revenue", "Cost"]
    )


def test_data_model_studio_accepts_mapping_derivation():
    studio = PersonalProjectDataModelStudio(
        tables=[
            PersonalProjectDataModelTable(
                name="dim_type",
                table_type="dimension",
                columns=[
                    PersonalProjectDataModelColumn(
                        name="TypeLabel",
                        role="attribute",
                        derivation={
                            "type": "mapping",
                            "operation": "map_values",
                            "source_columns": ["Type"],
                            "parameters": {
                                "mapping": (
                                    "h => House\n"
                                    "u => Unit"
                                ),
                            },
                        },
                    ),
                ],
            )
        ],
        relationships=[],
    )

    result = validate_personal_data_model_studio(
        studio
    )

    assert (
        result.tables[0]
        .columns[0]
        .derivation
        .type
        == "mapping"
    )
