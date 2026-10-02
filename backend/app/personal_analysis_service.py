from pathlib import Path

import pandas as pd

from backend.app.models import (
    PersonalProjectAnalysisPlan,
    PersonalProjectAnalysisResult,
    PersonalProjectColumnIntelligence,
    PersonalProjectModelDiscovery,
    PersonalProjectDataModelStudio,
    PersonalProjectDataModelColumn,
    PersonalProjectKPIDefinition,
)

TIME_COLUMN_NAMES = {
    "year", "date", "datetime", "timestamp",
    "month", "quarter", "week", "day",
}
IDENTIFIER_COLUMN_NAMES = {"id", "uuid", "identifier"}
ENTITY_IDENTITY_COLUMN_NAMES = {
    "name", "first_name", "last_name", "full_name",
    "email", "phone", "telephone",
}


def _normalize_column_name(column: str) -> str:
    return (
        column.strip().lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def _is_time_column(column: str) -> bool:
    normalized = _normalize_column_name(column)
    return (
        normalized in TIME_COLUMN_NAMES
        or any(normalized.endswith(f"_{name}") for name in TIME_COLUMN_NAMES)
    )


def _is_identifier_column(column: str) -> bool:
    normalized = _normalize_column_name(column)
    return (
        normalized in IDENTIFIER_COLUMN_NAMES
        or normalized.endswith("_id")
    )


def _is_entity_identity_column(column: str) -> bool:
    return _normalize_column_name(column) in ENTITY_IDENTITY_COLUMN_NAMES


def _fact_table_name(dataset_filename: str | None) -> str:
    if not dataset_filename:
        return "fact_dataset"
    return f"fact_{_normalize_column_name(Path(dataset_filename).stem)}"


def build_personal_analysis_plan(
    profile: dict,
    dataset_filename: str | None = None,
) -> PersonalProjectAnalysisPlan:
    columns = profile.get("columns", [])
    row_count = int(profile.get("row_count", 0) or 0)
    numeric_columns = set(profile.get("numeric_columns", []))
    data_types = profile.get("data_types", {})
    null_counts = profile.get("null_counts", {})
    distinct_counts = profile.get("distinct_counts", {})
    examples = profile.get("column_examples", {})
    numeric_summary = profile.get("numeric_summary", {})

    time_candidates = [
        column for column in columns
        if _is_time_column(column)
    ]

    numeric_candidates = [
        column for column in columns
        if (
            column in numeric_columns
            and column not in time_candidates
            and not _is_identifier_column(column)
        )
    ]

    dimension_candidates = [
        column for column in columns
        if (
            column not in numeric_candidates
            and column not in time_candidates
            and not _is_identifier_column(column)
            and not _is_entity_identity_column(column)
        )
    ]

    key_candidates = [
        column for column in columns
        if (
            _is_identifier_column(column)
            and row_count > 0
            and int(null_counts.get(column, 0) or 0) == 0
            and int(distinct_counts.get(column, 0) or 0) == row_count
        )
    ]

    column_intelligence = []
    for column in columns:
        null_count = int(null_counts.get(column, 0) or 0)
        distinct_count = int(distinct_counts.get(column, 0) or 0)
        roles = []
        reasoning = []

        if column in key_candidates:
            roles.append("key")
            reasoning.append("Identifier-like name with unique, non-null values.")
        if column in time_candidates:
            roles.append("time")
            reasoning.append("Column name indicates a time or date field.")
        if column in numeric_candidates:
            roles.append("numeric")
            reasoning.append("Numeric field that can support aggregations.")
        if column in dimension_candidates:
            roles.append("dimension")
            reasoning.append("Descriptive field suitable for grouping.")
        if not reasoning:
            reasoning.append("No strong analytical role detected automatically.")

        stats = numeric_summary.get(column, {})
        confidence = (
            "high"
            if column in key_candidates or column in time_candidates
            else "medium"
            if column in numeric_candidates or column in dimension_candidates
            else "low"
        )

        column_intelligence.append(
            PersonalProjectColumnIntelligence(
                name=column,
                data_type=str(data_types.get(column, "unknown")),
                null_count=null_count,
                null_percentage=(
                    round((null_count / row_count) * 100, 2)
                    if row_count else 0.0
                ),
                distinct_count=distinct_count,
                cardinality_ratio=(
                    round(distinct_count / row_count, 4)
                    if row_count else 0.0
                ),
                examples=[str(value) for value in examples.get(column, [])],
                minimum=stats.get("min"),
                maximum=stats.get("max"),
                role_candidates=roles,
                confidence=confidence,
                reasoning=reasoning,
            )
        )

    dimension_tables = [
        f"dim_{_normalize_column_name(column)}"
        for column in dimension_candidates + time_candidates
    ]

    grain = (
        f"One row per {key_candidates[0]}."
        if key_candidates
        else "One row per validated source record."
    )

    discovery_reasoning = [
        (
            f"{key_candidates[0]} is a strong row-level key candidate."
            if key_candidates
            else "No reliable unique identifier was detected."
        )
    ]
    if numeric_candidates:
        discovery_reasoning.append(
            f"{len(numeric_candidates)} numeric field(s) can support future measures."
        )
    if dimension_candidates or time_candidates:
        discovery_reasoning.append(
            "Descriptive/time fields suggest a star-schema candidate."
        )

    discovery = PersonalProjectModelDiscovery(
        grain=grain,
        fact_table_candidate=_fact_table_name(dataset_filename),
        dimension_table_candidates=list(dict.fromkeys(dimension_tables)),
        confidence=(
            "high"
            if key_candidates and numeric_candidates
            else "medium"
            if numeric_candidates or dimension_candidates or time_candidates
            else "low"
        ),
        reasoning=discovery_reasoning,
    )

    suggested_questions = []
    first_numeric = numeric_candidates[0] if numeric_candidates else None
    first_dimension = dimension_candidates[0] if dimension_candidates else None
    first_time = time_candidates[0] if time_candidates else None

    if first_numeric and first_time:
        suggested_questions.append(
            f"How does {first_numeric} change over {first_time}?"
        )
    if first_numeric and first_dimension:
        suggested_questions.append(
            f"How does {first_numeric} vary by {first_dimension}?"
        )
    if first_numeric and first_dimension and first_time:
        suggested_questions.append(
            f"How does {first_numeric} change over {first_time} across {first_dimension}?"
        )

    return PersonalProjectAnalysisPlan(
        measure_candidates=numeric_candidates,
        numeric_candidates=numeric_candidates,
        key_candidates=key_candidates,
        dimension_candidates=dimension_candidates,
        time_candidates=time_candidates,
        column_intelligence=column_intelligence,
        model_discovery=discovery,
        suggested_questions=suggested_questions,
        source="local",
    )


def build_personal_analysis_result(
    df: pd.DataFrame,
    measure: str,
    dimension: str | None = None,
) -> PersonalProjectAnalysisResult:

    if measure not in df.columns:
        raise ValueError(
            f"Measure column not found: {measure}"
        )

    if not pd.api.types.is_numeric_dtype(
        df[measure]
    ):
        raise ValueError(
            f"Measure must be numeric: {measure}"
        )

    if (
        dimension is not None
        and dimension not in df.columns
    ):
        raise ValueError(
            f"Dimension column not found: {dimension}"
        )

    measure_series = (
        df[measure]
        .dropna()
    )

    overall = {
        "count": int(
            measure_series.count()
        ),
        "mean": (
            float(measure_series.mean())
            if not measure_series.empty
            else None
        ),
        "min": (
            float(measure_series.min())
            if not measure_series.empty
            else None
        ),
        "max": (
            float(measure_series.max())
            if not measure_series.empty
            else None
        ),
    }

    grouped_results: list[dict] = []

    if dimension is not None:

        grouped = df.groupby(
            dimension,
            dropna=False,
        )[measure]

        for (
            dimension_value,
            group,
        ) in grouped:

            clean_group = (
                group.dropna()
            )

            if pd.isna(
                dimension_value
            ):
                safe_dimension_value = None
            else:
                safe_dimension_value = (
                    dimension_value
                )

            grouped_results.append(
                {
                    "value":
                        safe_dimension_value,

                    "count":
                        int(
                            clean_group.count()
                        ),

                    "mean":
                        (
                            float(
                                clean_group.mean()
                            )
                            if not clean_group.empty
                            else None
                        ),

                    "min":
                        (
                            float(
                                clean_group.min()
                            )
                            if not clean_group.empty
                            else None
                        ),

                    "max":
                        (
                            float(
                                clean_group.max()
                            )
                            if not clean_group.empty
                            else None
                        ),
                }
            )

    return PersonalProjectAnalysisResult(
        measure=measure,
        dimension=dimension,
        overall=overall,
        grouped_results=(
            grouped_results
        ),
        source="local",
    )

def _get_model_column(
    studio: PersonalProjectDataModelStudio,
    table_name: str,
    column_name: str,
) -> PersonalProjectDataModelColumn:
    table = next(
        (
            table
            for table in studio.tables
            if table.name == table_name
        ),
        None,
    )

    if table is None:
        raise ValueError(
            f"Semantic table not found: {table_name}"
        )

    column = next(
        (
            column
            for column in table.columns
            if column.name == column_name
        ),
        None,
    )

    if column is None:
        raise ValueError(
            "Semantic column not found: "
            f"{table_name}.{column_name}"
        )

    return column


def _source_series(
    df: pd.DataFrame,
    source_column: str,
) -> pd.Series:
    if source_column not in df.columns:
        raise ValueError(
            "Source column required by semantic model "
            f"was not found: {source_column}"
        )

    return df[source_column]


def materialize_semantic_column(
    df: pd.DataFrame,
    studio: PersonalProjectDataModelStudio,
    table_name: str,
    column_name: str,
) -> pd.Series:
    column = _get_model_column(
        studio=studio,
        table_name=table_name,
        column_name=column_name,
    )

    derivation = column.derivation

    if derivation is None:
        source_name = (
            column.source_column
            or column.name
        )

        return _source_series(
            df,
            source_name,
        ).copy()

    source_series = [
        _source_series(df, source)
        for source in derivation.source_columns
    ]

    if derivation.type == "date_part":
        source = pd.to_datetime(
            source_series[0],
            errors="coerce",
            dayfirst=True,
        )

        if derivation.operation == "year":
            return source.dt.year

        if derivation.operation == "quarter":
            return source.dt.quarter

        if derivation.operation == "month":
            return source.dt.month

        if derivation.operation == "month_name":
            return source.dt.month_name()

        if derivation.operation == "day_of_week":
            return source.dt.day_name()

    if derivation.type == "mapping":
        mapping = {
            rule.source_value:
                rule.display_value
            for rule in derivation.mapping_rules
        }

        if not mapping:
            legacy = str(
                derivation.parameters.get(
                    "mapping",
                    "",
                )
            )

            for line in legacy.splitlines():
                if "=>" not in line:
                    continue

                source_value, display_value = (
                    line.split("=>", 1)
                )

                mapping[
                    source_value.strip()
                ] = display_value.strip()

        return source_series[0].map(
            lambda value: (
                mapping.get(
                    str(value),
                    value,
                )
                if not pd.isna(value)
                else value
            )
        )

    if derivation.type == "text":
        source = (
            source_series[0]
            .astype("string")
        )

        if derivation.operation == "trim":
            return source.str.strip()

        if derivation.operation == "uppercase":
            return source.str.upper()

        if derivation.operation == "lowercase":
            return source.str.lower()

        if derivation.operation == "replace":
            old = str(
                derivation.parameters.get(
                    "old",
                    "",
                )
            )

            new = str(
                derivation.parameters.get(
                    "new",
                    "",
                )
            )

            return source.str.replace(
                old,
                new,
                regex=False,
            )

        if derivation.operation == "substring":
            start = int(
                derivation.parameters.get(
                    "start",
                    0,
                )
            )

            length = derivation.parameters.get(
                "length"
            )

            if length is None:
                return source.str.slice(
                    start
                )

            return source.str.slice(
                start,
                start + int(length),
            )

    if derivation.type == "multi_column":
        separator = str(
            derivation.parameters.get(
                "separator",
                " ",
            )
        )

        result = (
            source_series[0]
            .astype("string")
            .fillna("")
        )

        for source in source_series[1:]:
            result = (
                result
                + separator
                + source.astype("string").fillna("")
            )

        return result.str.strip()

    if derivation.type == "numeric":
        numeric_sources = [
            pd.to_numeric(
                source,
                errors="coerce",
            )
            for source in source_series
        ]

        if derivation.operation == "round":
            decimals = int(
                derivation.parameters.get(
                    "decimals",
                    0,
                )
            )

            return numeric_sources[0].round(
                decimals
            )

        left = numeric_sources[0]
        right = numeric_sources[1]

        if derivation.operation == "add":
            return left + right

        if derivation.operation == "subtract":
            return left - right

        if derivation.operation == "multiply":
            return left * right

        if derivation.operation == "divide":
            return left.div(
                right.replace(0, pd.NA)
            )

    if derivation.type == "bucketing":
        source = pd.to_numeric(
            source_series[0],
            errors="coerce",
        )

        def bucket_value(value):
            if pd.isna(value):
                return None

            for rule in derivation.bucket_rules:
                minimum = float(
                    rule.min_value
                )
                maximum = float(
                    rule.max_value
                )

                if (
                    value >= minimum
                    and value <= maximum
                ):
                    return rule.label

            return None

        return source.map(
            bucket_value
        )

    raise ValueError(
        "Unsupported semantic derivation: "
        f"{derivation.type}/"
        f"{derivation.operation}"
    )


def _aggregate_series(
    series: pd.Series,
    aggregation: str,
) -> float | int | None:
    clean = pd.to_numeric(
        series,
        errors="coerce",
    ).dropna()

    if aggregation == "count":
        return int(
            clean.count()
        )

    if clean.empty:
        return None

    if aggregation == "sum":
        return float(
            clean.sum()
        )

    if aggregation == "mean":
        return float(
            clean.mean()
        )

    if aggregation == "min":
        return float(
            clean.min()
        )

    if aggregation == "max":
        return float(
            clean.max()
        )

    raise ValueError(
        f"Unsupported KPI aggregation: {aggregation}"
    )


def _evaluate_custom_formula(
    formula: str,
    df: pd.DataFrame,
    studio: PersonalProjectDataModelStudio,
) -> float | int | None:
    expression = formula.strip()

    def split_args(value: str) -> tuple[str, str]:
        depth = 0

        for index, char in enumerate(value):
            if char == "(":
                depth += 1

            elif char == ")":
                depth -= 1

            elif (
                char == ","
                and depth == 0
            ):
                return (
                    value[:index].strip(),
                    value[index + 1:].strip(),
                )

        raise ValueError(
            "SAFE_DIVIDE requires two arguments."
        )

    def evaluate(value: str):
        value = value.strip()

        open_index = value.find("(")

        if (
            open_index <= 0
            or not value.endswith(")")
        ):
            raise ValueError(
                "Invalid custom KPI expression."
            )

        function_name = (
            value[:open_index]
            .strip()
            .upper()
        )

        inner = value[
            open_index + 1:-1
        ].strip()

        if function_name == "SAFE_DIVIDE":
            left_expr, right_expr = (
                split_args(inner)
            )

            numerator = evaluate(
                left_expr
            )

            denominator = evaluate(
                right_expr
            )

            if (
                denominator is None
                or denominator == 0
            ):
                return None

            if numerator is None:
                return None

            return float(
                numerator / denominator
            )

        if function_name == "COUNT_ROWS":
            table_name = inner

            if not any(
                table.name == table_name
                for table in studio.tables
            ):
                raise ValueError(
                    "Semantic table not found: "
                    f"{table_name}"
                )

            return int(len(df))

        if "." not in inner:
            raise ValueError(
                "Custom KPI aggregate requires "
                "table.column reference."
            )

        table_name, column_name = (
            part.strip()
            for part
            in inner.split(".", 1)
        )

        series = (
            materialize_semantic_column(
                df=df,
                studio=studio,
                table_name=table_name,
                column_name=column_name,
            )
        )

        aggregation_map = {
            "SUM": "sum",
            "MEAN": "mean",
            "COUNT": "count",
            "MIN": "min",
            "MAX": "max",
        }

        aggregation = (
            aggregation_map.get(
                function_name
            )
        )

        if aggregation is None:
            raise ValueError(
                "Unsupported custom KPI function: "
                f"{function_name}"
            )

        return _aggregate_series(
            series,
            aggregation,
        )

    return evaluate(
        expression
    )


def build_semantic_analysis_result(
    df: pd.DataFrame,
    studio: PersonalProjectDataModelStudio,
    definition: PersonalProjectKPIDefinition,
    dimension_table: str | None = None,
    dimension: str | None = None,
) -> PersonalProjectAnalysisResult:
    if definition.fact_table is None:
        raise ValueError(
            "Saved KPI has no fact table."
        )

    def evaluate_metric(
        scoped_df: pd.DataFrame,
    ):
        if (
            definition.formula_mode
            == "custom"
        ):
            if not definition.formula:
                raise ValueError(
                    "Custom KPI formula is missing."
                )

            return _evaluate_custom_formula(
                formula=definition.formula,
                df=scoped_df,
                studio=studio,
            )

        if definition.formula_mode == "row_count":
            return int(
                len(scoped_df)
            )

        if (
            definition.measure is None
            or definition.aggregation is None
        ):
            raise ValueError(
                "Saved KPI is missing measure metadata."
            )

        measure_series = (
            materialize_semantic_column(
                df=scoped_df,
                studio=studio,
                table_name=definition.fact_table,
                column_name=definition.measure,
            )
        )

        return _aggregate_series(
            measure_series,
            definition.aggregation,
        )

    metric_value = evaluate_metric(
        df
    )

    grouped_results: list[dict] = []

    if (
        dimension_table is not None
        and dimension is not None
    ):
        dimension_series = (
            materialize_semantic_column(
                df=df,
                studio=studio,
                table_name=dimension_table,
                column_name=dimension,
            )
        )

        grouping_df = pd.DataFrame(
            {
                "__dimension": dimension_series,
            },
            index=df.index,
        )

        for (
            dimension_value,
            index_values,
        ) in grouping_df.groupby(
            "__dimension",
            dropna=False,
        ).groups.items():
            scoped_df = df.loc[
                index_values
            ]

            safe_dimension_value = (
                None
                if pd.isna(
                    dimension_value
                )
                else dimension_value
            )

            grouped_results.append(
                {
                    "value":
                        safe_dimension_value,
                    "count":
                        int(len(scoped_df)),
                    "metric_value":
                        evaluate_metric(
                            scoped_df
                        ),
                    "mean": None,
                    "min": None,
                    "max": None,
                }
            )

    return PersonalProjectAnalysisResult(
        measure=definition.title,
        dimension=dimension,
        kpi_code=definition.code,
        dimension_table=dimension_table,
        aggregation=(
            "custom"
            if definition.formula_mode
            == "custom"
            else definition.aggregation
        ),
        overall={
            "count": int(len(df)),
            "metric_value":
                metric_value,
            "mean": (
                metric_value
                if definition.aggregation
                == "mean"
                else None
            ),
            "min": (
                metric_value
                if definition.aggregation
                == "min"
                else None
            ),
            "max": (
                metric_value
                if definition.aggregation
                == "max"
                else None
            ),
        },
        grouped_results=grouped_results,
        source="local",
    )
