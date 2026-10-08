"""Conservative, zero-LLM dispatcher for verified local investigations.

Only dispatches when a recent backend-verified missingness filter exists
and a second column is explicitly named in the user's message. Never guesses
a business relationship or executes arbitrary user-provided SQL.
"""
from __future__ import annotations

from pathlib import Path
import re
import pandas as pd

from backend.app.mentor_action_evidence_service import record_action_evidence
from backend.app.mentor_evidence_sufficiency_service import assess_relationship_evidence
from backend.app.mentor_local_investigation_service import (
    verify_missingness_relationship,
)


MISSING_OPERATORS = {"is_missing", "is_null", "is_empty"}


def dispatch_local_investigation(workspace, message: str, working_path: Path) -> dict:
    """Return status and safe evidence without calling an LLM."""
    if not working_path.is_file():
        return {"status": "unavailable", "reason": "no_working_dataset"}
    events = workspace.action_evidence_events or []
    investigation = next(
        (
            item for item in reversed(events)
            if item.get("action") == "preview_investigation"
            and item.get("dataset") == "working"
            and item.get("verification_status") == "verified"
            and any(
                str(rule.get("operator", "")).lower() in MISSING_OPERATORS
                for rule in item.get("parameters", {}).get("filters", [])
            )
        ),
        None,
    )
    if investigation is None:
        return {"status": "not_applicable", "reason": "no_verified_missingness_filter"}

    # Refuse stale observations when the development dataset has changed.
    stat = working_path.stat()
    version = f"{stat.st_size}:{stat.st_mtime_ns}"
    if investigation.get("data_version") != version:
        return {"status": "stale", "reason": "dataset_version_changed"}

    rules = [
        item for item in investigation["parameters"]["filters"]
        if str(item.get("operator", "")).lower() in MISSING_OPERATORS
    ]
    if len(rules) != 1:
        return {"status": "needs_clarification", "reason": "ambiguous_missingness_target"}
    target = rules[0].get("column")
    available = pd.read_csv(working_path, nrows=0).columns.tolist()
    if target not in available:
        return {"status": "needs_clarification", "reason": "target_column_missing"}

    # A group column is a meaningful investigation choice; only dispatch
    # when the learner explicitly mentions it, not merely because it exists.
    candidates = [
        column for column in available if column != target
        and re.search(
            r"(?<!\w)" + re.escape(column) + r"(?!\w)",
            message,
            flags=re.IGNORECASE,
        )
    ]
    if len(candidates) != 1:
        return {
            "status": "needs_clarification",
            "reason": "request_one_group_column",
            "target_column": target,
        }
    group_column = candidates[0]
    df = pd.read_csv(working_path, usecols=[target, group_column])
    result = verify_missingness_relationship(
        df, target_column=target, group_column=group_column
    )
    result["sufficiency"] = assess_relationship_evidence(result)
    record_action_evidence(
        workspace,
        action="missingness_relationship",
        dataset="working",
        parameters={"target_column": target, "group_column": group_column, "max_groups": 12},
        result=result,
        data_version=version,
    )
    return {"status": "verified", "evidence": result}
