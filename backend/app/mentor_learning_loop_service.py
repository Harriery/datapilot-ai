from __future__ import annotations

import json
import os
import uuid

from openai import OpenAI

import backend.app.database as database

from backend.app.ai_usage_guard import (
    guarded_responses_parse,
)
from backend.app.models import (
    DataQualityFinding,
    LearningEvidenceContext,
    LearningEvidenceDecision,
    PrepareLearningPhaseEvaluation,
    Workspace,
    WorkspaceLearningLoop,
)


client = OpenAI(
    api_key=os.getenv(
        "OPENAI_API_KEY"
    )
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


def evaluate_prepare_phase_response(
    *,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    response: str,
) -> PrepareLearningPhaseEvaluation:
    """
    Evaluate one learner-authored reasoning response.

    Only reasoning phases are reviewed from free text. Implement/validate
    remain gated by trusted Workbench transformation evidence.
    """
    if loop.current_phase not in {
        "observe",
        "reason",
        "decide",
        "explain",
    }:
        raise ValueError(
            "Current learning-loop phase is not a free-text reasoning phase."
        )

    payload = {
        "phase": loop.current_phase,
        "skill_name": loop.skill_name,
        "finding": finding.model_dump(),
        "learner_response": response,
    }

    phase_rubrics = {
        "observe": (
            "Success means the learner identifies a relevant observation "
            "from the supplied finding/evidence without inventing facts or "
            "jumping straight to a transformation."
        ),
        "reason": (
            "Success means the learner gives a plausible explanation or "
            "identifies evidence that would discriminate between possible "
            "causes. A bare fix without reasoning is not enough."
        ),
        "decide": (
            "Success means the learner chooses an action and justifies it "
            "from the available evidence. Automatic fill/drop rules without "
            "data-specific justification are insufficient."
        ),
        "explain": (
            "Success means the learner can explain what was changed, why the "
            "choice was appropriate, and how the trusted validation supports "
            "the result. Use trusted_validation from the loop when present."
        ),
    }

    instructions = f"""
    You evaluate one step in an adaptive Data Engineering learning loop.

    Current phase: {loop.current_phase}
    Skill: {loop.skill_name}

    Rubric:
    {phase_rubrics[loop.current_phase]}

    Rules:
    - Evaluate only the learner_response.
    - Finding is context, not learner evidence.
    - Do not reward confident wording by itself.
    - Do not invent dataset facts that are not supplied.
    - If the response is only a question/help request, set is_evidence=false.
    - If it is a genuine attempt, set is_evidence=true and success true/false.
    - evidence_type should normally be "explanation" for observe/reason/decide/explain.
    - misconception should be a short reusable concept label only when a clear
      misconception is visible; otherwise null.
    - note must be concise and specific.
    """

    response_obj = guarded_responses_parse(
        client,
        purpose="mentor_learning_phase",
        model=os.getenv(
            "AI_MENTOR_MODEL",
            "gpt-5-mini",
        ),
        input=json.dumps(
            {
                **payload,
                "trusted_validation":
                    loop.trusted_validation,
            },
            ensure_ascii=False,
            indent=2,
        ),
        instructions=instructions,
        text_format=PrepareLearningPhaseEvaluation,
    )

    evaluation = response_obj.output_parsed

    if evaluation.is_evidence:
        if (
            evaluation.success is None
            or evaluation.evidence_type is None
        ):
            raise ValueError(
                "Prepare phase evaluation is missing required evidence fields."
            )

    return evaluation


def record_prepare_phase_evidence(
    *,
    learner_id: str,
    workspace_id: str,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    assistance_level: str,
    evaluation: PrepareLearningPhaseEvaluation,
) -> LearningEvidenceDecision:
    evidence = LearningEvidenceDecision(
        is_evidence=evaluation.is_evidence,
        evidence_type=evaluation.evidence_type,
        success=evaluation.success,
        note=evaluation.note,
    )

    if not evidence.is_evidence:
        return evidence

    context = LearningEvidenceContext(
        workspace_id=workspace_id,
        stage="prepare",
        learning_phase=loop.current_phase,
        task_type=finding.issue_type,
        target_type=loop.target_type,
        target_name=loop.target_name,
        user_authored=True,
        deterministic_validation=False,
        misconception=evaluation.misconception,
        metadata={
            "finding_index": loop.finding_index,
            "loop_id": loop.loop_id,
        },
    )

    database.record_learning_evidence(
        learner_id=learner_id,
        skill_name=loop.skill_name,
        assistance_level=assistance_level,
        success=bool(evidence.success),
        evidence_type=str(evidence.evidence_type),
        note=evidence.note,
        session_id=None,
        context=context.model_dump(
            exclude_none=True,
        ),
    )

    return evidence


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


def record_trusted_prepare_validation_evidence(
    *,
    learner_id: str,
    workspace_id: str,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    assistance_level: str,
    success: bool,
    validation_summary: dict,
) -> LearningEvidenceDecision:
    evidence = LearningEvidenceDecision(
        is_evidence=True,
        evidence_type="application",
        success=success,
        note=(
            "Trusted Workbench validation confirmed the learner's "
            "transformation."
            if success
            else
            "Trusted Workbench validation did not confirm the learner's "
            "transformation."
        ),
    )

    context = LearningEvidenceContext(
        workspace_id=workspace_id,
        stage="prepare",
        learning_phase="validate",
        task_type=finding.issue_type,
        target_type=loop.target_type,
        target_name=loop.target_name,
        user_authored=True,
        deterministic_validation=True,
        metadata={
            "finding_index": loop.finding_index,
            "loop_id": loop.loop_id,
            "validated_phases": [
                "implement",
                "validate",
            ],
            **validation_summary,
        },
    )

    database.record_learning_evidence(
        learner_id=learner_id,
        skill_name=loop.skill_name,
        assistance_level=assistance_level,
        success=success,
        evidence_type="application",
        note=evidence.note,
        session_id=None,
        context=context.model_dump(
            exclude_none=True,
        ),
    )

    return evidence


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

    loop.trusted_validation = {
        "success": True,
        "finding_type": finding.issue_type,
        "target_name": finding.column,
    }

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
