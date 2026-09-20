import pandas as pd
from backend.app.personal_analysis_service import (
    build_personal_analysis_plan,
    build_personal_analysis_result,
)


def test_build_personal_analysis_plan_for_housing_data():
    profile = {
        "columns": [
            "region",
            "year",
            "price",
        ],
        "numeric_columns": [
            "year",
            "price",
        ],
    }

    result = build_personal_analysis_plan(
        profile
    )

    assert (
        result.measure_candidates
        == ["price"]
    )

    assert (
        result.dimension_candidates
        == ["region"]
    )

    assert (
        result.time_candidates
        == ["year"]
    )

    assert (
        result.suggested_questions
        == [
            "How does price change over year?",
            "How does price vary by region?",
            (
                "How does price change over year "
                "across region?"
            ),
        ]
    )

    assert result.source == "local"

def test_analysis_plan_skips_identity_columns():
    profile = {
        "columns": [
            "customer_id",
            "name",
            "age",
            "city",
        ],
        "numeric_columns": [
            "customer_id",
            "age",
        ],
    }

    result = build_personal_analysis_plan(
        profile
    )

    assert (
        result.measure_candidates
        == ["age"]
    )

    assert (
        result.dimension_candidates
        == ["city"]
    )

    assert (
        result.time_candidates
        == []
    )

    assert (
        result.suggested_questions
        == [
            "How does age vary by city?",
        ]
    )

def test_build_personal_analysis_result_by_city():
    df = pd.DataFrame(
        {
            "age": [
                31.0,
                29.5,
                28.0,
                29.5,
            ],
            "city": [
                "Den Haag",
                "Rotterdam",
                "Utrecht",
                "Delft",
            ],
        }
    )

    result = (
        build_personal_analysis_result(
            df=df,
            measure="age",
            dimension="city",
        )
    )

    assert result.measure == "age"

    assert result.dimension == "city"

    assert result.overall == {
        "count": 4,
        "mean": 29.5,
        "min": 28.0,
        "max": 31.0,
    }

    assert len(
        result.grouped_results
    ) == 4

    assert result.source == "local"