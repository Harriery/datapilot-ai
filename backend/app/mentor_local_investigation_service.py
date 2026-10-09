"""Zero-token evidence queries on a development dataset.

Only the server computes the counts; conclusions about business meaning
remain hypotheses until the learner and Mentor assess the evidence.
"""
from __future__ import annotations

import pandas as pd


def verify_missingness_relationship(
    df: pd.DataFrame,
    *,
    target_column: str,
    group_column: str,
    max_groups: int = 12,
) -> dict:
    if target_column not in df.columns or group_column not in df.columns:
        raise ValueError("Both columns must exist in the working dataset.")
    if target_column == group_column:
        raise ValueError("Choose two distinct columns.")
    if not 1 <= max_groups <= 30:
        raise ValueError("max_groups must be between 1 and 30.")

    target_missing = df[target_column].isna()
    grouped = df[group_column].astype("string").fillna("<NULL>")
    counts = pd.DataFrame({
        "group": grouped,
        "missing": target_missing,
    }).groupby("group", dropna=False, observed=True)["missing"].agg(
        ["size", "sum"]
    ).sort_values("size", ascending=False)

    if len(counts) > max_groups:
        counts = counts.head(max_groups)
        truncated = True
    else:
        truncated = False

    results = [
        {
            "value": str(group),
            "rows": int(row["size"]),
            "missing_rows": int(row["sum"]),
            "present_rows": int(row["size"] - row["sum"]),
            "missing_pct": round(float(row["sum"]) / int(row["size"]) * 100, 2),
        }
        for group, row in counts.iterrows()
    ]
    return {
        "target_column": target_column,
        "group_column": group_column,
        "scope": "working_dataset",
        "total_rows": int(len(df)),
        "total_missing": int(target_missing.sum()),
        "groups": results,
        "groups_truncated": truncated,
        "verification_status": "verified",
        "business_rule_confirmed": False,
    }
