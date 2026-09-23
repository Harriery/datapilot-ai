import pytest

from backend.app.models import (
    PersonalProjectAnalysisPlan,
    PersonalProjectDataModelStudio,
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
