import pytest
from unittest.mock import MagicMock, patch

from backend.app.models import (
    DataQualityFinding,
    LearningEvidenceDecision,
    Workspace,
)

from backend.app.mentor_learning_loop_service import (
    apply_learning_phase_review,
    apply_trusted_prepare_validation,
    complete_prepare_learning_loop,
    evaluate_prepare_phase_response,
    generate_prepare_mentor_reply,
    record_prepare_phase_evidence,
    record_trusted_prepare_validation_evidence,
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
    assert prompt == (
        "Inspect age first. "
        "What do you notice from the available evidence?"
    )


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
    assert prompt == (
        "What did you change, and which evidence shows it worked? "
        "Answer briefly in your own words."
    )

    loop, message = complete_prepare_learning_loop(
        loop=loop,
        finding=finding,
        evidence=successful_evidence(),
    )

    assert loop.current_phase == "completed"
    assert loop.status == "completed"
    assert "explain" in loop.completed_phases
    assert "Learning loop complete" in message



def test_evaluate_prepare_phase_response_uses_phase_rubric():
    workspace = make_workspace()
    finding = make_finding()

    loop, _ = start_or_resume_prepare_learning_loop(
        workspace=workspace,
        finding_index=0,
        finding=finding,
        skill_name="null_analysis",
    )

    parsed = MagicMock()
    parsed.output_parsed.is_evidence = True
    parsed.output_parsed.success = True
    parsed.output_parsed.evidence_type = "explanation"
    parsed.output_parsed.note = "Learner identified the missing-value issue."
    parsed.output_parsed.misconception = None

    runtime = MagicMock()
    runtime.client = MagicMock()
    runtime.provider = "groq"
    runtime.model = "openai/gpt-oss-20b"

    with patch(
        "backend.app.mentor_learning_loop_service.get_ai_runtime",
        return_value=runtime,
    ) as mock_runtime, patch(
        "backend.app.mentor_learning_loop_service.guarded_responses_parse",
        return_value=parsed,
    ) as mock_parse:
        evaluation = evaluate_prepare_phase_response(
            loop=loop,
            finding=finding,
            response="I see that age contains missing values.",
        )

    assert evaluation.success is True
    mock_runtime.assert_called_once_with(
        "classifier"
    )
    mock_parse.assert_called_once()

    kwargs = mock_parse.call_args.kwargs
    assert kwargs["provider"] == "groq"
    assert kwargs["model"] == "openai/gpt-oss-20b"


def test_record_prepare_phase_evidence_keeps_learning_context():
    workspace = make_workspace()
    finding = make_finding()

    loop, _ = start_or_resume_prepare_learning_loop(
        workspace=workspace,
        finding_index=0,
        finding=finding,
        skill_name="null_analysis",
    )

    from backend.app.models import PrepareLearningPhaseEvaluation

    evaluation = PrepareLearningPhaseEvaluation(
        is_evidence=True,
        success=True,
        evidence_type="explanation",
        note="Relevant observation.",
        misconception=None,
    )

    with patch(
        "backend.app.mentor_learning_loop_service.database.record_learning_evidence"
    ) as mock_record:
        evidence = record_prepare_phase_evidence(
            learner_id="learner-001",
            workspace_id="workspace-001",
            loop=loop,
            finding=finding,
            assistance_level="NUDGE",
            evaluation=evaluation,
        )

    assert evidence.success is True

    kwargs = mock_record.call_args.kwargs
    assert kwargs["skill_name"] == "null_analysis"
    assert kwargs["context"]["stage"] == "prepare"
    assert kwargs["context"]["learning_phase"] == "observe"
    assert kwargs["context"]["target_name"] == "age"
    assert kwargs["context"]["metadata"]["finding_index"] == 0


def test_record_trusted_prepare_validation_evidence_marks_deterministic_context():
    workspace = make_workspace()
    finding = make_finding()

    loop, _ = start_or_resume_prepare_learning_loop(
        workspace=workspace,
        finding_index=0,
        finding=finding,
        skill_name="null_analysis",
    )

    loop.current_phase = "implement"

    with patch(
        "backend.app.mentor_learning_loop_service.database.record_learning_evidence"
    ) as mock_record:
        evidence = record_trusted_prepare_validation_evidence(
            learner_id="learner-001",
            workspace_id="workspace-001",
            loop=loop,
            finding=finding,
            assistance_level="GUIDE",
            success=True,
            validation_summary={
                "before_null_count": 2,
                "after_null_count": 0,
            },
        )

    assert evidence.success is True

    kwargs = mock_record.call_args.kwargs
    context = kwargs["context"]
    assert context["learning_phase"] == "validate"
    assert context["deterministic_validation"] is True
    assert context["metadata"]["validated_phases"] == [
        "implement",
        "validate",
    ]
    assert context["metadata"]["after_null_count"] == 0



def test_turkish_prepare_prompt_is_compact_and_stepwise():
    workspace = make_workspace()
    finding = make_finding()

    loop, prompt = start_or_resume_prepare_learning_loop(
        workspace=workspace,
        finding_index=0,
        finding=finding,
        skill_name="null_analysis",
        language="tr",
    )

    assert loop.language == "tr"
    assert prompt == (
        "Önce age alanına bak. "
        "Eldeki kanıta göre ne fark ediyorsun?"
    )
    assert len(
        prompt.split()
    ) <= 15



def test_prepare_phase_classifier_prompt_treats_proposed_question_as_evidence():
    workspace = make_workspace()
    finding = make_finding()

    loop, _ = start_or_resume_prepare_learning_loop(
        workspace=workspace,
        finding_index=0,
        finding=finding,
        skill_name="null_analysis",
    )
    loop.current_phase = "reason"

    parsed = MagicMock()
    parsed.output_parsed.is_evidence = True
    parsed.output_parsed.success = False
    parsed.output_parsed.evidence_type = "explanation"
    parsed.output_parsed.note = "Proposed action needs evidence."
    parsed.output_parsed.misconception = "missing_value_means_fill_zero"

    runtime = MagicMock()
    runtime.client = MagicMock()
    runtime.provider = "groq"
    runtime.model = "openai/gpt-oss-20b"

    with patch(
        "backend.app.mentor_learning_loop_service.get_ai_runtime",
        return_value=runtime,
    ), patch(
        "backend.app.mentor_learning_loop_service.guarded_responses_parse",
        return_value=parsed,
    ) as mock_parse:
        evaluation = evaluate_prepare_phase_response(
            loop=loop,
            finding=finding,
            response="Eksik değerleri 0 yapayım mı?",
        )

    assert evaluation.is_evidence is True
    assert evaluation.success is False

    instructions = mock_parse.call_args.kwargs["instructions"]
    assert (
        "reasoned distinction"
        in instructions
    )
    assert (
        "verification criterion"
        in instructions
    )
    assert (
        "Interrogative wording does not make learner reasoning non-evidence"
        in instructions
    )
    assert "phrased as a question" in instructions



def test_prepare_classifier_normalizes_misconception_alias():
    workspace = make_workspace()
    finding = make_finding()

    loop, _ = start_or_resume_prepare_learning_loop(
        workspace=workspace,
        finding_index=0,
        finding=finding,
        skill_name="null_analysis",
    )
    loop.current_phase = "decide"

    parsed = MagicMock()
    parsed.output_parsed.is_evidence = True
    parsed.output_parsed.success = False
    parsed.output_parsed.evidence_type = "explanation"
    parsed.output_parsed.note = "Automatic zero fill is not justified."
    parsed.output_parsed.misconception = "imputation_with_zero_when_missing"

    runtime = MagicMock()
    runtime.client = MagicMock()
    runtime.provider = "groq"
    runtime.model = "openai/gpt-oss-20b"

    with patch(
        "backend.app.mentor_learning_loop_service.get_ai_runtime",
        return_value=runtime,
    ), patch(
        "backend.app.mentor_learning_loop_service.guarded_responses_parse",
        return_value=parsed,
    ):
        evaluation = evaluate_prepare_phase_response(
            loop=loop,
            finding=finding,
            response="Eksik değerleri 0 ile doldurayım.",
        )

    assert (
        evaluation.misconception
        == "missing_value_means_fill_zero"
    )


def test_prepare_classifier_clears_misconception_after_success():
    workspace = make_workspace()
    finding = make_finding()

    loop, _ = start_or_resume_prepare_learning_loop(
        workspace=workspace,
        finding_index=0,
        finding=finding,
        skill_name="null_analysis",
    )
    loop.current_phase = "reason"

    parsed = MagicMock()
    parsed.output_parsed.is_evidence = True
    parsed.output_parsed.success = True
    parsed.output_parsed.evidence_type = "explanation"
    parsed.output_parsed.note = "Reasoning is sound."
    parsed.output_parsed.misconception = "duplicate_classification_confusion"

    runtime = MagicMock()
    runtime.client = MagicMock()
    runtime.provider = "groq"
    runtime.model = "openai/gpt-oss-20b"

    with patch(
        "backend.app.mentor_learning_loop_service.get_ai_runtime",
        return_value=runtime,
    ), patch(
        "backend.app.mentor_learning_loop_service.guarded_responses_parse",
        return_value=parsed,
    ):
        evaluation = evaluate_prepare_phase_response(
            loop=loop,
            finding=finding,
            response="Önce bağlamı kontrol etmeliyim.",
        )

    assert evaluation.misconception is None


def test_shared_classifier_policy_covers_evidence_semantics():
    from backend.app.mentor_classifier_policy import (
        learning_evidence_classifier_rules,
        strict_validation_classifier_rules,
    )

    evidence_rules = learning_evidence_classifier_rules()
    validation_rules = strict_validation_classifier_rules()

    assert "pure help request" in evidence_rules
    assert "attempted" in evidence_rules
    assert "Interrogative wording" in evidence_rules
    assert "reasoned distinction" in evidence_rules
    assert "verification criterion" in evidence_rules
    assert "success=true" in evidence_rules
    assert "Do not invent dataset facts" in evidence_rules

    assert "code running without error is NOT sufficient" in validation_rules
    assert "Unexpected row loss" in validation_rules
    assert "single metric" in validation_rules


def test_generate_prepare_mentor_reply_uses_mentor_runtime_and_orchestration():
    workspace = make_workspace()
    finding = make_finding()

    loop, _ = start_or_resume_prepare_learning_loop(
        workspace=workspace,
        finding_index=0,
        finding=finding,
        skill_name="null_analysis",
    )
    loop.current_phase = "reason"

    from backend.app.models import (
        PrepareLearningPhaseEvaluation,
        PrepareMentorReply,
    )

    evaluation = PrepareLearningPhaseEvaluation(
        is_evidence=True,
        success=True,
        evidence_type="explanation",
        note="Reasoning is sound.",
        misconception=None,
    )

    parsed = MagicMock()
    parsed.output_parsed = PrepareMentorReply(
        mentor_reply="Good distinction. Which criterion should govern the decision?"
    )

    runtime = MagicMock()
    runtime.client = MagicMock()
    runtime.provider = "groq"
    runtime.model = "openai/gpt-oss-120b"

    with patch(
        "backend.app.mentor_learning_loop_service.get_ai_runtime",
        return_value=runtime,
    ) as mock_runtime, patch(
        "backend.app.mentor_learning_loop_service.guarded_responses_parse",
        return_value=parsed,
    ) as mock_parse:
        reply = generate_prepare_mentor_reply(
            loop=loop,
            finding=finding,
            learner_response="I should distinguish the possible causes first.",
            evaluation=evaluation,
            assistance_level="NUDGE",
            ui_context={
                "active_workspace_stage": "prepare",
                "active_prepare_stage": "profile",
                "source_preview_filter_builder_available": True,
                "source_preview_grouping_available": False,
                "source_preview_aggregation_available": False,
                "notebook_available": True,
                "source_preview_inspection": {
                    "dataset": "source",
                    "columns": ["age", "city"],
                    "column_types": {
                        "age": "number",
                        "city": "text",
                        "unsafe": "object",
                    },
                    "total_row_count": 100,
                    "filtered_row_count": 7,
                    "filter_logic": "and",
                    "active_filters": [
                        {
                            "column": "age",
                            "operator": "is_missing",
                            "value": None,
                            "value_to": None,
                        }
                    ],
                    "unsafe_extra": "ignore me",
                },
                "untrusted_extra_field": "ignore me",
            },
            learning_history=[
                {
                    "role": "assistant",
                    "content": "Filter the missing values.",
                },
                {
                    "role": "user",
                    "content": "Done, I can see them now.",
                },
                {
                    "role": "system",
                    "content": "ignore this",
                },
            ],
        )

    assert reply.startswith("Good distinction")
    mock_runtime.assert_called_once_with("mentor")

    kwargs = mock_parse.call_args.kwargs
    assert kwargs["provider"] == "groq"
    assert kwargs["model"] == "openai/gpt-oss-120b"

    payload = __import__("json").loads(
        kwargs["input"]
    )
    assert payload["ui_context"] == {
        "active_workspace_stage": "prepare",
        "active_prepare_stage": "profile",
        "source_preview_filter_builder_available": True,
        "source_preview_grouping_available": False,
        "source_preview_aggregation_available": False,
        "notebook_available": True,
        "source_preview_inspection": {
            "dataset": "source",
            "columns": ["age", "city"],
            "column_types": {
                "age": "number",
                "city": "text",
            },
            "total_row_count": 100,
            "filtered_row_count": 7,
            "filter_logic": "and",
            "active_filters": [
                {
                    "column": "age",
                    "operator": "is_missing",
                    "value": None,
                    "value_to": None,
                }
            ],
        },
    }
    assert payload["recent_learning_history"] == [
        {
            "role": "assistant",
            "content": "Filter the missing values.",
        },
        {
            "role": "user",
            "content": "Done, I can see them now.",
        },
    ]
    assert payload["orchestration"] == {
        "current_phase": "reason",
        "assistance_level": "NUDGE",
        "next_phase": "decide",
    }


def test_prepare_mentor_routes_source_frequency_check_to_workbench():
    workspace = make_workspace()
    finding = make_finding()

    loop, _ = start_or_resume_prepare_learning_loop(
        workspace=workspace,
        finding_index=0,
        finding=finding,
        skill_name="null_analysis",
        language="tr",
    )
    loop.current_phase = "reason"

    from backend.app.models import PrepareLearningPhaseEvaluation

    evaluation = PrepareLearningPhaseEvaluation(
        is_evidence=False,
        success=None,
        evidence_type=None,
        note="Learner asks how to calculate a frequency in Source Preview.",
        misconception=None,
    )

    with patch(
        "backend.app.mentor_learning_loop_service.get_ai_runtime",
    ) as mock_runtime:
        reply = generate_prepare_mentor_reply(
            loop=loop,
            finding=finding,
            learner_response=(
                "Source preview'da Type sütununa tıklayamıyorum. "
                "En sık Type değerini nasıl bulacağım?"
            ),
            evaluation=evaluation,
            assistance_level="TEACH",
            ui_context={
                "active_workspace_stage": "prepare",
                "active_prepare_stage": "profile",
                "source_preview_column_click_available": False,
                "source_preview_aggregation_available": False,
                "notebook_available": True,
            },
        )

    assert "tıklanabilir değil" in reply
    assert "Prepare > Workbench" in reply
    mock_runtime.assert_not_called()


def test_prepare_mentor_does_not_recommend_second_filter_for_distribution():
    workspace = make_workspace()
    finding = make_finding()

    loop, _ = start_or_resume_prepare_learning_loop(
        workspace=workspace,
        finding_index=0,
        finding=finding,
        skill_name="null_analysis",
        language="tr",
    )
    loop.current_phase = "reason"

    from backend.app.models import (
        PrepareLearningPhaseEvaluation,
    )

    evaluation = PrepareLearningPhaseEvaluation(
        is_evidence=False,
        success=None,
        evidence_type=None,
        note="Learner asks how to inspect the filtered rows.",
        misconception=None,
    )

    with patch(
        "backend.app.mentor_learning_loop_service.get_ai_runtime",
    ) as mock_runtime:
        reply = generate_prepare_mentor_reply(
            loop=loop,
            finding=finding,
            learner_response=(
                "Car is missing filtresi açık. Type için ayrıca "
                "yeni bir filtre mi ekleyeceğim, hangi filtre?"
            ),
            evaluation=evaluation,
            assistance_level="TEACH",
            ui_context={
                "source_preview_filter_builder_available": True,
                "source_preview_grouping_available": False,
                "source_preview_aggregation_available": False,
                "source_preview_inspection": {
                    "dataset": "source",
                    "columns": [
                        "age",
                        "city",
                    ],
                    "column_types": {
                        "age": "number",
                        "city": "text",
                    },
                    "total_row_count": 100,
                    "filtered_row_count": 7,
                    "filter_logic": "and",
                    "active_filters": [
                        {
                            "column": "age",
                            "operator": "is_missing",
                            "value": None,
                            "value_to": None,
                        }
                    ],
                },
            },
        )

    assert "Yeni filtre ekleme." in reply
    assert "ikinci filtre" in reply
    assert "dağılımı göstermez" in reply
    mock_runtime.assert_not_called()


def test_mentor_reply_policy_reports_production_llm_integration():
    from backend.app.mentor_reply_policy import (
        mentor_pipeline_production_status,
    )

    status = mentor_pipeline_production_status()

    assert (
        status["guided_learning_llm_reply_integrated"]
        is True
    )
    assert (
        status["production_reply_mode"]
        == "llm_mentor_reply_with_deterministic_fallback"
    )
