from pathlib import Path

from backend.benchmarks.run_mentor_benchmark import (
    CandidateResponse,
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
