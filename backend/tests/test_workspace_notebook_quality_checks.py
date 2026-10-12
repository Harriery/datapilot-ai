"""Notebook quality checks survive model and request round-trips."""

from backend.app.models import (
    WorkspaceNotebook,
    WorkspaceNotebookUpdateRequest,
    WorkspaceNotebookQualityCheck,
)


def _check():
    return {
        "check_id": "check-1",
        "cell_id": "cell-1",
        "section_title": "CANCELLATION_REASON",
        "title": "Cancelled flights with arrival time",
        "note": "Zero suspicious records in the notebook sample.",
        "code": '((df["CANCELLED"] == 1) & df["ARRIVAL_TIME"].notna()).sum()',
        "cell_type": "python",
        "result_summary": "np.int64(0)",
        "status": "sample_passed",
        "sample_row_count": 5000,
        "total_row_count": 10000,
        "dataset_kind": "working",
        "processed_dataset_id": None,
        "observed_at": "2026-10-12T11:00:00+00:00",
    }


def test_quality_check_saved_with_notebook_roundtrip():
    notebook = WorkspaceNotebook(
        notebook_id="nb-1",
        name="01_Data_Cleaning",
        cells=[],
        quality_checks=[_check()],
        created_at="2026-10-12T11:00:00+00:00",
        updated_at="2026-10-12T11:00:00+00:00",
    )
    restored = WorkspaceNotebook.model_validate(notebook.model_dump())
    assert len(restored.quality_checks) == 1
    assert restored.quality_checks[0].section_title == "CANCELLATION_REASON"
    assert restored.quality_checks[0].sample_row_count == 5000
    assert restored.quality_checks[0].status == "sample_passed"


def test_old_notebook_uses_empty_quality_checks():
    notebook = WorkspaceNotebook(
        notebook_id="nb-1",
        name="Legacy notebook",
        created_at="2026-10-12T11:00:00+00:00",
        updated_at="2026-10-12T11:00:00+00:00",
    )
    assert notebook.quality_checks == []


def test_update_request_accepts_scoped_check_and_rejects_bad_count():
    data = {
        "name": "01_Data_Cleaning",
        "cells": [],
        "quality_checks": [_check()],
    }
    request = WorkspaceNotebookUpdateRequest.model_validate(data)
    assert request.quality_checks[0].result_summary == "np.int64(0)"
    assert WorkspaceNotebookUpdateRequest(name="Legacy notebook").quality_checks == []
    from pydantic import ValidationError
    bad = _check()
    bad["sample_row_count"] = -1
    try:
        WorkspaceNotebookQualityCheck.model_validate(bad)
        assert False, "negative scope must be invalid"
    except ValidationError:
        pass
