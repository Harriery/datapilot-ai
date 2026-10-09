"""Deterministic evidence sufficiency gate; never asserts business semantics.

A verified calculation is not the same as a confirmed business rule.
No LLM calls or data modifications occur here.
"""
from __future__ import annotations


def assess_relationship_evidence(evidence: dict) -> dict:
    """Assess whether numerical evidence can support a learner interpretation."""
    if evidence.get("verification_status") != "verified":
        return {
            "status": "needs_verification",
            "reason": "unverified_result",
            "can_interpret": False,
            "can_transform": False,
        }

    rows = evidence.get("total_rows")
    missing = evidence.get("total_missing")
    groups = evidence.get("groups")
    if (
        type(rows) is not int
        or type(missing) is not int
        or rows < 0
        or missing < 0
        or missing > rows
        or not isinstance(groups, list)
    ):
        return {
            "status": "conflicting",
            "reason": "invalid_totals",
            "can_interpret": False,
            "can_transform": False,
        }

    summed_rows = 0
    summed_missing = 0
    for item in groups:
        size = item.get("rows") if isinstance(item, dict) else None
        nulls = item.get("missing_rows") if isinstance(item, dict) else None
        present = item.get("present_rows") if isinstance(item, dict) else None
        if (
            type(size) is not int
            or type(nulls) is not int
            or type(present) is not int
            or min(size, nulls, present) < 0
            or nulls + present != size
        ):
            return {
                "status": "conflicting",
                "reason": "invalid_group_counts",
                "can_interpret": False,
                "can_transform": False,
            }
        summed_rows += size
        summed_missing += nulls

    if not evidence.get("groups_truncated", False) and (
        summed_rows != rows or summed_missing != missing
    ):
        return {
            "status": "conflicting",
            "reason": "group_totals_mismatch",
            "can_interpret": False,
            "can_transform": False,
        }
    if evidence.get("groups_truncated", False):
        return {
            "status": "needs_more_evidence",
            "reason": "groups_truncated",
            "can_interpret": False,
            "can_transform": False,
        }
    if rows == 0:
        return {
            "status": "needs_more_evidence",
            "reason": "empty_dataset",
            "can_interpret": False,
            "can_transform": False,
        }

    # Numerical verification permits discussing a hypothesis, not treatment.
    return {
        "status": "ready_for_interpretation",
        "reason": "group_counts_consistent",
        "can_interpret": True,
        "can_transform": False,
        "business_rule_confirmed": False,
    }
