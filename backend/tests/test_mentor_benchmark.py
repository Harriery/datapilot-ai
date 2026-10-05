from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.benchmarks.mentor_benchmark_provider import (
    generate_benchmark_structured,
)
from backend.benchmarks.run_mentor_benchmark import (
    CandidateResponse,
    build_candidate_payload,
    build_benchmark_plan,
    build_orchestration_context,
    calculate_expected_matches,
    determine_orchestrated_assistance,
    determine_orchestrated_next_phase,
    load_suite,
    select_match_group,
    MODEL_OWNED_MATCH_FIELDS,
    ORCHESTRATION_DIAGNOSTIC_FIELDS,
)


def test_mentor_benchmark_suite_has_expected_coverage():
    suite = load_suite()

    scenarios = suite["scenarios"]

    assert suite["suite_id"] == "datapilot-mentor-v1"
    assert len(scenarios) == 30

    stages = {
        scenario["stage"]
        for scenario in scenarios
    }

    assert {
        "prepare",
        "data_model",
        "kpi",
        "analysis",
        "dashboard",
        "practice",
    }.issubset(
        stages
    )

    assert all(
        scenario["expected"][
            "required_behaviors"
        ]
        for scenario in scenarios
    )


def test_candidate_response_schema_contains_only_model_owned_fields():
    response = CandidateResponse(
        is_evidence=True,
        success=True,
        misconception=None,
        mentor_reply="Good observation. What pattern would you inspect next?",
    )

    assert response.is_evidence is True
    assert response.success is True
    assert "assistance_level" not in CandidateResponse.model_fields
    assert "next_phase" not in CandidateResponse.model_fields


def test_benchmark_suite_is_repository_local():
    path = Path(
        "backend/benchmarks/mentor_benchmark_v1.json"
    )

    assert path.exists()



def test_calculate_expected_matches_is_deterministic():
    suite = load_suite()

    scenario = next(
        item
        for item in suite["scenarios"]
        if item["id"]
        == "prepare_missing_observe_small_ratio"
    )

    candidate = CandidateResponse(
        is_evidence=True,
        success=True,
        misconception=None,
        mentor_reply=(
            "Doğru gözlem. Şimdi eksik değerlerin "
            "belirli bir örüntü gösterip göstermediğine bak."
        ),
    )

    matches = calculate_expected_matches(
        scenario=scenario,
        candidate=candidate,
    )

    assert matches == {
        "evidence_expected_match": True,
        "success_expected_match": True,
        "assistance_allowed_match": True,
        "next_phase_match": True,
        "misconception_match": True,
    }


def test_calculate_expected_matches_catches_wrong_misconception():
    suite = load_suite()

    scenario = next(
        item
        for item in suite["scenarios"]
        if item["id"]
        == "prepare_missing_decide_auto_fill_misconception"
    )

    candidate = CandidateResponse(
        is_evidence=True,
        success=False,
        misconception="different_label",
        mentor_reply="Önce 0 değerinin anlamını doğrula.",
    )

    matches = calculate_expected_matches(
        scenario=scenario,
        candidate=candidate,
    )

    assert matches["evidence_expected_match"] is True
    assert matches["success_expected_match"] is True
    assert matches["assistance_allowed_match"] is True
    assert matches["next_phase_match"] is True
    assert matches["misconception_match"] is False


def test_build_benchmark_plan_makes_no_network_calls():
    plan = build_benchmark_plan(
        suite_path=Path(
            "backend/benchmarks/mentor_benchmark_v1.json"
        ),
        provider="groq",
        candidate_model="openai/gpt-oss-120b",
        judge_provider="groq",
        judge_model="openai/gpt-oss-20b",
        scenario_limit=3,
    )

    assert plan["scenario_count"] == 3
    assert plan["network_calls"] is False
    assert len(plan["scenario_ids"]) == 3



def test_benchmark_provider_routes_groq_to_openai_compatible_adapter():
    with patch(
        "backend.benchmarks.mentor_benchmark_provider."
        "_generate_openai_compatible_structured",
        return_value=MagicMock(),
    ) as mock_generate:
        generate_benchmark_structured(
            provider="groq",
            model="openai/gpt-oss-120b",
            purpose="test",
            instructions="instructions",
            input_text="input",
            text_format=CandidateResponse,
        )

    kwargs = mock_generate.call_args.kwargs
    assert kwargs["provider"] == "groq"
    assert kwargs["model"] == "openai/gpt-oss-120b"


def test_benchmark_provider_routes_google_to_gemini_adapter():
    with patch(
        "backend.benchmarks.mentor_benchmark_provider."
        "_generate_gemini_structured",
        return_value=MagicMock(),
    ) as mock_generate:
        generate_benchmark_structured(
            provider="google",
            model="gemini-test-model",
            purpose="test",
            instructions="instructions",
            input_text="input",
            text_format=CandidateResponse,
        )

    kwargs = mock_generate.call_args.kwargs
    assert kwargs["model"] == "gemini-test-model"


def test_benchmark_provider_rejects_unknown_provider():
    import pytest

    from backend.app.ai_provider_service import (
        AIProviderConfigurationError,
    )

    with pytest.raises(
        AIProviderConfigurationError
    ):
        generate_benchmark_structured(
            provider="unknown",
            model="model",
            purpose="test",
            instructions="instructions",
            input_text="input",
            text_format=CandidateResponse,
        )



def test_benchmark_compact_threshold_is_twenty_words():
    source = Path(
        "backend/benchmarks/run_mentor_benchmark.py"
    ).read_text(
        encoding="utf-8"
    )

    assert "mentor_reply_word_count <= 20" in source
    assert "Give only ONE next small step." in source



def test_benchmark_marks_wrong_attempts_as_evidence_rule():
    from backend.benchmarks.run_mentor_benchmark import (
        build_candidate_instructions,
    )

    instructions = build_candidate_instructions()

    assert (
        "is_evidence=true and success=false"
        in instructions
    )
    assert (
        "genuine incorrect attempt"
        in instructions
    )



def test_candidate_payload_does_not_leak_expected_answer():
    suite = load_suite()

    scenario = suite["scenarios"][0]

    payload = build_candidate_payload(
        scenario
    )

    assert "expected" not in payload
    assert payload["learner_message"] == scenario["learner_message"]
    assert payload["workspace_context"] == scenario["workspace_context"]
    assert "orchestration_context" in payload
    assert "assistance_level" in payload["orchestration_context"]


def test_candidate_instructions_require_same_language_and_no_repeat():
    from backend.benchmarks.run_mentor_benchmark import (
        build_candidate_instructions,
    )

    instructions = build_candidate_instructions()

    assert "same language as learner_message" in instructions
    assert "do not ask them to repeat" in instructions
    assert "Do not provide code unless" in instructions



def test_benchmark_separates_model_owned_and_orchestration_matches():
    matches = {
        "evidence_expected_match": 100.0,
        "success_expected_match": 100.0,
        "assistance_allowed_match": 70.0,
        "next_phase_match": 60.0,
        "misconception_match": 100.0,
    }

    model_owned = select_match_group(
        matches,
        MODEL_OWNED_MATCH_FIELDS,
    )
    orchestration = select_match_group(
        matches,
        ORCHESTRATION_DIAGNOSTIC_FIELDS,
    )

    assert model_owned == {
        "evidence_expected_match": 100.0,
        "success_expected_match": 100.0,
        "misconception_match": 100.0,
    }
    assert orchestration == {
        "assistance_allowed_match": 70.0,
        "next_phase_match": 60.0,
    }


def test_orchestrator_increases_help_for_explicit_beginner_request():
    suite = load_suite()
    scenario = next(
        item
        for item in suite["scenarios"]
        if item["id"] == "mentor_help_request_beginner"
    )

    assert determine_orchestrated_assistance(scenario) == "GUIDE"


def test_orchestrator_increases_help_for_repeated_misconception():
    suite = load_suite()
    scenario = next(
        item
        for item in suite["scenarios"]
        if item["id"] == "practice_target_repeated_misconception"
    )

    assert determine_orchestrated_assistance(scenario) == "GUIDE"


def test_orchestrator_advances_only_after_successful_evidence():
    assert determine_orchestrated_next_phase(
        current_phase="reason",
        is_evidence=True,
        success=True,
    ) == "decide"

    assert determine_orchestrated_next_phase(
        current_phase="reason",
        is_evidence=False,
        success=None,
    ) == "reason"

    assert determine_orchestrated_next_phase(
        current_phase="reason",
        is_evidence=True,
        success=False,
    ) == "reason"

    assert determine_orchestrated_next_phase(
        current_phase="explain",
        is_evidence=True,
        success=True,
    ) == "completed"


def test_concise_judge_dimension_does_not_mix_correctness():
    from backend.benchmarks.run_mentor_benchmark import (
        build_judge_instructions,
    )

    instructions = build_judge_instructions()

    assert "scores only RESPONSE SHAPE" in instructions
    assert "Do not lower this score" in instructions



def test_candidate_instructions_leave_phase_and_assistance_to_orchestrator():
    from backend.benchmarks.run_mentor_benchmark import (
        build_candidate_instructions,
    )

    instructions = build_candidate_instructions()

    assert "Do NOT choose assistance_level or next_phase" in instructions
    assert "orchestrator owns those decisions" in instructions



def test_benchmark_provider_retries_groq_output_parse_failure_once():
    from backend.benchmarks.mentor_benchmark_provider import (
        _generate_openai_compatible_structured,
    )

    class FakeParseError(Exception):
        status_code = 400
        body = {
            "error": {
                "code": "output_parse_failed",
            }
        }

    parsed = CandidateResponse(
        is_evidence=True,
        success=True,
        misconception=None,
        mentor_reply="Kısa cevap.",
    )
    response = MagicMock()
    response.output_parsed = parsed

    with patch(
        "backend.benchmarks.mentor_benchmark_provider."
        "_openai_compatible_client",
        return_value=MagicMock(),
    ), patch(
        "backend.benchmarks.mentor_benchmark_provider."
        "guarded_responses_parse",
        side_effect=[
            FakeParseError("parse failed"),
            response,
        ],
    ) as mock_parse:
        result = _generate_openai_compatible_structured(
            provider="groq",
            model="openai/gpt-oss-20b",
            purpose="judge",
            instructions="Return structured output.",
            input_text="input",
            text_format=CandidateResponse,
        )

    assert result == parsed
    assert mock_parse.call_count == 2
    assert (
        mock_parse.call_args_list[1].kwargs["purpose"]
        == "judge_parse_retry"
    )


def test_benchmark_provider_does_not_retry_unrelated_error():
    from backend.benchmarks.mentor_benchmark_provider import (
        _generate_openai_compatible_structured,
    )
    import pytest

    class FakeOtherError(Exception):
        status_code = 429
        body = {
            "error": {
                "code": "rate_limit_exceeded",
            }
        }

    with patch(
        "backend.benchmarks.mentor_benchmark_provider."
        "_openai_compatible_client",
        return_value=MagicMock(),
    ), patch(
        "backend.benchmarks.mentor_benchmark_provider."
        "guarded_responses_parse",
        side_effect=FakeOtherError("rate limited"),
    ) as mock_parse:
        with pytest.raises(FakeOtherError):
            _generate_openai_compatible_structured(
                provider="groq",
                model="openai/gpt-oss-20b",
                purpose="judge",
                instructions="instructions",
                input_text="input",
                text_format=CandidateResponse,
            )

    assert mock_parse.call_count == 1



def test_benchmark_provider_retries_groq_json_validation_failure_once():
    from backend.benchmarks.mentor_benchmark_provider import (
        _generate_openai_compatible_structured,
    )

    class FakeJsonValidationError(Exception):
        status_code = 400
        body = {
            "error": {
                "code": "json_validate_failed",
                "failed_generation": (
                    "max completion tokens reached before "
                    "generating a valid document"
                ),
            }
        }

    parsed = CandidateResponse(
        is_evidence=True,
        success=True,
        misconception=None,
        mentor_reply="Kısa cevap.",
    )
    response = MagicMock()
    response.output_parsed = parsed

    with patch(
        "backend.benchmarks.mentor_benchmark_provider."
        "_openai_compatible_client",
        return_value=MagicMock(),
    ), patch(
        "backend.benchmarks.mentor_benchmark_provider."
        "guarded_responses_parse",
        side_effect=[
            FakeJsonValidationError("json failed"),
            response,
        ],
    ) as mock_parse:
        result = _generate_openai_compatible_structured(
            provider="groq",
            model="openai/gpt-oss-20b",
            purpose="judge",
            instructions="Return structured output.",
            input_text="input",
            text_format=CandidateResponse,
        )

    assert result == parsed
    assert mock_parse.call_count == 2
    assert (
        mock_parse.call_args_list[1].kwargs["purpose"]
        == "judge_parse_retry"
    )
