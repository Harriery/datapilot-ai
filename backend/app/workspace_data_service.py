from pathlib import Path
from uuid import UUID

import pandas as pd

from pathlib import Path
from uuid import UUID
from datetime import datetime, timezone
import json

import pandas as pd

from backend.app.models import (
    DataEngineeringTask,
    WorkspaceCheckpoint,
    WorkspaceWorkbenchOperation,
)

WORKSPACE_DATA_ROOT = Path(
    "data/workspaces"
)


def _get_workspace_data_dir(
    workspace_id: str,
) -> Path:
    # Path traversal gibi riskleri önlemek için
    # gerçekten UUID olduğundan emin oluyoruz.
    safe_workspace_id = str(
        UUID(workspace_id)
    )

    return (
        WORKSPACE_DATA_ROOT
        / safe_workspace_id
    )


def save_workspace_dataset(
    workspace_id: str,
    content: bytes,
) -> None:
    workspace_dir = (
        _get_workspace_data_dir(
            workspace_id
        )
    )

    workspace_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_path = (
        workspace_dir / "source.csv"
    )

    working_path = (
        workspace_dir / "working.csv"
    )

    # Original source.
    # Bundan sonraki transform işlemleri
    # bu dosyaya yazmayacak.
    source_path.write_bytes(content)

    # Junior'ın çalışacağı kopya.
    working_path.write_bytes(content)


def load_workspace_working_dataframe(
    workspace_id: str,
) -> pd.DataFrame:
    working_path = (
        _get_workspace_data_dir(
            workspace_id
        )
        / "working.csv"
    )

    if not working_path.exists():
        raise FileNotFoundError(
            "Workspace çalışma datası bulunamadı."
        )

    return pd.read_csv(
        working_path
    )

def load_workspace_source_dataframe(
    workspace_id: str,
) -> pd.DataFrame:
    source_path = (
        _get_workspace_data_dir(
            workspace_id
        )
        / "source.csv"
    )

    if not source_path.exists():
        raise FileNotFoundError(
            "Workspace source datası bulunamadı."
        )

    return pd.read_csv(
        source_path
    )

def dataframe_to_records(
    df: pd.DataFrame,
) -> list[dict]:
    safe_df = (
        df.astype(object).where(
            pd.notnull(df),
            None,
        )
    )

    return safe_df.to_dict(
        orient="records"
    )

def save_workspace_working_dataframe(
    workspace_id: str,
    df: pd.DataFrame,
) -> None:
    workspace_dir = (
        _get_workspace_data_dir(
            workspace_id
        )
    )

    workspace_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    working_path = (
        workspace_dir / "working.csv"
    )

    temporary_path = (
        workspace_dir / "working.tmp.csv"
    )

    # Önce geçici dosyaya yazıyoruz.
    # Yazma başarılı olursa working.csv ile değiştiriyoruz.
    df.to_csv(
        temporary_path,
        index=False,
    )

    temporary_path.replace(
        working_path
    )


def create_workspace_version(
    workspace_id: str,
    df: pd.DataFrame,
    task: DataEngineeringTask | None,
    checkpoint: WorkspaceCheckpoint,
    label: str,
    workbench_operations: (
        list[WorkspaceWorkbenchOperation] | None
    ) = None,
    workbench_active_operation_id: (
        str | None
    ) = None,
    operation_id: str | None = None,
    operation_title: str | None = None,
    operation_type: str | None = None,
    transformation_code: str | None = None,
    before_columns: list[str] | None = None,
    after_columns: list[str] | None = None,
) -> int:
    workspace_dir = (
        _get_workspace_data_dir(
            workspace_id
        )
    )

    versions_dir = (
        workspace_dir / "versions"
    )

    versions_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    existing_numbers: list[int] = []

    for path in versions_dir.glob(
        "version_*.json"
    ):
        try:
            number = int(
                path.stem.split("_")[1]
            )

            existing_numbers.append(
                number
            )

        except (
            ValueError,
            IndexError,
        ):
            continue

    version_number = (
        max(
            existing_numbers,
            default=0,
        )
        + 1
    )

    csv_path = versions_dir / (
        f"version_{version_number:03d}.csv"
    )

    metadata_path = versions_dir / (
        f"version_{version_number:03d}.json"
    )

    df.to_csv(
        csv_path,
        index=False,
    )

    operation_metadata = None

    if operation_id is not None:
        operation_metadata = {
            "operation_id":
                operation_id,

            "operation_title":
                operation_title,

            "operation_type":
                operation_type,

            "transformation_code":
                transformation_code,

            "before_columns":
                before_columns or [],

            "after_columns":
                after_columns or [],

            "schema_changed": (
                before_columns
                != after_columns
                if (
                    before_columns is not None
                    and after_columns is not None
                )
                else None
            ),
        }

    metadata = {
        "version_number":
            version_number,

        "label":
            label,

        "created_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "row_count":
            len(df),

        "task": (
            task.model_dump()
            if task is not None
            else None
        ),

        "checkpoint":
            checkpoint.model_dump(),

        "workbench_operations": (
            [
                operation.model_dump()
                for operation
                in workbench_operations
            ]
            if workbench_operations
            is not None
            else None
        ),

        "workbench_active_operation_id": (
            workbench_active_operation_id
        ),

        "operation":
            operation_metadata,
    }

    metadata_path.write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return version_number

def delete_workspace_version(
    workspace_id: str,
    version_number: int,
) -> None:
    versions_dir = (
        _get_workspace_data_dir(
            workspace_id
        )
        / "versions"
    )

    csv_path = versions_dir / (
        f"version_{version_number:03d}.csv"
    )

    metadata_path = versions_dir / (
        f"version_{version_number:03d}.json"
    )

    if csv_path.exists():
        csv_path.unlink()

    if metadata_path.exists():
        metadata_path.unlink()


def list_workspace_versions(
    workspace_id: str,
) -> list[dict]:
    versions_dir = (
        _get_workspace_data_dir(
            workspace_id
        )
        / "versions"
    )

    if not versions_dir.exists():
        return []

    versions: list[dict] = []

    for metadata_path in versions_dir.glob(
        "version_*.json"
    ):
        try:
            metadata = json.loads(
                metadata_path.read_text(
                    encoding="utf-8"
                )
            )

            operation = (
                metadata.get("operation")
                or {}
            )

            versions.append(
                {
                    "version_number":
                        metadata[
                            "version_number"
                        ],

                    "label":
                        metadata["label"],

                    "created_at":
                        metadata[
                            "created_at"
                        ],

                    "row_count":
                        metadata[
                            "row_count"
                        ],

                    "operation_id":
                        operation.get(
                            "operation_id"
                        ),

                    "operation_title":
                        operation.get(
                            "operation_title"
                        ),

                    "operation_type":
                        operation.get(
                            "operation_type"
                        ),

                    "transformation_code":
                        operation.get(
                            "transformation_code"
                        ),

                    "schema_changed":
                        operation.get(
                            "schema_changed"
                        ),
                }
            )

        except (
            OSError,
            json.JSONDecodeError,
            KeyError,
        ):
            continue

    versions.sort(
        key=lambda item:
            item["version_number"],
        reverse=True,
    )

    return versions

def load_workspace_version(
    workspace_id: str,
    version_number: int,
) -> tuple[
    pd.DataFrame,
    DataEngineeringTask | None,
    WorkspaceCheckpoint,
    list[WorkspaceWorkbenchOperation] | None,
    str | None,
]:
    if version_number < 1:
        raise ValueError(
            "Version number 1 veya daha büyük olmalı."
        )

    versions_dir = (
        _get_workspace_data_dir(
            workspace_id
        )
        / "versions"
    )

    csv_path = versions_dir / (
        f"version_{version_number:03d}.csv"
    )

    metadata_path = versions_dir / (
        f"version_{version_number:03d}.json"
    )

    if (
        not csv_path.exists()
        or not metadata_path.exists()
    ):
        raise FileNotFoundError(
            "Workspace version bulunamadı."
        )

    try:
        metadata = json.loads(
            metadata_path.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as exc:
        raise ValueError(
            "Workspace version metadata geçersiz."
        ) from exc

    df = pd.read_csv(
        csv_path
    )

    task_data = metadata.get(
        "task"
    )

    task = (
        DataEngineeringTask.model_validate(
            task_data
        )
        if task_data is not None
        else None
    )

    checkpoint = (
        WorkspaceCheckpoint.model_validate(
            metadata["checkpoint"]
        )
    )

    operations_data = metadata.get(
        "workbench_operations"
    )

    workbench_operations = (
        [
            WorkspaceWorkbenchOperation
            .model_validate(item)
            for item in operations_data
        ]
        if operations_data is not None
        else None
    )

    active_operation_id = metadata.get(
        "workbench_active_operation_id"
    )

    return (
        df,
        task,
        checkpoint,
        workbench_operations,
        active_operation_id,
    )