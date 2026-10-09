from backend.app.mentor_evidence_sufficiency_service import (
    assess_relationship_evidence,
)


def _valid():
    return {
        "verification_status": "verified",
        "total_rows": 4,
        "total_missing": 3,
        "groups_truncated": False,
        "groups": [
            {"value": "0", "rows": 2, "missing_rows": 2, "present_rows": 0},
            {"value": "1", "rows": 2, "missing_rows": 1, "present_rows": 1},
        ],
    }


def test_consistent_evidence_allows_interpretation_not_transformation():
    decision = assess_relationship_evidence(_valid())
    assert decision["status"] == "ready_for_interpretation"
    assert decision["can_interpret"] is True
    assert decision["can_transform"] is False
    assert decision["business_rule_confirmed"] is False


def test_unverified_evidence_blocks_interpretation():
    example = _valid()
    example["verification_status"] = "unverified"
    assert assess_relationship_evidence(example)["status"] == "needs_verification"


def test_conflicting_group_totals_are_rejected():
    example = _valid()
    example["groups"][1]["missing_rows"] = 2
    assert assess_relationship_evidence(example)["status"] == "conflicting"


def test_truncated_groups_require_additional_evidence():
    example = _valid()
    example["groups_truncated"] = True
    decision = assess_relationship_evidence(example)
    assert decision["status"] == "needs_more_evidence"
    assert decision["can_transform"] is False


def test_empty_dataset_requires_additional_evidence():
    example = {
        "verification_status": "verified",
        "total_rows": 0,
        "total_missing": 0,
        "groups": [],
        "groups_truncated": False,
    }
    assert assess_relationship_evidence(example)["status"] == "needs_more_evidence"
