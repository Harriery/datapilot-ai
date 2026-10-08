from types import SimpleNamespace

from backend.app.mentor_action_evidence_service import (
    concise_action_evidence,
    record_action_evidence,
)


def test_verified_action_record_is_deduplicated_without_ai():
    workspace = SimpleNamespace(action_evidence_events=[])
    arguments = {
        "action": "preview_investigation",
        "dataset": "working",
        "parameters": {
            "filters": [{"column": "reason", "operator": "is_missing"}],
            "logic": "and",
            "search": "",
        },
        "result": {"total_rows": 100, "matching_rows": 80},
        "data_version": "source-1",
    }
    assert record_action_evidence(workspace, **arguments)
    assert not record_action_evidence(workspace, **arguments)
    assert len(workspace.action_evidence_events) == 1
    assert workspace.action_evidence_events[0]["verification_status"] == "verified"
    assert workspace.action_evidence_events[0]["origin"] == "backend"


def test_new_dataset_version_creates_new_evidence():
    workspace = SimpleNamespace(action_evidence_events=[])
    base = {
        "action": "preview_investigation",
        "dataset": "working",
        "parameters": {"filters": [{"column": "reason", "operator": "is_missing"}]},
        "result": {"total_rows": 100, "matching_rows": 80},
    }
    assert record_action_evidence(workspace, **base, data_version="v1")
    assert record_action_evidence(workspace, **base, data_version="v2")
    assert len(workspace.action_evidence_events) == 2


def test_evidence_history_is_bounded_and_context_is_compact():
    workspace = SimpleNamespace(action_evidence_events=[])
    for number in range(90):
        record_action_evidence(
            workspace,
            action="preview_investigation",
            dataset="source",
            parameters={"search": str(number)},
            result={"total_rows": 100, "matching_rows": 1},
            data_version="v1",
        )
    assert len(workspace.action_evidence_events) == 80
    context = concise_action_evidence(workspace)
    assert len(context) == 4
    assert context[-1]["parameters"]["search"] == "89"
    assert "timestamp" not in context[-1]
    assert "fingerprint" not in context[-1]
