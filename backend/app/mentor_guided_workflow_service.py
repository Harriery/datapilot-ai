from __future__ import annotations

from backend.app.mentor_supervisor_service import (
    select_pattern_comparison_column,
)
from backend.app.models import (
    DataQualityFinding,
    WorkspaceLearningLoop,
)


WORKFLOW_STATES = (
    "OBSERVE_SCOPE",
    "NEED_PATTERN_INVESTIGATION",
    "NEED_SUBSET_RESULT",
    "NEED_BASELINE_RESULT",
    "NEED_COMPARISON_INTERPRETATION",
    "READY_FOR_DECISION",
    "NEED_IMPLEMENTATION",
    "NEED_VALIDATION",
    "NEED_EXPLANATION",
    "COMPLETE",
    "NEED_REASONING_EVIDENCE",
)


def _investigation(
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
) -> dict | None:
    value = loop.active_investigation
    if not isinstance(value, dict):
        return None
    if not value:
        return None
    if (
        value.get("kind")
        != "missingness_pattern_frequency"
    ):
        return None
    if (
        value.get("target_column")
        != finding.column
    ):
        return None
    return value


def _ensure_missing_investigation(
    *,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    profile: dict,
) -> dict | None:
    existing = _investigation(
        loop,
        finding,
    )
    if existing is not None:
        return existing

    comparison = (
        select_pattern_comparison_column(
            profile=profile,
            target_name=finding.column,
        )
    )

    if comparison is None:
        return None

    loop.active_investigation = {
        "kind":
            "missingness_pattern_frequency",
        "target_column":
            finding.column,
        "comparison_column":
            comparison,
        "step":
            "subset_frequency",
        "subset_output":
            None,
        "baseline_output":
            None,
        "last_processed_observation_id":
            None,
    }
    return loop.active_investigation


def _consume_execution_observation(
    *,
    loop: WorkspaceLearningLoop,
    investigation: dict | None,
    diagnosis: dict | None,
) -> None:
    if (
        not isinstance(investigation, dict)
        or not isinstance(diagnosis, dict)
    ):
        return

    observation_id = diagnosis.get(
        "observation_id"
    )
    if not observation_id:
        return

    if (
        investigation.get(
            "last_processed_observation_id"
        )
        == observation_id
    ):
        return

    issue_code = diagnosis.get(
        "issue_code"
    )

    if (
        issue_code
        == "missing_scoped_frequency_check"
    ):
        investigation["subset_output"] = (
            diagnosis.get("output")
        )
        investigation["step"] = (
            "baseline_frequency"
        )
        investigation[
            "last_processed_observation_id"
        ] = observation_id
        return

    if (
        issue_code
        == "baseline_frequency_check"
    ):
        investigation["baseline_output"] = (
            diagnosis.get("output")
        )
        investigation["step"] = "interpret"
        investigation[
            "last_processed_observation_id"
        ] = observation_id


def _phase_state(
    loop: WorkspaceLearningLoop,
) -> str:
    if loop.status == "completed":
        return "COMPLETE"

    mapping = {
        "observe": "OBSERVE_SCOPE",
        "decide": "READY_FOR_DECISION",
        "implement": "NEED_IMPLEMENTATION",
        "validate": "NEED_VALIDATION",
        "explain": "NEED_EXPLANATION",
        "completed": "COMPLETE",
    }
    return mapping.get(
        loop.current_phase,
        "NEED_REASONING_EVIDENCE",
    )


def _missing_reason_state(
    *,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    profile: dict,
    diagnosis: dict | None,
) -> str:
    investigation = (
        _ensure_missing_investigation(
            loop=loop,
            finding=finding,
            profile=profile,
        )
    )

    _consume_execution_observation(
        loop=loop,
        investigation=investigation,
        diagnosis=diagnosis,
    )

    if investigation is None:
        return "NEED_PATTERN_INVESTIGATION"

    if not investigation.get(
        "subset_output"
    ):
        investigation["step"] = (
            "subset_frequency"
        )
        return "NEED_SUBSET_RESULT"

    if not investigation.get(
        "baseline_output"
    ):
        investigation["step"] = (
            "baseline_frequency"
        )
        return "NEED_BASELINE_RESULT"

    investigation["step"] = "interpret"
    return "NEED_COMPARISON_INTERPRETATION"


def resolve_guided_workflow_state(
    *,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    profile: dict,
    live_state: dict,
    execution_diagnosis: dict | None,
) -> dict:
    """
    Resolve the guided-learning workflow from trusted state.

    The learner message is deliberately absent from this API. Messages can
    change how the Mentor teaches the current state, but cannot select the
    technical state or silently change the investigation target.
    """
    semantic_state = _phase_state(loop)

    if loop.current_phase == "reason":
        if finding.issue_type == "missing_values":
            semantic_state = (
                _missing_reason_state(
                    loop=loop,
                    finding=finding,
                    profile=profile,
                    diagnosis=(
                        execution_diagnosis
                    ),
                )
            )
        else:
            semantic_state = (
                "NEED_REASONING_EVIDENCE"
            )

    blocker = None
    if isinstance(
        execution_diagnosis,
        dict,
    ):
        status = execution_diagnosis.get(
            "status"
        )
        issue_code = (
            execution_diagnosis.get(
                "issue_code"
            )
        )

        if status == "error":
            blocker = {
                "kind":
                    "execution_error",
                "issue_code":
                    issue_code,
            }
        elif issue_code in {
            "working_vs_raw_confusion",
            "investigation_target_mismatch",
        }:
            blocker = {
                "kind":
                    "task_alignment",
                "issue_code":
                    issue_code,
            }
        elif status in {
            "premature_action",
            "logic_mismatch",
            "off_task",
        }:
            blocker = {
                "kind":
                    "task_alignment",
                "issue_code":
                    issue_code,
            }

    investigation = _investigation(
        loop,
        finding,
    )

    snapshot = {
        "version": "state-machine-v1",
        "state": semantic_state,
        "phase": loop.current_phase,
        "issue_type": finding.issue_type,
        "target_name": finding.column,
        "investigation": (
            dict(investigation)
            if isinstance(
                investigation,
                dict,
            )
            else {}
        ),
        "blocker": blocker,
        "live": {
            "active_prepare_stage":
                live_state.get(
                    "active_prepare_stage"
                ),
            "workbench_view":
                live_state.get(
                    "workbench_view"
                ),
            "selected_notebook":
                live_state.get(
                    "selected_notebook"
                ),
            "notebook_count":
                live_state.get(
                    "notebook_count",
                    0,
                ),
        },
    }

    loop.workflow_state = semantic_state

    return snapshot
