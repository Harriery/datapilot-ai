from pathlib import Path
from uuid import UUID

import pandas as pd


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