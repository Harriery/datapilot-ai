from __future__ import annotations

import json
from typing import Any, Literal

import pandas as pd
from pandas.api.types import (
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
)


SUPPORTED_FILTER_OPERATORS = {
    "is_missing",
    "is_not_missing",
    "is_blank",
    "is_not_blank",
    "equals",
    "not_equals",
    "contains",
    "not_contains",
    "starts_with",
    "ends_with",
    "greater_than",
    "greater_than_or_equal",
    "less_than",
    "less_than_or_equal",
    "between",
    "before",
    "after",
    "date_between",
    "in",
    "not_in",
    "is_duplicate",
    "is_unique",
}


def preview_column_types(
    df: pd.DataFrame,
) -> dict[str, str]:
    result: dict[str, str] = {}

    for column in df.columns:
        series = df[column]

        if is_bool_dtype(series.dtype):
            kind = "boolean"
        elif is_datetime64_any_dtype(series.dtype):
            kind = "datetime"
        elif is_numeric_dtype(series.dtype):
            kind = "number"
        else:
            kind = "text"

            non_missing = series.dropna()

            if not non_missing.empty:
                text = (
                    non_missing.astype("string")
                    .str.strip()
                )
                date_like = text.str.match(
                    r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}",
                    na=False,
                )

                if (
                    float(date_like.mean())
                    >= 0.8
                ):
                    parsed = pd.to_datetime(
                        text,
                        errors="coerce",
                    )

                    if (
                        float(parsed.notna().mean())
                        >= 0.8
                    ):
                        kind = "datetime"

        result[str(column)] = kind

    return result


def parse_preview_filters(
    raw_filters: str | None,
) -> list[dict[str, Any]]:
    if raw_filters is None or not raw_filters.strip():
        return []

    try:
        parsed = json.loads(raw_filters)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Preview filters must be valid JSON."
        ) from exc

    if not isinstance(parsed, list):
        raise ValueError(
            "Preview filters must be a list."
        )

    if len(parsed) > 12:
        raise ValueError(
            "A maximum of 12 preview filters is supported."
        )

    normalized: list[dict[str, Any]] = []

    for item in parsed:
        if not isinstance(item, dict):
            raise ValueError(
                "Each preview filter must be an object."
            )

        column = str(
            item.get("column", "")
        ).strip()
        operator = str(
            item.get("operator", "")
        ).strip()

        if not column:
            raise ValueError(
                "Preview filter column is required."
            )

        if operator not in SUPPORTED_FILTER_OPERATORS:
            raise ValueError(
                f"Unsupported preview filter operator: {operator}"
            )

        normalized.append(
            {
                "column": column,
                "operator": operator,
                "value": item.get("value"),
                "value_to": item.get("value_to"),
            }
        )

    return normalized


def _text_series(
    series: pd.Series,
) -> pd.Series:
    return (
        series.astype("string")
        .fillna("")
        .str.strip()
    )


def _require_value(
    item: dict[str, Any],
    key: str = "value",
) -> str:
    value = item.get(key)

    if value is None or str(value).strip() == "":
        raise ValueError(
            f"Preview filter {key} is required."
        )

    return str(value).strip()


def _numeric_value(
    item: dict[str, Any],
    key: str = "value",
) -> float:
    raw = _require_value(
        item,
        key,
    )

    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(
            f"Preview filter {key} must be numeric."
        ) from exc


def _date_value(
    item: dict[str, Any],
    key: str = "value",
) -> pd.Timestamp:
    raw = _require_value(
        item,
        key,
    )

    parsed = pd.to_datetime(
        raw,
        errors="coerce",
    )

    if pd.isna(parsed):
        raise ValueError(
            f"Preview filter {key} must be a valid date."
        )

    return parsed


def _filter_mask(
    df: pd.DataFrame,
    item: dict[str, Any],
) -> pd.Series:
    column = item["column"]
    operator = item["operator"]

    if column not in df.columns:
        raise ValueError(
            f"Preview filter column does not exist: {column}"
        )

    series = df[column]

    if operator == "is_missing":
        return series.isna()

    if operator == "is_not_missing":
        return series.notna()

    if operator in {
        "is_blank",
        "is_not_blank",
    }:
        blank = (
            series.notna()
            & _text_series(series).eq("")
        )
        return (
            blank
            if operator == "is_blank"
            else ~blank
        )

    if operator in {
        "is_duplicate",
        "is_unique",
    }:
        duplicate = (
            series.notna()
            & series.duplicated(
                keep=False
            )
        )
        if operator == "is_duplicate":
            return duplicate

        return (
            series.notna()
            & ~duplicate
        )

    if operator in {
        "contains",
        "not_contains",
        "starts_with",
        "ends_with",
    }:
        value = _require_value(item)
        text = _text_series(series)

        if operator in {
            "contains",
            "not_contains",
        }:
            mask = text.str.contains(
                value,
                case=False,
                regex=False,
                na=False,
            )
            return (
                ~mask
                if operator == "not_contains"
                else mask
            )

        folded = text.str.casefold()
        needle = value.casefold()

        if operator == "starts_with":
            return folded.str.startswith(
                needle,
                na=False,
            )

        return folded.str.endswith(
            needle,
            na=False,
        )

    if operator in {
        "greater_than",
        "greater_than_or_equal",
        "less_than",
        "less_than_or_equal",
        "between",
    }:
        numeric = pd.to_numeric(
            series,
            errors="coerce",
        )
        value = _numeric_value(item)

        if operator == "greater_than":
            return numeric > value
        if operator == "greater_than_or_equal":
            return numeric >= value
        if operator == "less_than":
            return numeric < value
        if operator == "less_than_or_equal":
            return numeric <= value

        value_to = _numeric_value(
            item,
            "value_to",
        )
        lower = min(
            value,
            value_to,
        )
        upper = max(
            value,
            value_to,
        )
        return numeric.between(
            lower,
            upper,
            inclusive="both",
        )

    if operator in {
        "before",
        "after",
        "date_between",
    }:
        dates = pd.to_datetime(
            series,
            errors="coerce",
        )
        value = _date_value(item)

        if operator == "before":
            return dates < value
        if operator == "after":
            return dates > value

        value_to = _date_value(
            item,
            "value_to",
        )
        lower = min(
            value,
            value_to,
        )
        upper = max(
            value,
            value_to,
        )
        return dates.between(
            lower,
            upper,
            inclusive="both",
        )

    if operator in {
        "in",
        "not_in",
    }:
        values = [
            value.strip()
            for value in _require_value(
                item
            ).split(",")
            if value.strip()
        ]

        if not values:
            raise ValueError(
                "Preview filter value must include at least one item."
            )

        text = _text_series(
            series
        ).str.casefold()

        normalized_values = [
            value.casefold()
            for value in values
        ]

        mask = text.isin(
            normalized_values
        )

        return (
            ~mask
            if operator == "not_in"
            else mask
        )

    if operator in {
        "equals",
        "not_equals",
    }:
        value = _require_value(item)

        if is_bool_dtype(series.dtype):
            normalized = value.casefold()

            if normalized not in {
                "true",
                "false",
                "1",
                "0",
                "yes",
                "no",
            }:
                raise ValueError(
                    "Boolean preview filter value must be true or false."
                )

            expected = normalized in {
                "true",
                "1",
                "yes",
            }
            mask = series.eq(
                expected
            )
        elif is_numeric_dtype(series.dtype):
            expected = _numeric_value(
                item
            )
            mask = pd.to_numeric(
                series,
                errors="coerce",
            ).eq(expected)
        elif is_datetime64_any_dtype(
            series.dtype
        ):
            expected = _date_value(
                item
            )
            mask = pd.to_datetime(
                series,
                errors="coerce",
            ).eq(expected)
        else:
            mask = (
                _text_series(series)
                .str.casefold()
                .eq(value.casefold())
            )

        return (
            ~mask
            if operator == "not_equals"
            else mask
        )

    raise ValueError(
        f"Unsupported preview filter operator: {operator}"
    )


def apply_preview_filters(
    *,
    df: pd.DataFrame,
    filters: list[dict[str, Any]],
    logic: Literal[
        "and",
        "or",
    ] = "and",
) -> pd.DataFrame:
    if not filters:
        return df

    masks = [
        _filter_mask(
            df,
            item,
        )
        for item in filters
    ]

    combined = masks[0]

    for mask in masks[1:]:
        combined = (
            combined & mask
            if logic == "and"
            else combined | mask
        )

    return df.loc[
        combined
    ]
