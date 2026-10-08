from types import SimpleNamespace

import pandas as pd

from backend.app.mentor_action_evidence_service import record_action_evidence
from backend.app.mentor_local_dispatcher_service import (
    dispatch_local_investigation,
)


def _workspace_with_filter(path):
    stat = path.stat()
    version = f"{stat.st_size}:{stat.st_mtime_ns}"
    workspace = SimpleNamespace(action_evidence_events=[])
    record_action_evidence(
        workspace,
        action="preview_investigation",
        dataset="working",
        parameters={
            "filters": [{"column": "optional", "operator": "is_missing"}],
            "logic": "and",
            "search": "",
        },
        result={"total_rows": 4, "matching_rows": 3},
        data_version=version,
    )
    return workspace


def test_dispatcher_verifies_explicit_relationship_without_llm(tmp_path):
    path = tmp_path / "working.csv"
    pd.DataFrame({
        "optional": [None, None, "yes", None],
        "flag": [0, 0, 1, 1],
    }).to_csv(path, index=False)
    workspace = _workspace_with_filter(path)
    response = dispatch_local_investigation(
        workspace,
        "Filtreyi flag kolonuyla karşılaştırabilir misin?",
        path,
    )
    assert response["status"] == "verified"
    assert response["evidence"]["total_missing"] == 3
    assert response["evidence"]["business_rule_confirmed"] is False
    assert response["evidence"]["sufficiency"]["status"] == "ready_for_interpretation"
    assert response["evidence"]["sufficiency"]["can_transform"] is False
    assert len(workspace.action_evidence_events) == 2
    assert dispatch_local_investigation(
        workspace, "flag kolonuyla tekrar karşılaştır", path
    )["status"] == "verified"
    assert len(workspace.action_evidence_events) == 2


def test_dispatcher_does_not_guess_a_column(tmp_path):
    path = tmp_path / "working.csv"
    pd.DataFrame({"optional": [None], "flag": [0]}).to_csv(path, index=False)
    workspace = _workspace_with_filter(path)
    result = dispatch_local_investigation(
        workspace, "Bundan sonra ne yapalım?", path
    )
    assert result["status"] == "needs_clarification"
    assert len(workspace.action_evidence_events) == 1


def test_dispatcher_rejects_stale_filter_evidence(tmp_path):
    path = tmp_path / "working.csv"
    pd.DataFrame({"optional": [None], "flag": [0]}).to_csv(path, index=False)
    workspace = _workspace_with_filter(path)
    pd.DataFrame({
        "optional": [None, "new"],
        "flag": [0, 1],
    }).to_csv(path, index=False)
    result = dispatch_local_investigation(workspace, "check flag", path)
    assert result["status"] == "stale"
    assert len(workspace.action_evidence_events) == 1


def test_dispatcher_without_working_data_does_not_fail(tmp_path):
    workspace = SimpleNamespace(action_evidence_events=[])
    assert dispatch_local_investigation(
        workspace, "hello", tmp_path / "none.csv"
    )["status"] == "unavailable"


def test_explicit_pair_runs_without_prior_preview_filter(tmp_path):
    path = tmp_path / "working.csv"
    pd.DataFrame({
        "CANCELLATION_REASON": [None, "A", None, None],
        "CANCELLED": [0, 1, 0, 1],
    }).to_csv(path, index=False)
    workspace = SimpleNamespace(action_evidence_events=[])
    message = (
        "CANCELLATION_REASON sütunundaki eksik değerlerin "
        "CANCELLED ile ilişkisini Local Engine üzerinden incele."
    )
    response = dispatch_local_investigation(workspace, message, path)
    assert response["status"] == "verified"
    assert response["evidence"]["total_missing"] == 3
    assert response["evidence"]["sufficiency"]["status"] == "ready_for_interpretation"
    assert len(workspace.action_evidence_events) == 1


def test_explicit_pair_can_recalculate_after_stale_preview(tmp_path):
    path = tmp_path / "working.csv"
    pd.DataFrame({
        "CANCELLATION_REASON": [None], "CANCELLED": [0],
    }).to_csv(path, index=False)
    workspace = SimpleNamespace(action_evidence_events=[])
    stat = path.stat()
    record_action_evidence(
        workspace,
        action="preview_investigation",
        dataset="source",
        parameters={
            "filters": [{"column": "CANCELLATION_REASON", "operator": "is_missing"}],
        },
        result={"total_rows": 1, "matching_rows": 1},
        data_version=f"{stat.st_size}:{stat.st_mtime_ns}",
    )
    response = dispatch_local_investigation(
        workspace,
        "CANCELLATION_REASON sütunundaki eksik değerlerin CANCELLED ile ilişkisini incele",
        path,
    )
    assert response["status"] == "verified"
    assert response["evidence"]["total_rows"] == 1


def test_explicit_pair_rejects_ambiguous_target(tmp_path):
    path = tmp_path / "working.csv"
    pd.DataFrame({"first": [None], "second": [None]}).to_csv(path, index=False)
    workspace = SimpleNamespace(action_evidence_events=[])
    result = dispatch_local_investigation(
        workspace, "first ve second eksik değer ilişkisini incele", path
    )
    assert result["status"] == "needs_clarification"
    assert not workspace.action_evidence_events
