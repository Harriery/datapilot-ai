import math

import pandas as pd

from backend.app.models import (
    DataQualityAnalysis,
    DataQualityFinding,
)


def analyze_dataframe_locally(
    df: pd.DataFrame,
) -> DataQualityAnalysis:

    findings: list[DataQualityFinding] = []

    row_count = len(df)

    # ==================================================
    # DUPLICATE COLUMN NAMES
    # ==================================================

    duplicate_columns = (
        df.columns[
            df.columns.duplicated()
        ]
        .tolist()
    )

    for column in duplicate_columns:
        findings.append(
            DataQualityFinding(
                issue_type="schema_issue",
                column=str(column),
                severity="high",
                observation=(
                    f"Column name '{column}' "
                    "appears more than once."
                ),
                suggested_action=(
                    "Review the schema and make "
                    "column names unique before "
                    "continuing."
                ),
            )
        )

    # ==================================================
    # UNNAMED COLUMNS
    # ==================================================

    for column in df.columns:

        column_name = str(column)

        if column_name.startswith(
            "Unnamed:"
        ):
            findings.append(
                DataQualityFinding(
                    issue_type="schema_issue",
                    column=column_name,
                    severity="low",
                    observation=(
                        "An unnamed column was found."
                    ),
                    suggested_action=(
                        "Check whether this column "
                        "was created accidentally "
                        "during CSV export."
                    ),
                )
            )

    # ==================================================
    # MISSING VALUES
    # ==================================================

    for column in df.columns:

        missing_count = int(
            df[column].isna().sum()
        )

        if missing_count == 0:
            continue

        if row_count == 0:
            missing_percent = 0
        else:
            missing_percent = round(
                missing_count
                / row_count
                * 100,
                2,
            )

        severity = (
            "high"
            if missing_percent >= 50
            else "medium"
        )

        findings.append(
            DataQualityFinding(
                issue_type="missing_values",
                column=str(column),
                severity=severity,
                observation=(
                    f"{missing_count} missing "
                    f"values found "
                    f"({missing_percent}%)."
                ),
                suggested_action=(
                    "Inspect the affected rows and "
                    "confirm the business rule before "
                    "dropping or filling values."
                ),
            )
        )

    # ==================================================
    # DUPLICATE ROWS
    # ==================================================

    duplicate_count = int(
        df.duplicated().sum()
    )

    if duplicate_count > 0:

        if row_count == 0:
            duplicate_percent = 0
        else:
            duplicate_percent = round(
                duplicate_count
                / row_count
                * 100,
                2,
            )

        findings.append(
            DataQualityFinding(
                issue_type="duplicate_rows",
                column=None,
                severity=(
                    "high"
                    if duplicate_percent >= 20
                    else "medium"
                ),
                observation=(
                    f"{duplicate_count} duplicate "
                    f"rows found "
                    f"({duplicate_percent}%)."
                ),
                suggested_action=(
                    "Inspect duplicate rows and "
                    "confirm whether they represent "
                    "true duplicates before removing "
                    "them."
                ),
            )
        )

    # ==================================================
    # COLUMN-LEVEL CHECKS
    # ==================================================

    for column in df.columns:

        series = df[column]

        non_null = series.dropna()

        # ----------------------------------------------
        # CONSTANT COLUMN
        # ----------------------------------------------

        if (
            len(non_null) > 1
            and non_null.nunique(
                dropna=True
            ) == 1
        ):
            findings.append(
                DataQualityFinding(
                    issue_type="suspicious_values",
                    column=str(column),
                    severity="low",
                    observation=(
                        "All non-null values in this "
                        "column are identical."
                    ),
                    suggested_action=(
                        "Confirm whether this column "
                        "is intentionally constant or "
                        "contains no useful variation."
                    ),
                )
            )

        # ----------------------------------------------
        # STRING CHECKS
        # ----------------------------------------------

        if (
            pd.api.types
            .is_object_dtype(series)
            or pd.api.types
            .is_string_dtype(series)
        ):

            string_series = (
                series.astype("string")
            )

            stripped = (
                string_series.str.strip()
            )

            empty_count = int(
                stripped.eq("")
                .fillna(False)
                .sum()
            )

            if empty_count > 0:
                findings.append(
                    DataQualityFinding(
                        issue_type=(
                            "missing_values"
                        ),
                        column=str(column),
                        severity="medium",
                        observation=(
                            f"{empty_count} empty "
                            "or whitespace-only "
                            "values found."
                        ),
                        suggested_action=(
                            "Review whether empty "
                            "strings should be treated "
                            "as missing values."
                        ),
                    )
                )

            whitespace_mask = (
                string_series.notna()
                & (
                    string_series
                    != stripped
                )
            )

            whitespace_count = int(
                whitespace_mask.sum()
            )

            if whitespace_count > 0:
                findings.append(
                    DataQualityFinding(
                        issue_type=(
                            "suspicious_values"
                        ),
                        column=str(column),
                        severity="low",
                        observation=(
                            f"{whitespace_count} "
                            "values contain leading "
                            "or trailing whitespace."
                        ),
                        suggested_action=(
                            "Inspect the affected "
                            "values and normalize "
                            "whitespace if appropriate."
                        ),
                    )
                )

            clean_values = (
                stripped
                .dropna()
            )

            if len(clean_values) > 1:

                original_unique = (
                    clean_values.nunique()
                )

                lowercase_unique = (
                    clean_values
                    .str.lower()
                    .nunique()
                )

                if (
                    lowercase_unique
                    < original_unique
                ):
                    findings.append(
                        DataQualityFinding(
                            issue_type=(
                                "suspicious_values"
                            ),
                            column=str(column),
                            severity="low",
                            observation=(
                                "Values differ only "
                                "by letter casing."
                            ),
                            suggested_action=(
                                "Check whether casing "
                                "should be standardized "
                                "for this column."
                            ),
                        )
                    )

        # ----------------------------------------------
        # NUMERIC CHECKS
        # ----------------------------------------------

        if pd.api.types.is_numeric_dtype(
            series
        ):

            numeric_series = (
                pd.to_numeric(
                    series,
                    errors="coerce",
                )
            )

            infinity_count = int(
                numeric_series
                .map(
                    lambda value:
                    isinstance(
                        value,
                        (int, float),
                    )
                    and math.isinf(value)
                )
                .sum()
            )

            if infinity_count > 0:
                findings.append(
                    DataQualityFinding(
                        issue_type=(
                            "suspicious_values"
                        ),
                        column=str(column),
                        severity="high",
                        observation=(
                            f"{infinity_count} "
                            "infinite numeric values "
                            "found."
                        ),
                        suggested_action=(
                            "Inspect how infinite "
                            "values were produced "
                            "before continuing."
                        ),
                    )
                )

            finite_values = (
                numeric_series[
                    numeric_series.map(
                        lambda value:
                        pd.notna(value)
                        and not math.isinf(
                            float(value)
                        )
                    )
                ]
            )

            # ------------------------------------------
            # IQR OUTLIER SIGNAL
            # ------------------------------------------

            if len(finite_values) >= 4:

                q1 = finite_values.quantile(
                    0.25
                )

                q3 = finite_values.quantile(
                    0.75
                )

                iqr = q3 - q1

                if iqr > 0:

                    lower_bound = (
                        q1 - 1.5 * iqr
                    )

                    upper_bound = (
                        q3 + 1.5 * iqr
                    )

                    outlier_count = int(
                        (
                            (
                                finite_values
                                < lower_bound
                            )
                            |
                            (
                                finite_values
                                > upper_bound
                            )
                        ).sum()
                    )

                    if outlier_count > 0:
                        findings.append(
                            DataQualityFinding(
                                issue_type=(
                                    "suspicious_values"
                                ),
                                column=str(column),
                                severity="low",
                                observation=(
                                    f"{outlier_count} "
                                    "possible outlier "
                                    "values detected "
                                    "using the IQR "
                                    "method."
                                ),
                                suggested_action=(
                                    "Review these "
                                    "values with domain "
                                    "or business rules. "
                                    "Do not remove them "
                                    "automatically."
                                ),
                            )
                        )

    return DataQualityAnalysis(
        findings=findings
    )

def merge_data_quality_analyses(
    local_analysis: DataQualityAnalysis,
    ai_analysis: DataQualityAnalysis,
) -> DataQualityAnalysis:

    merged_findings = []
    seen = set()

    for analysis in (
        local_analysis,
        ai_analysis,
    ):
        for finding in analysis.findings:

            key = (
                finding.issue_type,
                finding.column,
                finding.observation,
                finding.suggested_action,
            )

            if key in seen:
                continue

            seen.add(key)

            merged_findings.append(
                finding
            )

    return DataQualityAnalysis(
        findings=merged_findings
    )