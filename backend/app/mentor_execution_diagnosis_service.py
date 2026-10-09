from __future__ import annotations

import re

from backend.app.models import (
    DataQualityFinding,
    WorkspaceLearningLoop,
)


def _selected_notebook_state(
    ui_context: dict | None,
) -> dict:
    if not isinstance(ui_context, dict):
        return {}

    value = ui_context.get(
        "selected_notebook_state"
    )

    return value if isinstance(value, dict) else {}


def diagnose_notebook_execution(
    *,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    ui_context: dict | None,
) -> dict | None:
    """
    Deterministic diagnosis of the latest visible notebook execution.
    This detects execution, dataset-context and obvious task-alignment problems.
    """
    state = _selected_notebook_state(ui_context)

    latest = state.get("latest_cell")
    if not isinstance(latest, dict):
        return None

    code = latest.get("code")
    execution = latest.get("last_execution")

    if not isinstance(code, str) or not isinstance(execution, dict):
        return None

    executed_at = execution.get("executed_at")
    cell_id = latest.get("cell_id")
    notebook_id = state.get("notebook_id")

    observation_id = ":".join(
        str(item or "")
        for item in (
            notebook_id,
            cell_id,
            executed_at,
        )
    )

    output = str(execution.get("output") or "")
    success = bool(execution.get("success"))
    normalized = code.casefold()
    target = (finding.column or "").casefold()

    base = {
        "observation_id": observation_id,
        "notebook_id": notebook_id,
        "cell_id": cell_id,
        "executed_at": executed_at,
        "dataset_kind": state.get("dataset_kind"),
        "code": code[:4000],
        "output": output[:1200],
    }

    if not success:
        error_kind = "execution_error"

        for candidate in (
            "SyntaxError",
            "NameError",
            "KeyError",
            "TypeError",
            "ValueError",
            "AttributeError",
        ):
            if candidate.casefold() in output.casefold():
                error_kind = candidate
                break

        return {
            **base,
            "status": "error",
            "issue_code": error_kind,
            "misconception": "code_execution_error",
            "message": "The latest notebook cell did not execute successfully.",
            "practice_tags": ["python_debugging"],
        }

    if (
        finding.issue_type == "missing_values"
        and loop.current_phase in {"observe", "reason"}
    ):
        if state.get("dataset_kind") == "working":
            return {
                **base,
                "status": "wrong_context",
                "issue_code": "working_vs_raw_confusion",
                "misconception": "dataset_context_confusion",
                "message": (
                    "The code ran on the working dataset while the task is "
                    "investigating original missing rows."
                ),
                "practice_tags": ["dataset_context", "null_analysis"],
            }

        if any(token in normalized for token in ("fillna(", "dropna(")):
            return {
                **base,
                "status": "premature_action",
                "issue_code": "premature_missing_value_treatment",
                "misconception": "premature_transformation",
                "message": (
                    "The code changes missing values before the reasoning "
                    "phase has established an evidence-based treatment."
                ),
                "practice_tags": ["null_analysis", "reason_before_transform"],
            }

        investigation = (
            loop.active_investigation
            if isinstance(loop.active_investigation, dict)
            else {}
        )
        comparison = str(
            investigation.get("comparison_column")
            or ""
        ).casefold()
        investigation_step = investigation.get("step")

        if "value_counts(" in normalized and comparison:
            if comparison not in normalized:
                return {
                    **base,
                    "status": "logic_mismatch",
                    "issue_code": "investigation_target_mismatch",
                    "misconception": "investigation_target_drift",
                    "message": (
                        "The code switched away from the comparison column "
                        f"locked for this investigation ({investigation.get('comparison_column')})."
                    ),
                    "practice_tags": ["task_context", "null_analysis"],
                }

            has_missing_scope = (
                "isna(" in normalized
                or "isnull(" in normalized
                or ".isna()" in normalized
                or ".isnull()" in normalized
            )

            if investigation_step == "baseline_frequency":
                if has_missing_scope:
                    return {
                        **base,
                        "status": "logic_mismatch",
                        "issue_code": "baseline_still_missing_scoped",
                        "misconception": "filter_scope_confusion",
                        "message": (
                            "The baseline step must use the overall raw dataset, "
                            "not only the missing-value subset."
                        ),
                        "practice_tags": ["pandas_filtering", "null_analysis"],
                    }

                return {
                    **base,
                    "status": "aligned_success",
                    "issue_code": "baseline_frequency_check",
                    "misconception": None,
                    "message": (
                        "The overall comparison-column distribution was calculated "
                        "for the baseline step."
                    ),
                    "practice_tags": ["pandas_filtering", "null_analysis"],
                }

            if not has_missing_scope:
                return {
                    **base,
                    "status": "logic_mismatch",
                    "issue_code": "frequency_without_missing_scope",
                    "misconception": "filter_scope_confusion",
                    "message": (
                        "value_counts() is valid, but it is not scoped to the "
                        "rows where the target column is missing."
                    ),
                    "practice_tags": ["pandas_filtering", "null_analysis"],
                }

            if target and target not in normalized:
                return {
                    **base,
                    "status": "off_task",
                    "issue_code": "target_not_referenced",
                    "misconception": "task_context_mismatch",
                    "message": (
                        "The missing-subset calculation does not reference the "
                        f"target column ({finding.column})."
                    ),
                    "practice_tags": ["task_context"],
                }

            return {
                **base,
                "status": "aligned_success",
                "issue_code": "missing_scoped_frequency_check",
                "misconception": None,
                "message": (
                    "The code scopes to missing rows and performs the locked "
                    "comparison-column frequency check."
                ),
                "practice_tags": ["pandas_filtering", "null_analysis"],
            }

        if target and target not in normalized:
            return {
                **base,
                "status": "off_task",
                "issue_code": "target_not_referenced",
                "misconception": "task_context_mismatch",
                "message": (
                    "The latest code does not reference the current target "
                    f"column ({finding.column})."
                ),
                "practice_tags": ["task_context"],
            }

        if "value_counts(" in normalized:
            has_missing_scope = (
                "isna(" in normalized
                or "isnull(" in normalized
                or ".isna()" in normalized
                or ".isnull()" in normalized
            )

            if not has_missing_scope:
                return {
                    **base,
                    "status": "logic_mismatch",
                    "issue_code": "frequency_without_missing_scope",
                    "misconception": "filter_scope_confusion",
                    "message": (
                        "value_counts() is valid, but it is not scoped to the "
                        "rows where the target column is missing."
                    ),
                    "practice_tags": ["pandas_filtering", "null_analysis"],
                }

            return {
                **base,
                "status": "aligned_success",
                "issue_code": "missing_scoped_frequency_check",
                "misconception": None,
                "message": (
                    "The code scopes to missing rows and performs a frequency "
                    "check, aligned with the current reasoning task."
                ),
                "practice_tags": ["pandas_filtering", "null_analysis"],
            }

    if re.search(r"\bdf\b", normalized):
        return {
            **base,
            "status": "executed",
            "issue_code": "execution_observed",
            "misconception": None,
            "message": "The latest notebook code executed; task alignment still requires reasoning.",
            "practice_tags": [],
        }

    return None



def diagnose_generic_notebook_execution(
    notebook_state: dict | None,
) -> dict | None:
    """
    Generic trusted execution observation for normal Mentor Chat.
    It can diagnose runtime/syntax failures without pretending to know the
    semantic task. Task-specific alignment remains in Guided Learning.
    """
    if not isinstance(notebook_state, dict):
        return None

    latest = notebook_state.get("latest_cell")
    if not isinstance(latest, dict):
        return None

    code = latest.get("code")
    execution = latest.get("last_execution")

    if not isinstance(code, str) or not isinstance(execution, dict):
        return None

    output = str(execution.get("output") or "")
    success = bool(execution.get("success"))
    executed_at = execution.get("executed_at")
    cell_id = latest.get("cell_id")
    notebook_id = notebook_state.get("notebook_id")

    observation_id = ":".join(
        str(item or "")
        for item in (notebook_id, cell_id, executed_at)
    )

    base = {
        "observation_id": observation_id,
        "notebook_id": notebook_id,
        "cell_id": cell_id,
        "executed_at": executed_at,
        "dataset_kind": notebook_state.get("dataset_kind"),
        "code": code[:4000],
        "output": output[:1200],
    }

    if not success:
        error_kind = "execution_error"
        for candidate in (
            "SyntaxError",
            "NameError",
            "KeyError",
            "TypeError",
            "ValueError",
            "AttributeError",
        ):
            if candidate.casefold() in output.casefold():
                error_kind = candidate
                break

        return {
            **base,
            "status": "error",
            "issue_code": error_kind,
            "misconception": "code_execution_error",
            "message": "The latest selected notebook cell failed to execute.",
            "practice_tags": ["python_debugging"],
        }

    return {
        **base,
        "status": "executed",
        "issue_code": "execution_observed",
        "misconception": None,
        "message": (
            "The latest selected notebook cell executed successfully. "
            "Execution success alone does not prove task correctness."
        ),
        "practice_tags": [],
    }
