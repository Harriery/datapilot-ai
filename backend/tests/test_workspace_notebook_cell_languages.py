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
