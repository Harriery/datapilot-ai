from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.benchmarks.mentor_benchmark_provider import (
    generate_benchmark_structured,
)
from backend.benchmarks.run_mentor_benchmark import (
    CandidateResponse,
    build_candidate_payload,
    build_benchmark_plan,
    calculate_expected_matches,
    load_suite,
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


def test_candidate_response_schema_requires_learning_loop_fields():
    response = CandidateResponse(
        is_evidence=True,
        success=True,
        assistance_level="NUDGE",
        next_phase="reason",
        misconception=None,
        mentor_reply="Good observation. What pattern would you inspect next?",
    )

    assert response.is_evidence is True
    assert response.success is True
    assert response.assistance_level == "NUDGE"
    assert response.next_phase == "reason"


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
        assistance_level="GUIDE",
        next_phase="reason",
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
        assistance_level="GUIDE",
        next_phase="decide",
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


def test_candidate_instructions_require_same_language_and_no_repeat():
    from backend.benchmarks.run_mentor_benchmark import (
        build_candidate_instructions,
    )

    instructions = build_candidate_instructions()

    assert "same language as learner_message" in instructions
    assert "do not ask them to repeat" in instructions
    assert "Do not provide code unless" in instructions
