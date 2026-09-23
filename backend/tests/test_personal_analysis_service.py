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
        result.numeric_candidates
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


def test_analysis_plan_builds_model_discovery():
    profile = {
        "row_count": 3,
        "columns": [
            "property_id",
            "region",
            "sale_date",
            "price",
        ],
        "data_types": {
            "property_id": "int64",
            "region": "object",
            "sale_date": "object",
            "price": "float64",
        },
        "null_counts": {
            "property_id": 0,
            "region": 0,
            "sale_date": 0,
            "price": 0,
        },
        "distinct_counts": {
            "property_id": 3,
            "region": 2,
            "sale_date": 3,
            "price": 3,
        },
        "column_examples": {
            "property_id": ["1", "2", "3"],
            "region": ["West", "East"],
            "sale_date": ["2026-01-01", "2026-01-02"],
            "price": ["350000", "420000"],
        },
        "numeric_columns": [
            "property_id",
            "price",
        ],
        "numeric_summary": {
            "property_id": {
                "count": 3,
                "mean": 2.0,
                "min": 1.0,
                "max": 3.0,
            },
            "price": {
                "count": 3,
                "mean": 390000.0,
                "min": 350000.0,
                "max": 420000.0,
            },
        },
    }

    result = build_personal_analysis_plan(
        profile,
        dataset_filename="housing.csv",
    )

    assert result.key_candidates == ["property_id"]
    assert result.numeric_candidates == ["price"]
    assert result.dimension_candidates == ["region"]
    assert result.time_candidates == ["sale_date"]

    assert result.model_discovery is not None
    assert result.model_discovery.grain == "One row per property_id."
    assert result.model_discovery.fact_table_candidate == "fact_housing"
    assert result.model_discovery.dimension_table_candidates == [
        "dim_region",
        "dim_sale_date",
    ]

    intelligence = {
        item.name: item
        for item in result.column_intelligence
    }

    assert intelligence["property_id"].role_candidates == ["key"]
    assert intelligence["price"].role_candidates == ["numeric"]
    assert intelligence["price"].minimum == 350000.0
    assert intelligence["region"].distinct_count == 2
