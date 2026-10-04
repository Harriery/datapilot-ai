import pytest

from backend.app.models import (
    DataQualityFinding,
    LearningEvidenceDecision,
    Workspace,
)

from backend.app.mentor_learning_loop_service import (
    apply_learning_phase_review,
    apply_trusted_prepare_validation,
    complete_prepare_learning_loop,
    start_or_resume_prepare_learning_loop,
)


def make_workspace():
    return Workspace(
        workspace_id="workspace-001",
        learner_id="learner-001",
        title="Learning Loop Test",
        workspace_type="data_engineering",
    )


def make_finding():
    return DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="age contains missing values.",
        suggested_action="Inspect the missing values.",
    )


def successful_evidence(
    evidence_type="explanation",
):
    return LearningEvidenceDecision(
        is_evidence=True,
        evidence_type=evidence_type,
        success=True,
        note="Learner provided a valid response.",
    )


def test_start_prepare_learning_loop_persists_observe_phase():
    workspace = make_workspace()
    finding = make_finding()

    loop, prompt = start_or_resume_prepare_learning_loop(
        workspace=workspace,
        finding_index=0,
        finding=finding,
        skill_name="null_analysis",
    )

    assert loop.current_phase == "observe"
    assert loop.status == "active"
    assert loop.target_name == "age"
    assert workspace.learning_loops == [loop]
    assert "Before changing anything" in prompt


def test_start_prepare_learning_loop_resumes_existing_loop():
    workspace = make_workspace()
    finding = make_finding()

    first, _ = start_or_resume_prepare_learning_loop(
        workspace=workspace,
        finding_index=0,
        finding=finding,
        skill_name="null_analysis",
    )

    second, _ = start_or_resume_prepare_learning_loop(
        workspace=workspace,
        finding_index=0,
        finding=finding,
        skill_name="null_analysis",
    )

    assert first.loop_id == second.loop_id
    assert len(workspace.learning_loops) == 1


def test_prepare_learning_loop_advances_reasoning_phases_only_on_success():
    workspace = make_workspace()
    finding = make_finding()

    loop, _ = start_or_resume_prepare_learning_loop(
        workspace=workspace,
        finding_index=0,
        finding=finding,
        skill_name="null_analysis",
    )

    failed = LearningEvidenceDecision(
        is_evidence=True,
        evidence_type="explanation",
        success=False,
        note="Reasoning is incomplete.",
    )

    loop, _ = apply_learning_phase_review(
        loop=loop,
        finding=finding,
        evidence=failed,
    )

    assert loop.current_phase == "observe"
    assert loop.completed_phases == []

    loop, _ = apply_learning_phase_review(
        loop=loop,
        finding=finding,
        evidence=successful_evidence(),
    )

    assert loop.current_phase == "reason"
    assert loop.completed_phases == ["observe"]


def test_prepare_learning_loop_uses_trusted_validation_for_implementation():
    workspace = make_workspace()
    finding = make_finding()

    loop, _ = start_or_resume_prepare_learning_loop(
        workspace=workspace,
        finding_index=0,
        finding=finding,
        skill_name="null_analysis",
    )

    for expected_phase in (
        "reason",
        "decide",
        "implement",
    ):
        loop, _ = apply_learning_phase_review(
            loop=loop,
            finding=finding,
            evidence=successful_evidence(),
        )
        assert loop.current_phase == expected_phase

    with pytest.raises(ValueError):
        apply_learning_phase_review(
            loop=loop,
            finding=finding,
            evidence=successful_evidence(
                "application"
            ),
        )

    loop, prompt = apply_trusted_prepare_validation(
        loop=loop,
        finding=finding,
        success=True,
    )

    assert loop.current_phase == "explain"
    assert "implement" in loop.completed_phases
    assert "validate" in loop.completed_phases
    assert "Explain in your own words" in prompt

    loop, message = complete_prepare_learning_loop(
        loop=loop,
        finding=finding,
        evidence=successful_evidence(),
    )

    assert loop.current_phase == "completed"
    assert loop.status == "completed"
    assert "explain" in loop.completed_phases
    assert "Learning loop complete" in message
