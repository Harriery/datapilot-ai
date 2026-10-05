from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import BaseModel, Field

from backend.app.ai_provider_service import (
    AIProviderConfigurationError,
)
from backend.app.ai_usage_guard import (
    AIBillingPolicyError,
    AIUsageLimitError,
)
from backend.app.mentor_misconception_taxonomy import (
    canonical_misconception_instructions,
    normalize_misconception,
)
from backend.benchmarks.mentor_benchmark_provider import (
    generate_benchmark_structured,
)
from backend.benchmarks.run_mentor_benchmark import (
    DEFAULT_SUITE,
    determine_orchestrated_assistance,
    determine_orchestrated_next_phase,
    load_suite,
    select_scenarios,
)


class ClassifierResponse(BaseModel):
    is_evidence: bool
    success: bool | None = None
    misconception: str | None = None


class MentorReplyResponse(BaseModel):
    mentor_reply: str


class PipelineBenchmarkEvaluation(BaseModel):
    technical_correctness: int = Field(ge=0, le=5)
    pedagogy: int = Field(ge=0, le=5)
    assistance_calibration: int = Field(ge=0, le=5)
    context_fidelity: int = Field(ge=0, le=5)
    non_hallucination: int = Field(ge=0, le=5)
    learning_loop_discipline: int = Field(ge=0, le=5)
    transfer_reasoning: int = Field(ge=0, le=5)
    concise_stepwise_guidance: int = Field(ge=0, le=5)
    learner_level_fit: int = Field(ge=0, le=5)
    language_match: int = Field(ge=0, le=5)
    notes: str


def scenario_without_expected(
    scenario: dict[str, Any],
) -> dict[str, Any]:
    return {
        key: value
        for key, value in scenario.items()
        if key != "expected"
    }


def build_classifier_instructions() -> str:
    return f"""
    You are DataPilot's learning-evidence classifier.

    Return structured output only.

    Rules:
    - Decide whether learner_message is genuine learning evidence.
    - A pure help request or clarification question with no proposed answer,
      action, explanation, or hypothesis is not learning evidence.
    - A learner claim, proposed decision, explanation, hypothesis, or attempted
      answer IS learning evidence even when it is wrong.
    - Interrogative wording does not make a proposed decision non-evidence.
      For example, "Should I fill missing values with 0?" is a proposed action,
      so classify it as evidence and evaluate whether that proposal is sound.
    - For genuine evidence, set success true or false from the supplied context
      AND the current learning phase.
    - For non-evidence, set success=null.
    - Validation phase is strict: code running without error is NOT sufficient
      validation. Compare before/after evidence and the intended operation.
      Unexpected row loss, row gain, or other unintended side effects mean
      success=false until reconciled.
    - In validation, checking only one metric (for example only null_count=0)
      is insufficient when another supplied metric contradicts success.
    - If success=true, misconception must be null.
    - {canonical_misconception_instructions()}
    - Do not invent dataset facts.
    - Do not generate mentor guidance.
    """


def build_mentor_reply_instructions() -> str:
    return """
    You are DataPilot's adaptive Data Engineering mentor.

    Upstream classification and deterministic orchestration are already complete.
    Do not reclassify the learner and do not choose a different learning phase.

    Follow learning_evaluation and orchestration exactly.

    Response rules:
    - Reply in the same language as learner_message.
    - Give only ONE small next step.
    - The reply must have one cognitive target only. Do not combine two checks
      or two questions in one sentence.
    - Prefer one short sentence; target <= 20 words.
    - If success=true and next_phase differs from current_phase, briefly
      acknowledge the learner and move to the next phase. Do not ask them to
      repeat or reconfirm what they already established.
    - If success=false, stay on the current concept and repair only the specific
      misconception. Challenge the faulty premise before suggesting any
      implementation. Do not answer "use X instead of Y" when the learner has
      not yet established what the data means.
    - In a reasoning phase, do not combine understanding the cause with choosing
      an imputation or transformation in the same reply. Give only the reasoning
      step.
    - If is_evidence=false, give one small step that helps the learner continue
      the current phase. Do not ask the learner to recompute, restate, or record
      a fact that is already present in workspace_context.
    - Never invent an arbitrary technique, threshold, percentage bucket, sample
      size, grouping rule, or transformation that is not justified by the
      supplied context.
    - If next_phase=completed, only close/acknowledge the completed learning step.
      Do not tell the learner to continue analysis, do another check, ask a new
      question, or start a new task.
    - Respect assistance_level:
      NONE = minimal acknowledgement or transfer prompt;
      NUDGE = one small hint/question;
      GUIDE = one concrete, targeted step;
      TEACH = one compact concept explanation plus one immediate check;
      DEMONSTRATE = one minimal example only when needed.
    - Do not provide code unless learner_message explicitly asks for code or
      assistance_level=DEMONSTRATE.
    - Do not jump from grain to dimension design, from reasoning to implementation,
      or from a validation conclusion to a new analysis.
    - Do not invent columns, values, business rules, or prior-project facts.
    """


def build_pipeline_judge_instructions() -> str:
    return """
    You are strictly evaluating one DataPilot mentor reply.

    Score each dimension from 0 to 5:
    - technical_correctness
    - pedagogy
    - assistance_calibration
    - context_fidelity
    - non_hallucination
    - learning_loop_discipline
    - transfer_reasoning
    - concise_stepwise_guidance
    - learner_level_fit
    - language_match

    Apply the scenario expected.required_behaviors and expected.forbidden_behaviors
    strictly when they are relevant to the reply.

    Important scoring rules:
    - technical_correctness: penalize inaccurate code claims, data claims, or
      analytical advice. Also penalize arbitrary methods, thresholds, percentage
      buckets, or transformations unsupported by the scenario context.
    - pedagogy: 5 requires the reply to advance learning without making the
      learner repeat an already-correct conclusion or re-check a fact that is
      already explicitly available in workspace_context.
    - assistance_calibration: 5 requires matching orchestration.assistance_level.
    - learning_loop_discipline: 5 requires targeting orchestration.next_phase.
      If next_phase=completed, any new directive, continuation request, question,
      or task prevents a score of 5.
    - concise_stepwise_guidance scores RESPONSE SHAPE only. A single <=20-word
      step with one cognitive target should normally score 5. If the reply
      combines two checks/questions, or contains a sequence such as "first X,
      then Y" or "X, ardından Y", it contains multiple steps and cannot score 5.
    - language_match is 5 only when mentor_reply matches learner_message language.
    - transfer_reasoning: if transfer is not relevant in the scenario, score 5
      unless the reply introduces an unjustified prior-project transfer.

    Do not reward a reply merely because it is short.
    Do not let one strong dimension hide a failure in another.
    """


def run_classifier(
    *,
    provider: str,
    model: str,
    scenario: dict[str, Any],
) -> tuple[ClassifierResponse, float]:
    started = perf_counter()

    result = generate_benchmark_structured(
        provider=provider,
        model=model,
        purpose="mentor_pipeline_classifier",
        instructions=build_classifier_instructions(),
        input_text=json.dumps(
            {
                "scenario":
                    scenario_without_expected(
                        scenario
                    ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        text_format=ClassifierResponse,
    )

    result.misconception = normalize_misconception(
        success=result.success,
        misconception=result.misconception,
    )

    return (
        result,
        round(
            (perf_counter() - started) * 1000,
            2,
        ),
    )


def build_orchestration(
    *,
    scenario: dict[str, Any],
    classification: ClassifierResponse,
) -> dict[str, Any]:
    return {
        "current_phase":
            scenario["phase"],
        "assistance_level":
            determine_orchestrated_assistance(
                scenario
            ),
        "next_phase":
            determine_orchestrated_next_phase(
                current_phase=scenario["phase"],
                is_evidence=classification.is_evidence,
                success=classification.success,
            ),
    }


def run_mentor_reply(
    *,
    provider: str,
    model: str,
    scenario: dict[str, Any],
    classification: ClassifierResponse,
    orchestration: dict[str, Any],
) -> tuple[MentorReplyResponse, float]:
    started = perf_counter()

    result = generate_benchmark_structured(
        provider=provider,
        model=model,
        purpose="mentor_pipeline_reply",
        instructions=build_mentor_reply_instructions(),
        input_text=json.dumps(
            {
                "scenario":
                    scenario_without_expected(
                        scenario
                    ),
                "learning_evaluation":
                    classification.model_dump(),
                "orchestration":
                    orchestration,
            },
            ensure_ascii=False,
            indent=2,
        ),
        text_format=MentorReplyResponse,
    )

    return (
        result,
        round(
            (perf_counter() - started) * 1000,
            2,
        ),
    )


def run_judge(
    *,
    provider: str,
    model: str,
    scenario: dict[str, Any],
    classification: ClassifierResponse,
    orchestration: dict[str, Any],
    mentor_reply: MentorReplyResponse,
) -> PipelineBenchmarkEvaluation:
    return generate_benchmark_structured(
        provider=provider,
        model=model,
        purpose="mentor_pipeline_judge",
        instructions=build_pipeline_judge_instructions(),
        input_text=json.dumps(
            {
                "scenario": scenario,
                "classification":
                    classification.model_dump(),
                "orchestration":
                    orchestration,
                "mentor_reply":
                    mentor_reply.mentor_reply,
            },
            ensure_ascii=False,
            indent=2,
        ),
        text_format=PipelineBenchmarkEvaluation,
    )


def classifier_matches(
    *,
    scenario: dict[str, Any],
    classification: ClassifierResponse,
) -> dict[str, bool]:
    expected = scenario["expected"]
    expected_misconception = expected.get(
        "misconception"
    )

    return {
        "evidence_expected_match":
            classification.is_evidence
            == expected["evidence_expected"],
        "success_expected_match":
            classification.success
            == expected["success_expected"],
        "misconception_match":
            (
                classification.misconception
                or None
            )
            == expected_misconception,
    }


def orchestration_matches(
    *,
    scenario: dict[str, Any],
    orchestration: dict[str, Any],
) -> dict[str, bool]:
    expected = scenario["expected"]

    return {
        "assistance_allowed_match":
            orchestration["assistance_level"]
            in expected["allowed_assistance"],
        "next_phase_match":
            orchestration["next_phase"]
            == expected["next_phase"],
    }


def explicit_code_request(
    learner_message: str,
) -> bool:
    message = learner_message.casefold()
    markers = (
        "kod",
        "code",
        "python",
        "sql",
        "pandas",
    )
    return any(
        marker in message
        for marker in markers
    )


def deterministic_reply_checks(
    *,
    scenario: dict[str, Any],
    orchestration: dict[str, Any],
    reply: str,
) -> dict[str, bool]:
    word_count = len(
        reply.split()
    )

    code_allowed = (
        explicit_code_request(
            scenario["learner_message"]
        )
        or orchestration[
            "assistance_level"
        ]
        == "DEMONSTRATE"
    )

    contains_code_markup = (
        "`" in reply
        or "```" in reply
    )

    return {
        "compact_reply":
            word_count <= 20,
        "code_policy_ok":
            (
                code_allowed
                or not contains_code_markup
            ),
        "completed_without_new_question":
            (
                orchestration[
                    "next_phase"
                ]
                != "completed"
                or "?" not in reply
            ),
    }


def percentage(
    rows: list[dict[str, Any]],
    section: str,
    field: str,
) -> float:
    if not rows:
        return 0.0

    return round(
        sum(
            1
            for row in rows
            if row[section][field]
        )
        / len(rows)
        * 100,
        1,
    )


def run_suite(
    *,
    suite_path: Path,
    classifier_provider: str,
    classifier_model: str,
    mentor_provider: str,
    mentor_model: str,
    judge_provider: str,
    judge_model: str,
    scenario_limit: int | None,
    scenario_ids: list[str] | None,
    output_path: Path,
) -> dict[str, Any]:
    suite = load_suite(
        suite_path
    )
    scenarios = select_scenarios(
        suite=suite,
        scenario_ids=scenario_ids,
        scenario_limit=scenario_limit,
    )

    rows: list[dict[str, Any]] = []

    for scenario in scenarios:
        classification, classifier_latency = (
            run_classifier(
                provider=classifier_provider,
                model=classifier_model,
                scenario=scenario,
            )
        )

        orchestration = build_orchestration(
            scenario=scenario,
            classification=classification,
        )

        mentor_reply, mentor_latency = (
            run_mentor_reply(
                provider=mentor_provider,
                model=mentor_model,
                scenario=scenario,
                classification=classification,
                orchestration=orchestration,
            )
        )

        evaluation = run_judge(
            provider=judge_provider,
            model=judge_model,
            scenario=scenario,
            classification=classification,
            orchestration=orchestration,
            mentor_reply=mentor_reply,
        )

        rows.append(
            {
                "scenario_id":
                    scenario["id"],
                "stage":
                    scenario["stage"],
                "classification":
                    classification.model_dump(),
                "orchestration":
                    orchestration,
                "mentor_reply":
                    mentor_reply.mentor_reply,
                "classifier_matches":
                    classifier_matches(
                        scenario=scenario,
                        classification=classification,
                    ),
                "orchestration_matches":
                    orchestration_matches(
                        scenario=scenario,
                        orchestration=orchestration,
                    ),
                "reply_checks":
                    deterministic_reply_checks(
                        scenario=scenario,
                        orchestration=orchestration,
                        reply=mentor_reply.mentor_reply,
                    ),
                "evaluation":
                    evaluation.model_dump(),
                "classifier_latency_ms":
                    classifier_latency,
                "mentor_latency_ms":
                    mentor_latency,
            }
        )

    score_fields = [
        "technical_correctness",
        "pedagogy",
        "assistance_calibration",
        "context_fidelity",
        "non_hallucination",
        "learning_loop_discipline",
        "transfer_reasoning",
        "concise_stepwise_guidance",
        "learner_level_fit",
        "language_match",
    ]

    average_scores = {
        field: round(
            sum(
                row["evaluation"][field]
                for row in rows
            )
            / len(rows),
            2,
        )
        if rows
        else 0.0
        for field in score_fields
    }

    classifier_fields = [
        "evidence_expected_match",
        "success_expected_match",
        "misconception_match",
    ]
    orchestration_fields = [
        "assistance_allowed_match",
        "next_phase_match",
    ]
    reply_check_fields = [
        "compact_reply",
        "code_policy_ok",
        "completed_without_new_question",
    ]

    result = {
        "suite_id":
            suite["suite_id"],
        "suite_version":
            suite["version"],
        "benchmark_type":
            "mentor_pipeline",
        "scenario_count":
            len(rows),
        "classifier_provider":
            classifier_provider,
        "classifier_model":
            classifier_model,
        "mentor_provider":
            mentor_provider,
        "mentor_model":
            mentor_model,
        "judge_provider":
            judge_provider,
        "judge_model":
            judge_model,
        "average_scores":
            average_scores,
        "classifier_match_percent": {
            field:
                percentage(
                    rows,
                    "classifier_matches",
                    field,
                )
            for field in classifier_fields
        },
        "orchestration_match_percent": {
            field:
                percentage(
                    rows,
                    "orchestration_matches",
                    field,
                )
            for field in orchestration_fields
        },
        "reply_check_percent": {
            field:
                percentage(
                    rows,
                    "reply_checks",
                    field,
                )
            for field in reply_check_fields
        },
        "average_classifier_latency_ms":
            round(
                sum(
                    row[
                        "classifier_latency_ms"
                    ]
                    for row in rows
                )
                / len(rows),
                2,
            )
            if rows
            else 0.0,
        "average_mentor_latency_ms":
            round(
                sum(
                    row[
                        "mentor_latency_ms"
                    ]
                    for row in rows
                )
                / len(rows),
                2,
            )
            if rows
            else 0.0,
        "results":
            rows,
    }

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return result


def build_plan(
    *,
    suite_path: Path,
    scenario_limit: int | None,
    scenario_ids: list[str] | None,
    classifier_provider: str,
    classifier_model: str,
    mentor_provider: str,
    mentor_model: str,
    judge_provider: str,
    judge_model: str,
) -> dict[str, Any]:
    suite = load_suite(
        suite_path
    )
    scenarios = select_scenarios(
        suite=suite,
        scenario_ids=scenario_ids,
        scenario_limit=scenario_limit,
    )

    return {
        "suite_id":
            suite["suite_id"],
        "benchmark_type":
            "mentor_pipeline",
        "scenario_count":
            len(scenarios),
        "estimated_external_requests":
            len(scenarios) * 3,
        "classifier_provider":
            classifier_provider,
        "classifier_model":
            classifier_model,
        "mentor_provider":
            mentor_provider,
        "mentor_model":
            mentor_model,
        "judge_provider":
            judge_provider,
        "judge_model":
            judge_model,
        "scenario_ids": [
            scenario["id"]
            for scenario in scenarios
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the DataPilot classifier -> orchestrator -> mentor pipeline benchmark."
        )
    )
    parser.add_argument(
        "--suite",
        type=Path,
        default=DEFAULT_SUITE,
    )
    parser.add_argument(
        "--classifier-provider",
        required=True,
    )
    parser.add_argument(
        "--classifier-model",
        required=True,
    )
    parser.add_argument(
        "--mentor-provider",
        required=True,
    )
    parser.add_argument(
        "--mentor-model",
        required=True,
    )
    parser.add_argument(
        "--judge-provider",
        required=True,
    )
    parser.add_argument(
        "--judge-model",
        required=True,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--scenario-id",
        action="append",
        dest="scenario_ids",
        default=None,
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
    )
    parser.add_argument(
        "--confirm-live",
        action="store_true",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    plan = build_plan(
        suite_path=args.suite,
        scenario_limit=args.limit,
        scenario_ids=args.scenario_ids,
        classifier_provider=args.classifier_provider,
        classifier_model=args.classifier_model,
        mentor_provider=args.mentor_provider,
        mentor_model=args.mentor_model,
        judge_provider=args.judge_provider,
        judge_model=args.judge_model,
    )

    if args.dry_run:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.output.write_text(
            json.dumps(
                plan,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                plan,
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if not args.confirm_live:
        print(
            "Benchmark blocked before external AI calls. "
            "Use --dry-run or add --confirm-live."
        )
        print(
            json.dumps(
                plan,
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    try:
        result = run_suite(
            suite_path=args.suite,
            classifier_provider=args.classifier_provider,
            classifier_model=args.classifier_model,
            mentor_provider=args.mentor_provider,
            mentor_model=args.mentor_model,
            judge_provider=args.judge_provider,
            judge_model=args.judge_model,
            scenario_limit=args.limit,
            scenario_ids=args.scenario_ids,
            output_path=args.output,
        )
    except (
        AIProviderConfigurationError,
        AIBillingPolicyError,
        AIUsageLimitError,
    ) as exc:
        print(
            f"Benchmark blocked: {exc}"
        )
        return 2

    print(
        json.dumps(
            {
                "suite_id":
                    result["suite_id"],
                "benchmark_type":
                    result["benchmark_type"],
                "scenario_count":
                    result["scenario_count"],
                "average_scores":
                    result["average_scores"],
                "classifier_match_percent":
                    result["classifier_match_percent"],
                "orchestration_match_percent":
                    result["orchestration_match_percent"],
                "reply_check_percent":
                    result["reply_check_percent"],
                "average_classifier_latency_ms":
                    result["average_classifier_latency_ms"],
                "average_mentor_latency_ms":
                    result["average_mentor_latency_ms"],
                "output":
                    str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
