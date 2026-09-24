from backend.app.models import (
    DataQualityAnalysis,
)


def build_notebook_mentor_guidance(
    code: str,
    dataset_profile: dict | None,
    dataset_analysis: DataQualityAnalysis | None,
) -> list[str]:
    normalized = (
        code
        .strip()
        .lower()
    )

    guidance: list[str] = []

    null_counts = (
        (
            dataset_profile
            or {}
        ).get(
            "null_counts",
            {}
        )
        or {}
    )

    missing_columns = [
        (
            str(column),
            int(count),
        )
        for column, count
        in null_counts.items()
        if int(count) > 0
    ]

    missing_columns.sort(
        key=lambda item:
            item[1],
        reverse=True,
    )

    if "dropna(" in normalized:
        if missing_columns:
            top_missing = ", ".join(
                (
                    f"{column} ({count})"
                )
                for column, count
                in missing_columns[:4]
            )

            guidance.append(
                (
                    "dropna() can remove many rows. "
                    "The source profile currently has "
                    f"missing values in: {top_missing}. "
                    "Check the exact subset/business rule "
                    "before dropping rows."
                )
            )
        else:
            guidance.append(
                (
                    "Before using dropna(), compare "
                    "the before/after row count and "
                    "confirm which columns are allowed "
                    "to remove records."
                )
            )

    if "fillna(" in normalized:
        guidance.append(
            (
                "For fillna(), justify the fill strategy "
                "per column. Mean/median/mode can change "
                "the distribution and should be validated "
                "against the business meaning."
            )
        )

    if (
        "pd.to_datetime" in normalized
        or ".astype(" in normalized
        or "to_numeric(" in normalized
    ):
        guidance.append(
            (
                "Type conversion can silently create "
                "missing/invalid values. Compare null "
                "counts before and after conversion."
            )
        )

    if (
        "df = df[" in normalized
        or ".query(" in normalized
        or ".loc[" in normalized
    ):
        guidance.append(
            (
                "This code may filter rows. Track the "
                "before/after row count and confirm that "
                "record removal is an intentional business "
                "rule rather than accidental data loss."
            )
        )

    if (
        ".drop(" in normalized
        and "columns" in normalized
    ):
        guidance.append(
            (
                "Column removal is irreversible in the "
                "working result. Confirm that the column "
                "is not needed for model grain, joins, "
                "KPIs or later validation."
            )
        )

    if "inplace=true" in normalized:
        guidance.append(
            (
                "Prefer explicit dataframe assignment in "
                "learning/pipeline code. It is easier to "
                "review and replay than inplace mutation."
            )
        )

    if (
        dataset_analysis is not None
        and any(
            finding.issue_type
            == "missing_values"
            for finding
            in dataset_analysis.findings
        )
        and not any(
            token in normalized
            for token in (
                "dropna(",
                "fillna(",
            )
        )
    ):
        guidance.append(
            (
                "The workspace still has missing-value "
                "findings. Make sure this experiment does "
                "not hide them without resolving the "
                "intended quality rule."
            )
        )

    if not guidance:
        guidance.append(
            (
                "State what you expect this cell to change, "
                "then compare row count, schema and a small "
                "preview before promoting it to the pipeline."
            )
        )

    return guidance
