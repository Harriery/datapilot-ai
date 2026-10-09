import pandas as pd
import pytest

from backend.app.workspace_preview_filter_service import (
    apply_preview_filters,
    parse_preview_filters,
    preview_column_types,
)


def make_df():
    return pd.DataFrame(
        {
            "city": [
                "Den Haag",
                "Rotterdam",
                "Delft",
                None,
            ],
            "value": [
                10,
                20,
                30,
                40,
            ],
            "date": [
                "2026-01-01",
                "2026-02-01",
                "2026-03-01",
                "2026-04-01",
            ],
            "category": [
                "A",
                "A",
                "B",
                "C",
            ],
        }
    )


def test_preview_column_types_infers_number_text_and_date():
    types = preview_column_types(
        make_df()
    )

    assert types["city"] == "text"
    assert types["value"] == "number"
    assert types["date"] == "datetime"


def test_preview_filter_is_missing():
    result = apply_preview_filters(
        df=make_df(),
        filters=[
            {
                "column": "city",
                "operator": "is_missing",
                "value": None,
                "value_to": None,
            }
        ],
    )

    assert len(result) == 1
    assert result.iloc[0]["value"] == 40


def test_preview_filter_numeric_between():
    result = apply_preview_filters(
        df=make_df(),
        filters=[
            {
                "column": "value",
                "operator": "between",
                "value": "15",
                "value_to": "35",
            }
        ],
    )

    assert result["value"].tolist() == [
        20,
        30,
    ]


def test_preview_filter_text_contains():
    result = apply_preview_filters(
        df=make_df(),
        filters=[
            {
                "column": "city",
                "operator": "contains",
                "value": "dam",
                "value_to": None,
            }
        ],
    )

    assert result["city"].tolist() == [
        "Rotterdam",
    ]


def test_preview_filters_support_and_or_logic():
    filters = [
        {
            "column": "category",
            "operator": "equals",
            "value": "A",
            "value_to": None,
        },
        {
            "column": "value",
            "operator": "greater_than",
            "value": "15",
            "value_to": None,
        },
    ]

    and_result = apply_preview_filters(
        df=make_df(),
        filters=filters,
        logic="and",
    )
    or_result = apply_preview_filters(
        df=make_df(),
        filters=filters,
        logic="or",
    )

    assert and_result["value"].tolist() == [
        20,
    ]
    assert or_result["value"].tolist() == [
        10,
        20,
        30,
        40,
    ]


def test_preview_filters_do_not_mutate_source_dataframe():
    df = make_df()
    original = df.copy(
        deep=True
    )

    apply_preview_filters(
        df=df,
        filters=[
            {
                "column": "city",
                "operator": "is_not_missing",
                "value": None,
                "value_to": None,
            }
        ],
    )

    pd.testing.assert_frame_equal(
        df,
        original,
    )


def test_parse_preview_filters_rejects_unknown_operator():
    with pytest.raises(
        ValueError,
        match="Unsupported preview filter operator",
    ):
        parse_preview_filters(
            '[{"column":"city","operator":"explode"}]'
        )
