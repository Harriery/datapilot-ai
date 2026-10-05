from pathlib import Path

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.benchmarks.run_mentor_pipeline_benchmark import (
    BenchmarkCheckpointError,
    ClassifierResponse,
    build_classifier_instructions,
    checkpoint_path_for_output,
    build_mentor_reply_instructions,
    build_orchestration,
    build_plan,
    deterministic_reply_checks,
    run_suite,
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



def test_pipeline_classifier_treats_question_shaped_decision_as_evidence_rule():
    instructions = build_classifier_instructions()

    assert "Interrogative wording does not make a proposed decision non-evidence" in instructions
    assert "Should I fill missing values with 0?" in instructions


def test_pipeline_mentor_repairs_premise_before_replacement():
    instructions = build_mentor_reply_instructions()
    normalized = " ".join(
        instructions.split()
    )

    assert (
        "Challenge the faulty premise before suggesting any implementation"
        in normalized
    )
    assert "use X instead of Y" in normalized



def test_pipeline_mentor_forbids_arbitrary_methods_and_multi_step_reasoning():
    instructions = " ".join(
        build_mentor_reply_instructions().split()
    )

    assert "Never invent an arbitrary technique" in instructions
    assert "percentage bucket" in instructions
    assert "do not combine" in instructions
    assert "Give only the reasoning step" in instructions


def test_pipeline_mentor_completed_phase_only_closes():
    instructions = " ".join(
        build_mentor_reply_instructions().split()
    )

    assert "If next_phase=completed" in instructions
    assert "only close/acknowledge" in instructions
    assert "Do not tell the learner to continue analysis" in instructions



def test_pipeline_mentor_avoids_rechecking_known_context():
    instructions = " ".join(
        build_mentor_reply_instructions().split()
    )

    assert "Do not ask the learner to recompute" in instructions
    assert "already present in workspace_context" in instructions


def test_pipeline_mentor_has_one_cognitive_target():
    instructions = " ".join(
        build_mentor_reply_instructions().split()
    )

    assert "one cognitive target only" in instructions
    assert "Do not combine two checks" in instructions



def test_pipeline_classifier_has_strict_validation_rules():
    instructions = " ".join(
        build_classifier_instructions().split()
    )

    assert "code running without error is NOT sufficient validation" in instructions
    assert "Compare before/after evidence" in instructions
    assert "Unexpected row loss" in instructions
    assert "checking only one metric" in instructions


def test_pipeline_classifier_uses_canonical_misconception_taxonomy():
    instructions = build_classifier_instructions()

    assert "missing_value_means_fill_zero" in instructions
    assert "execution_success_equals_validation" in instructions
    assert "single_metric_validation" in instructions
    assert "Do not invent a new label" in instructions
    assert "If success=true, misconception must be null" in instructions



def test_pipeline_checkpoint_path_uses_output_stem():
    output = Path(
        "backend/benchmarks/results/example.json"
    )

    assert checkpoint_path_for_output(output) == Path(
        "backend/benchmarks/results/example.checkpoint.json"
    )


def test_pipeline_resume_skips_completed_scenario(tmp_path):
    output = tmp_path / "resume-test.json"
    checkpoint = checkpoint_path_for_output(
        output
    )

    suite = load_suite()
    selected = suite["scenarios"][:2]

    config = {
        "suite_id": suite["suite_id"],
        "suite_version": suite["version"],
        "scenario_ids": [
            scenario["id"]
            for scenario in selected
        ],
        "classifier_provider": "groq",
        "classifier_model": "classifier",
        "mentor_provider": "groq",
        "mentor_model": "mentor",
        "judge_provider": "groq",
        "judge_model": "judge",
    }

    first_row = {
        "scenario_id": selected[0]["id"],
        "stage": selected[0]["stage"],
        "classification": {
            "is_evidence": True,
            "success": True,
            "misconception": None,
        },
        "orchestration": {
            "current_phase": selected[0]["phase"],
            "assistance_level": "GUIDE",
            "next_phase": "reason",
        },
        "mentor_reply": "Devam edin.",
        "classifier_matches": {
            "evidence_expected_match": True,
            "success_expected_match": True,
            "misconception_match": True,
        },
        "orchestration_matches": {
            "assistance_allowed_match": True,
            "next_phase_match": True,
        },
        "reply_checks": {
            "compact_reply": True,
            "code_policy_ok": True,
            "completed_without_new_question": True,
        },
        "evaluation": {
            "technical_correctness": 5,
            "pedagogy": 5,
            "assistance_calibration": 5,
            "context_fidelity": 5,
            "non_hallucination": 5,
            "learning_loop_discipline": 5,
            "transfer_reasoning": 5,
            "concise_stepwise_guidance": 5,
            "learner_level_fit": 5,
            "language_match": 5,
            "notes": "ok",
        },
        "classifier_latency_ms": 10.0,
        "mentor_latency_ms": 20.0,
    }

    checkpoint.write_text(
        json.dumps(
            {
                "checkpoint_version": 1,
                "status": "in_progress",
                "run_config": config,
                "completed_scenario_ids": [
                    selected[0]["id"]
                ],
                "completed_scenario_count": 1,
                "estimated_completed_requests": 3,
                "last_error": None,
                "results": [
                    first_row
                ],
            }
        ),
        encoding="utf-8",
    )

    classifier_result = ClassifierResponse(
        is_evidence=True,
        success=True,
        misconception=None,
    )
    mentor_result = MagicMock()
    mentor_result.mentor_reply = "Kısa cevap."
    judge_result = MagicMock()
    judge_result.model_dump.return_value = {
        "technical_correctness": 5,
        "pedagogy": 5,
        "assistance_calibration": 5,
        "context_fidelity": 5,
        "non_hallucination": 5,
        "learning_loop_discipline": 5,
        "transfer_reasoning": 5,
        "concise_stepwise_guidance": 5,
        "learner_level_fit": 5,
        "language_match": 5,
        "notes": "ok",
    }

    with patch(
        "backend.benchmarks.run_mentor_pipeline_benchmark."
        "select_scenarios",
        return_value=selected,
    ), patch(
        "backend.benchmarks.run_mentor_pipeline_benchmark."
        "run_classifier",
        return_value=(
            classifier_result,
            11.0,
        ),
    ) as mock_classifier, patch(
        "backend.benchmarks.run_mentor_pipeline_benchmark."
        "run_mentor_reply",
        return_value=(
            mentor_result,
            21.0,
        ),
    ), patch(
        "backend.benchmarks.run_mentor_pipeline_benchmark."
        "run_judge",
        return_value=judge_result,
    ):
        result = run_suite(
            suite_path=Path(
                "backend/benchmarks/mentor_benchmark_v1.json"
            ),
            classifier_provider="groq",
            classifier_model="classifier",
            mentor_provider="groq",
            mentor_model="mentor",
            judge_provider="groq",
            judge_model="judge",
            scenario_limit=2,
            scenario_ids=None,
            output_path=output,
            resume=True,
        )

    assert mock_classifier.call_count == 1
    assert result["scenario_count"] == 2
    assert result["resume_metadata"]["resumed"] is True
    assert (
        result["resume_metadata"]["resumed_scenario_count"]
        == 1
    )
    assert result["resume_metadata"]["estimated_requests_saved"] == 3
    assert not checkpoint.exists()


def test_pipeline_checkpoint_config_mismatch_fails_closed(tmp_path):
    output = tmp_path / "resume-test.json"
    checkpoint = checkpoint_path_for_output(
        output
    )

    checkpoint.write_text(
        json.dumps(
            {
                "checkpoint_version": 1,
                "status": "in_progress",
                "run_config": {
                    "suite_id": "wrong-suite",
                },
                "results": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkCheckpointError
    ):
        run_suite(
            suite_path=Path(
                "backend/benchmarks/mentor_benchmark_v1.json"
            ),
            classifier_provider="groq",
            classifier_model="classifier",
            mentor_provider="groq",
            mentor_model="mentor",
            judge_provider="groq",
            judge_model="judge",
            scenario_limit=1,
            scenario_ids=None,
            output_path=output,
            resume=True,
        )


def test_pipeline_partial_failure_keeps_completed_checkpoint(tmp_path):
    output = tmp_path / "partial.json"
    checkpoint = checkpoint_path_for_output(
        output
    )

    suite = load_suite()
    selected = suite["scenarios"][:2]

    classifications = [
        (
            ClassifierResponse(
                is_evidence=True,
                success=True,
                misconception=None,
            ),
            10.0,
        ),
        RuntimeError("boom"),
    ]

    mentor_result = MagicMock()
    mentor_result.mentor_reply = "Kısa cevap."
    judge_result = MagicMock()
    judge_result.model_dump.return_value = {
        "technical_correctness": 5,
        "pedagogy": 5,
        "assistance_calibration": 5,
        "context_fidelity": 5,
        "non_hallucination": 5,
        "learning_loop_discipline": 5,
        "transfer_reasoning": 5,
        "concise_stepwise_guidance": 5,
        "learner_level_fit": 5,
        "language_match": 5,
        "notes": "ok",
    }

    with patch(
        "backend.benchmarks.run_mentor_pipeline_benchmark."
        "select_scenarios",
        return_value=selected,
    ), patch(
        "backend.benchmarks.run_mentor_pipeline_benchmark."
        "run_classifier",
        side_effect=classifications,
    ), patch(
        "backend.benchmarks.run_mentor_pipeline_benchmark."
        "run_mentor_reply",
        return_value=(
            mentor_result,
            20.0,
        ),
    ), patch(
        "backend.benchmarks.run_mentor_pipeline_benchmark."
        "run_judge",
        return_value=judge_result,
    ):
        with pytest.raises(RuntimeError):
            run_suite(
                suite_path=Path(
                    "backend/benchmarks/mentor_benchmark_v1.json"
                ),
                classifier_provider="groq",
                classifier_model="classifier",
                mentor_provider="groq",
                mentor_model="mentor",
                judge_provider="groq",
                judge_model="judge",
                scenario_limit=2,
                scenario_ids=None,
                output_path=output,
                resume=False,
            )

    saved = json.loads(
        checkpoint.read_text(
            encoding="utf-8"
        )
    )

    assert saved["completed_scenario_count"] == 1
    assert saved["completed_scenario_ids"] == [
        selected[0]["id"]
    ]
    assert saved["last_error"]["scenario_id"] == selected[1]["id"]
