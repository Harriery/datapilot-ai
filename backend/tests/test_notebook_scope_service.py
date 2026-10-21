from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch
from backend.app.notebook_scope_service import notebook_input_version


def test_input_identity_changes_with_scope_and_source_replacement(tmp_path):
    workspace_id = str(uuid4())
    notebook = SimpleNamespace(dataset_kind="working", processed_dataset_id=None)
    path = tmp_path / "working.csv"
    path.write_text("v\n1\n")
    with patch("backend.app.notebook_scope_service.get_workspace_data_dir", return_value=tmp_path):
        original = notebook_input_version(workspace_id, notebook, 10000)
        assert original == notebook_input_version(workspace_id, notebook, 10000)
        assert original != notebook_input_version(workspace_id, notebook, 5000)
        path.write_text("v\n1\n2\n")
        assert original != notebook_input_version(workspace_id, notebook, 10000)
