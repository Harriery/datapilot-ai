from backend.app.models import (
    PersonalProjectAnalysisPlan,
)

from backend.app.personal_data_model_service import (
    build_personal_data_model_plan,
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