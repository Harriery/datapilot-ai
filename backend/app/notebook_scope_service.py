"""Cheap input identity: source file stat plus the selected sampling contract.

This is a freshness token, not a cryptographic proof of file contents.
"""
import hashlib
import json
from pathlib import Path
from backend.app.workspace_data_service import get_workspace_data_dir


def notebook_input_version(workspace_id, notebook, sample_size):
    if not workspace_id:
        return None
    try:
        root = get_workspace_data_dir(workspace_id)
        kind = notebook.dataset_kind
        if kind == "raw":
            path = root / "source.csv"
        elif kind == "working":
            path = root / "working.csv"
        else:
            dataset_id = notebook.processed_dataset_id
            if not dataset_id or Path(dataset_id).name != dataset_id:
                return None
            path = root / "processed_datasets" / f"{dataset_id}.csv"
        stat = path.stat()
        identity = [kind, getattr(notebook, "processed_dataset_id", None),
                    stat.st_size, stat.st_mtime_ns, sample_size, 42]
        return hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24]
    except (OSError, ValueError, TypeError):
        return None
