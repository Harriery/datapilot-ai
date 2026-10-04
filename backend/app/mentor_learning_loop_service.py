from __future__ import annotations

import uuid

from backend.app.models import (
    DataQualityFinding,
    LearningEvidenceDecision,
    Workspace,
    WorkspaceLearningLoop,
)


PREPARE_PHASES = (
    "observe",
    "reason",
    "decide",
    "implement",
    "validate",
    "explain",
)


def _phase_prompt(
    *,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
) -> str:
    target = (
        finding.column
        if finding.column
        else "the dataset"
    )

    prompts = {
        "observe": (
            f"Before changing anything, inspect {target}. "
            "What do you notice about this issue from the available evidence?"
        ),
        "reason": (
            "What could explain this issue, and what evidence would help you "
            "distinguish between the possible causes?"
        ),
        "decide": (
            "What action would you choose for this issue, and why is that "
            "decision appropriate for this data rather than an automatic fix?"
        ),
        "implement": (
            "Implement the smallest safe change in the Workbench or notebook. "
            "Write the code yourself, then run it."
        ),
        "validate": (
            "Validate the result against the original data. Confirm that the "
            "intended issue changed without introducing an unexpected data loss "
            "or schema problem."
        ),
        "explain": (
            "Explain in your own words what you changed, why you chose that "
            "approach, and what evidence shows the result is acceptable."
        ),
    }

    if loop.current_phase == "completed":
        return "This learning loop is complete."

    return prompts[loop.current_phase]


def start_or_resume_prepare_learning_loop(
    *,
    workspace: Workspace,
    finding_index: int,
    finding: DataQualityFinding,
    skill_name: str,
) -> tuple[WorkspaceLearningLoop, str]:
    for loop in workspace.learning_loops:
        if (
            loop.stage == "prepare"
            and loop.finding_index == finding_index
            and loop.status == "active"
        ):
            return (
                loop,
                _phase_prompt(
                    loop=loop,
                    finding=finding,
                ),
            )

    loop = WorkspaceLearningLoop(
        loop_id=str(uuid.uuid4()),
        stage="prepare",
        finding_index=finding_index,
        skill_name=skill_name,
        target_type=(
            "column"
            if finding.column
            else "dataset"
        ),
        target_name=finding.column,
        current_phase="observe",
        completed_phases=[],
        status="active",
    )

    workspace.learning_loops.append(loop)

    return (
        loop,
        _phase_prompt(
            loop=loop,
            finding=finding,
        ),
    )


def apply_learning_phase_review(
    *,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    evidence: LearningEvidenceDecision,
) -> tuple[WorkspaceLearningLoop, str]:
    if loop.status == "completed":
        return (
            loop,
            "This learning loop is already complete.",
        )

    if loop.current_phase in {
        "implement",
        "validate",
    }:
        raise ValueError(
            "Implement and validate phases must be advanced by trusted "
            "Workbench/transformation validation, not free-text review."
        )

    if (
        not evidence.is_evidence
        or evidence.success is not True
    ):
        return (
            loop,
            _phase_prompt(
                loop=loop,
                finding=finding,
            ),
        )

    current_phase = loop.current_phase

    if current_phase not in loop.completed_phases:
        loop.completed_phases.append(
            current_phase
        )

    current_index = PREPARE_PHASES.index(
        current_phase
    )

    next_phase = PREPARE_PHASES[
        current_index + 1
    ]

    loop.current_phase = next_phase

    return (
        loop,
        _phase_prompt(
            loop=loop,
            finding=finding,
        ),
    )


def apply_trusted_prepare_validation(
    *,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    success: bool,
) -> tuple[WorkspaceLearningLoop, str]:
    if loop.status == "completed":
        return (
            loop,
            "This learning loop is already complete.",
        )

    if loop.current_phase not in {
        "implement",
        "validate",
    }:
        raise ValueError(
            "Trusted transformation validation can only advance the "
            "implement/validate portion of the prepare learning loop."
        )

    if not success:
        loop.current_phase = "implement"

        return (
            loop,
            _phase_prompt(
                loop=loop,
                finding=finding,
            ),
        )

    for phase in (
        "implement",
        "validate",
    ):
        if phase not in loop.completed_phases:
            loop.completed_phases.append(
                phase
            )

    loop.current_phase = "explain"

    return (
        loop,
        _phase_prompt(
            loop=loop,
            finding=finding,
        ),
    )


def complete_prepare_learning_loop(
    *,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    evidence: LearningEvidenceDecision,
) -> tuple[WorkspaceLearningLoop, str]:
    if loop.current_phase != "explain":
        raise ValueError(
            "Prepare learning loop can only be completed from explain phase."
        )

    if (
        not evidence.is_evidence
        or evidence.success is not True
    ):
        return (
            loop,
            _phase_prompt(
                loop=loop,
                finding=finding,
            ),
        )

    if "explain" not in loop.completed_phases:
        loop.completed_phases.append(
            "explain"
        )

    loop.current_phase = "completed"
    loop.status = "completed"

    return (
        loop,
        "Learning loop complete. The decision, implementation, validation, "
        "and explanation are now recorded as separate learning evidence.",
    )
