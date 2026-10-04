from pathlib import Path

from backend.benchmarks.run_mentor_pipeline_benchmark import (
    ClassifierResponse,
    build_classifier_instructions,
    build_mentor_reply_instructions,
    build_orchestration,
    build_plan,
    deterministic_reply_checks,
    scenario_without_expected,
)
from backend.benchmarks.run_mentor_benchmark import (
    load_suite,
)


def test_pipeline_scenario_payload_hides_expected_answer():
    suite = load_suite()
    scenario = suite["scenarios"][0]

    payload = scenario_without_expected(scenario)

    assert "expected" not in payload
    assert payload["learner_message"] == scenario["learner_message"]


def test_pipeline_classifier_only_classifies_learning_evidence():
    instructions = build_classifier_instructions()

    assert "Do not generate mentor guidance." in instructions
    assert "help request or clarification question" in instructions


def test_pipeline_orchestrator_advances_after_success():
    suite = load_suite()
    scenario = next(
        item
        for item in suite["scenarios"]
        if item["id"] == "model_grain_order_lines"
    )

    orchestration = build_orchestration(
        scenario=scenario,
        classification=ClassifierResponse(
            is_evidence=True,
            success=True,
            misconception=None,
        ),
    )

    assert orchestration["current_phase"] == "reason"
    assert orchestration["next_phase"] == "decide"
    assert orchestration["assistance_level"] == "GUIDE"


def test_pipeline_mentor_consumes_upstream_state():
    instructions = build_mentor_reply_instructions()

    assert "Upstream classification and deterministic orchestration" in instructions
    assert "If next_phase=completed" in instructions
    assert "Do not reclassify the learner" in instructions


def test_pipeline_reply_checks_completed_question():
    scenario = {
        "learner_message": "Bunu anlamadım, neye bakmalıyım?",
    }
    orchestration = {
        "assistance_level": "GUIDE",
        "next_phase": "completed",
    }

    checks = deterministic_reply_checks(
        scenario=scenario,
        orchestration=orchestration,
        reply="Şimdi başka bir analiz yapalım mı?",
    )

    assert checks["compact_reply"] is True
    assert checks["completed_without_new_question"] is False


def test_pipeline_plan_counts_three_requests_per_scenario():
    plan = build_plan(
        suite_path=Path(
            "backend/benchmarks/mentor_benchmark_v1.json"
        ),
        scenario_limit=3,
        scenario_ids=None,
        classifier_provider="groq",
        classifier_model="openai/gpt-oss-20b",
        mentor_provider="groq",
        mentor_model="openai/gpt-oss-120b",
        judge_provider="groq",
        judge_model="openai/gpt-oss-20b",
    )

    assert plan["scenario_count"] == 3
    assert plan["estimated_external_requests"] == 9
    assert plan["benchmark_type"] == "mentor_pipeline"
