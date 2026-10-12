"""Legacy notebook sections and explicit per-cell section membership."""

from backend.app.models import (
    WorkspaceNotebook,
    WorkspaceNotebookCell,
    WorkspaceNotebookUpdateRequest,
)


def test_legacy_notebook_section_mode_defaults_to_legacy():
    notebook = WorkspaceNotebook.model_validate({
        "notebook_id": "legacy",
        "name": "Earlier notebook",
        "cells": [
            {"cell_id": "a", "code": "print(1)", "section_title": "A"},
            {"cell_id": "b", "code": "print(2)"},
        ],
        "created_at": "2026-10-11",
        "updated_at": "2026-10-11",
    })
    assert notebook.section_mode == "legacy"
    assert [cell.section_title for cell in notebook.cells] == ["A", None]


def test_explicit_ungrouped_and_grouped_cells_round_trip():
    request = WorkspaceNotebookUpdateRequest(
        name="Flight notebook",
        section_mode="explicit",
        cells=[
            WorkspaceNotebookCell(cell_id="a", code="SELECT 1", cell_type="sql", section_title="CANCELLATION_REASON"),
            WorkspaceNotebookCell(cell_id="b", code="print(2)", section_title=None),
            WorkspaceNotebookCell(cell_id="c", code="# notes", cell_type="markdown", section_title="DENEME"),
        ],
    )
    restored = WorkspaceNotebookUpdateRequest.model_validate_json(request.model_dump_json())
    assert restored.section_mode == "explicit"
    assert [(cell.cell_id, cell.section_title, cell.cell_type) for cell in restored.cells] == [
        ("a", "CANCELLATION_REASON", "sql"),
        ("b", None, "python"),
        ("c", "DENEME", "markdown"),
    ]


def test_existing_update_payload_keeps_legacy_mode():
    request = WorkspaceNotebookUpdateRequest(name="Legacy", cells=[
        WorkspaceNotebookCell(cell_id="a", code="print(1)"),
    ])
    assert request.section_mode == "legacy"
