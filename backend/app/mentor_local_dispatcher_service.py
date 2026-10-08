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


def _explicit_missingness_pair(message: str, available: list[str]) -> tuple[str, str] | None:
    """Use explicit column names only, never infer a business relationship."""
    normalized = message.casefold()
    if not any(word in normalized for word in (
        "eksik", "missing", "null", "boş", "bos", "isna",
    )):
        return None
    mentioned = [
        col for col in available
        if re.search(r"(?<!\w)" + re.escape(col) + r"(?!\w)", message, re.IGNORECASE)
    ]
    # Avoid silently picking from three or more named columns.
    if len(mentioned) != 2:
        return None
    # Resolve the target only when the learner's wording is unambiguous.
    # "first ve second eksik" does not identify which field is missing.
    # Explicit constructions such as "reason sütunundaki eksikler" do.
    target_matches = [
        col for col in mentioned
        if re.search(
            r"(?<!\\w)" + re.escape(col)
            + r"(?!\\w)\\s+(?:sütunundaki|kolonundaki|alanındaki|"
            + r"sütununda|kolonunda|alanında)\\s+"
            + r"(?:eksik\\w*|boş\\w*|bos\\w*|missing|null)",
            message, re.IGNORECASE,
        )
    ]
    if len(target_matches) != 1:
        return None
    target = target_matches[0]
    return target, next(col for col in mentioned if col != target)


def dispatch_local_investigation(workspace, message: str, working_path: Path) -> dict:
    """Verify a specific column relationship without model calls or raw SQL."""
    if not working_path.is_file():
        return {"status": "unavailable", "reason": "no_working_dataset"}
    try:
        available = pd.read_csv(working_path, nrows=0).columns.tolist()
    except (OSError, pd.errors.ParserError):
        return {"status": "unavailable", "reason": "working_dataset_unreadable"}
    stat = working_path.stat()
    version = f"{stat.st_size}:{stat.st_mtime_ns}"

    events = workspace.action_evidence_events or []
    recent = next(
        (
            item for item in reversed(events)
            if item.get("action") == "preview_investigation"
            and item.get("verification_status") == "verified"
            and any(
                str(rule.get("operator", "")).lower() in MISSING_OPERATORS
                for rule in item.get("parameters", {}).get("filters", [])
            )
        ),
        None,
    )
    target = None
    group_column = None
    if recent is not None and recent.get("dataset") == "working":
        if recent.get("data_version") == version:
            rules = [
                item for item in recent["parameters"].get("filters", [])
                if str(item.get("operator", "")).lower() in MISSING_OPERATORS
            ]
            if len(rules) == 1 and rules[0].get("column") in available:
                candidate = rules[0]["column"]
                choices = [
                    col for col in available if col != candidate
                    and re.search(
                        r"(?<!\w)" + re.escape(col) + r"(?!\w)",
                        message, re.IGNORECASE,
                    )
                ]
                if len(choices) == 1:
                    target, group_column = candidate, choices[0]

    if target is None:
        pair = _explicit_missingness_pair(message, available)
        if pair is None:
            if recent is not None and recent.get("data_version") != version:
                return {"status": "stale", "reason": "dataset_version_changed"}
            return {
                "status": "needs_clarification",
                "reason": "provide_explicit_missingness_pair",
            }
        target, group_column = pair

    try:
        df = pd.read_csv(working_path, usecols=[target, group_column])
    except (OSError, ValueError, pd.errors.ParserError):
        return {"status": "unavailable", "reason": "working_dataset_unreadable"}

    result = verify_missingness_relationship(
        df, target_column=target, group_column=group_column
    )
    result["sufficiency"] = assess_relationship_evidence(result)
    record_action_evidence(
        workspace,
        action="missingness_relationship",
        dataset="working",
        parameters={
            "target_column": target,
            "group_column": group_column,
            "max_groups": 12,
        },
        result=result,
        data_version=version,
    )
    return {"status": "verified", "evidence": result}
