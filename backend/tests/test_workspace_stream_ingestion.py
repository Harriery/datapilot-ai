import io
import os
from uuid import uuid4

import pytest

from backend.app import workspace_data_service as service


def test_stream_retries_transient_windows_permission_error(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "WORKSPACE_DATA_ROOT", tmp_path)
    workspace_id = str(uuid4())
    target = tmp_path / workspace_id / "source.csv"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"previous")
    real_replace = os.replace
    calls = 0

    def intermittent_lock(src, dst):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise PermissionError("temporarily locked")
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", intermittent_lock)
    monkeypatch.setattr("time.sleep", lambda _: None)
    count = service.save_workspace_dataset_stream(workspace_id, io.BytesIO(b"new data"), chunk_size=3)
    assert count == 8
    assert calls == 2
    assert target.read_bytes() == b"new data"
    assert not list(target.parent.glob("*.tmp.csv"))


def test_stream_preserves_existing_source_if_lock_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "WORKSPACE_DATA_ROOT", tmp_path)
    workspace_id = str(uuid4())
    target = tmp_path / workspace_id / "source.csv"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"previous")

    def locked(src, dst):
        raise PermissionError("locked")

    monkeypatch.setattr(os, "replace", locked)
    monkeypatch.setattr("time.sleep", lambda _: None)
    with pytest.raises(PermissionError, match="previous source.csv was preserved"):
        service.save_workspace_dataset_stream(workspace_id, io.BytesIO(b"new data"))
    assert target.read_bytes() == b"previous"
    assert not list(target.parent.glob("*.tmp.csv"))
