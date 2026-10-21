from backend.app.models import WorkspaceNotebookCell
from pydantic import ValidationError
import pytest


@pytest.mark.parametrize("language", ["python", "sql", "markdown"])
def test_notebook_cell_type_round_trip(language):
    cell = WorkspaceNotebookCell(cell_id="cell-1", code="SELECT 1", cell_type=language)
    restored = WorkspaceNotebookCell.model_validate_json(cell.model_dump_json())
    assert restored.cell_type == language


def test_existing_notebook_cell_defaults_to_python():
    cell = WorkspaceNotebookCell.model_validate({
        "cell_id": "old-cell",
        "code": "df.head()",
    })
    assert cell.cell_type == "python"


def test_notebook_cell_rejects_unknown_language():
    with pytest.raises(ValidationError):
        WorkspaceNotebookCell(cell_id="bad", code="abc", cell_type="javascript")


def test_notebook_update_discards_prior_execution_when_code_changes(tmp_path):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    import backend.app.database as database

    database.DATABASE_PATH = tmp_path / "notebook-provenance.db"
    database.init_db()
    database.insert_learner_profile(
        learner_id="provenance-test", answer_length="concise",
        learning_style="guided", code_support="medium",
    )
    client = TestClient(app)
    created = client.post("/workspaces", json={
        "learner_id": "provenance-test", "title": "Notebook provenance",
        "workspace_type": "data_engineering",
    })
    assert created.status_code == 200, created.text
    workspace_id = created.json()["workspace_id"]
    url = f"/workspaces/provenance-test/{workspace_id}/notebooks"
    notebook_response = client.post(url, json={
        "name": "01_analysis", "dataset_kind": "raw",
    })
    assert notebook_response.status_code == 200, notebook_response.text
    notebook = notebook_response.json()
    notebook_id = notebook["notebook_id"]
    edit_url = f"{url}/{notebook_id}"
    original = notebook["cells"]
    assert original
    cell = {
        **original[0],
        "code": original[0]["code"],
        "last_execution": {
            "success": True, "expression_kind": "scalar",
            "output": "original output",
            "executed_at": "2026-10-12T10:00:00Z",
        },
    }
    payload = {
        "name": notebook["name"], "dataset_kind": "raw",
        "processed_dataset_id": None, "cells": [cell],
    }
    saved = client.put(edit_url, json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()["cells"][0]["last_execution"]["output"] == "original output"

    stale = {**cell, "code": "df.tail()"}
    changed = client.put(edit_url, json={**payload, "cells": [stale]})
    assert changed.status_code == 200, changed.text
    assert changed.json()["cells"][0]["code"] == "df.tail()"
    assert changed.json()["cells"][0]["last_execution"] is None


@pytest.mark.parametrize("change", ["code", "order", "delete", "section"])
def test_upstream_changes_invalidate_downstream_execution_evidence(tmp_path, monkeypatch, change):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    import backend.app.database as database
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "dependencies.db")
    database.init_db()
    database.insert_learner_profile(learner_id="dependencies", answer_length="concise", learning_style="guided", code_support="medium")
    client = TestClient(app)
    workspace = client.post("/workspaces", json={"learner_id": "dependencies", "title": "Dependencies", "workspace_type": "data_engineering"}).json()
    url = f'/workspaces/dependencies/{workspace["workspace_id"]}/notebooks'
    notebook = client.post(url, json={"name": "Analysis", "dataset_kind": "raw"}).json()
    url += "/" + notebook["notebook_id"]
    cells = [{"cell_id": str(i), "code": f"print({i})", "cell_type": "python"} for i in range(3)]
    first = client.put(url, json={"name": "Analysis", "dataset_kind": "raw", "cells": cells})
    assert first.status_code == 200, first.text
    for cell in cells:
        cell["last_execution"] = {"success": True, "output": cell["cell_id"], "executed_at": "2026-10-18"}
    saved = client.put(url, json={"name": "Analysis", "dataset_kind": "raw", "cells": cells})
    assert all(c["last_execution"] for c in saved.json()["cells"])
    if change == "code": cells[1]["code"] = "print(99)"
    elif change == "order": cells[1], cells[2] = cells[2], cells[1]
    elif change == "delete": cells.pop(1)
    else: cells[1]["section_title"] = "New label"
    updated = client.put(url, json={"name": "Analysis", "dataset_kind": "raw", "cells": cells})
    assert updated.status_code == 200, updated.text
    result = updated.json()["cells"]
    assert result[0]["last_execution"] is not None
    assert all((c["last_execution"] is not None) == (change == "section") for c in result[1:])
