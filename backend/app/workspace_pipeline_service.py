import pandas as pd

from backend.app.models import (
    WorkspacePipelineAction,
    WorkspaceWorkbenchOperation,
)


def _require_column(
    df: pd.DataFrame,
    column: str,
) -> None:
    if column not in df.columns:
        raise ValueError(
            f"Pipeline column bulunamadı: {column}"
        )


def apply_pipeline_action(
    df: pd.DataFrame,
    action: WorkspacePipelineAction,
) -> pd.DataFrame:
    result = df.copy()

    _require_column(
        result,
        action.column,
    )

    if action.action == "rename":
        if not action.new_name:
            raise ValueError(
                "Rename action için new_name gerekli."
            )

        if (
            action.new_name
            in result.columns
            and action.new_name
            != action.column
        ):
            raise ValueError(
                (
                    "Rename hedef column zaten mevcut: "
                    f"{action.new_name}"
                )
            )

        return result.rename(
            columns={
                action.column:
                    action.new_name
            }
        )

    if action.action == "remove":
        if len(result.columns) <= 1:
            raise ValueError(
                "Pipeline dataset içindeki son column'u silemez."
            )

        return result.drop(
            columns=[
                action.column
            ]
        )

    if action.action == "change_type":
        if action.data_type is None:
            raise ValueError(
                "Change type action için data_type gerekli."
            )

        if action.data_type == "string":
            result[action.column] = (
                result[action.column]
                .astype("string")
            )

        elif action.data_type == "integer":
            result[action.column] = (
                pd.to_numeric(
                    result[action.column],
                    errors="coerce",
                )
                .astype("Int64")
            )

        elif action.data_type == "float":
            result[action.column] = (
                pd.to_numeric(
                    result[action.column],
                    errors="coerce",
                )
            )

        elif action.data_type == "datetime":
            result[action.column] = (
                pd.to_datetime(
                    result[action.column],
                    errors="coerce",
                )
            )

        return result

    if action.action == "fill_missing":
        if action.fill_strategy is None:
            raise ValueError(
                "Fill action için fill_strategy gerekli."
            )

        series = result[
            action.column
        ]

        if action.fill_strategy == "value":
            fill_value = (
                action.fill_value
            )

        elif action.fill_strategy == "mean":
            fill_value = series.mean()

        elif action.fill_strategy == "median":
            fill_value = series.median()

        elif action.fill_strategy == "mode":
            mode = series.mode(
                dropna=True
            )

            if mode.empty:
                raise ValueError(
                    (
                        "Mode ile doldurmak için "
                        f"{action.column} column'unda "
                        "en az bir değer gerekli."
                    )
                )

            fill_value = mode.iloc[0]

        else:
            fill_value = 0

        result[action.column] = (
            series.fillna(
                fill_value
            )
        )

        return result

    if action.action == "replace_values":
        result[action.column] = (
            result[action.column]
            .replace(
                action.old_value,
                action.new_value,
            )
        )

        return result

    if action.action == "derived":
        if (
            not action.derived_name
            or not action.derived_operation
        ):
            raise ValueError(
                (
                    "Derived action için "
                    "derived_name ve "
                    "derived_operation gerekli."
                )
            )

        if (
            action.derived_name
            in result.columns
            and action.derived_name
            != action.column
        ):
            raise ValueError(
                (
                    "Derived hedef column zaten mevcut: "
                    f"{action.derived_name}"
                )
            )

        source = result[
            action.column
        ]

        if action.derived_operation == "copy":
            derived = source.copy()

        elif action.derived_operation == "uppercase":
            derived = (
                source
                .astype("string")
                .str.upper()
            )

        elif action.derived_operation == "lowercase":
            derived = (
                source
                .astype("string")
                .str.lower()
            )

        elif action.derived_operation == "add":
            if action.derived_value is None:
                raise ValueError(
                    "Derived add action için value gerekli."
                )

            derived = (
                source
                + action.derived_value
            )

        else:
            if action.derived_value is None:
                raise ValueError(
                    "Derived multiply action için value gerekli."
                )

            derived = (
                source
                * action.derived_value
            )

        result[
            action.derived_name
        ] = derived

        return result

    raise ValueError(
        (
            "Desteklenmeyen pipeline action: "
            f"{action.action}"
        )
    )


def apply_replayable_workbench_pipeline(
    source_df: pd.DataFrame,
    operations: list[
        WorkspaceWorkbenchOperation
    ],
) -> tuple[
    pd.DataFrame,
    list[str],
]:
    unfinished = [
        operation.title
        for operation in operations
        if operation.status != "completed"
    ]

    if unfinished:
        raise ValueError(
            (
                "Full dataset pipeline uygulanmadan önce "
                "tüm Workbench işlemleri tamamlanmalı: "
                + ", ".join(
                    unfinished
                )
            )
        )

    completed = [
        operation
        for operation in operations
        if operation.status == "completed"
    ]

    non_replayable = [
        operation.title
        for operation in completed
        if operation.pipeline_action is None
    ]

    if non_replayable:
        raise ValueError(
            (
                "Bu işlemler structured pipeline metadata "
                "içermediği için full dataset üzerinde "
                "güvenli replay edilemiyor: "
                + ", ".join(
                    non_replayable
                )
            )
        )

    result = source_df.copy()

    applied_operation_ids: list[
        str
    ] = []

    for operation in completed:
        if operation.pipeline_action is None:
            continue

        try:
            result = apply_pipeline_action(
                result,
                operation.pipeline_action,
            )

        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                (
                    f"Pipeline operation başarısız "
                    f"({operation.title}): {exc}"
                )
            ) from exc

        applied_operation_ids.append(
            operation.operation_id
        )

    return (
        result.reset_index(
            drop=True
        ),
        applied_operation_ids,
    )
