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
from backend.benchmarks.mentor_benchmark_provider import (
    generate_benchmark_structured,
)
from backend.app.ai_usage_guard import (
    AIBillingPolicyError,
    AIUsageLimitError,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUITE = (
    ROOT
    / "backend"
    / "benchmarks"
    / "mentor_benchmark_v1.json"
)


class BenchmarkEvaluation(BaseModel):
    technical_correctness: int = Field(
        ge=0,
        le=5,
    )
    pedagogy: int = Field(
        ge=0,
        le=5,
    )
    assistance_calibration: int = Field(
        ge=0,
        le=5,
    )
    context_fidelity: int = Field(
        ge=0,
        le=5,
    )
    non_hallucination: int = Field(
        ge=0,
        le=5,
    )
    learning_loop_discipline: int = Field(
        ge=0,
        le=5,
    )
    transfer_reasoning: int = Field(
        ge=0,
        le=5,
    )
    concise_stepwise_guidance: int = Field(
        ge=0,
        le=5,
    )
    learner_level_fit: int = Field(
        ge=0,
        le=5,
    )
    language_match: int = Field(
        ge=0,
        le=5,
    )

    notes: str


class CandidateResponse(BaseModel):
    is_evidence: bool
    success: bool | None = None
    assistance_level: str
    next_phase: str
    misconception: str | None = None
    mentor_reply: str


def load_suite(
    path: Path = DEFAULT_SUITE,
) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def select_scenarios(
    *,
    suite: dict[str, Any],
    scenario_ids: list[str] | None = None,
    scenario_limit: int | None = None,
) -> list[dict[str, Any]]:
    scenarios = suite[
        "scenarios"
    ]

    if scenario_ids:
        requested = set(
            scenario_ids
        )

        scenarios = [
            scenario
            for scenario in scenarios
            if scenario["id"] in requested
        ]

        found = {
            scenario["id"]
            for scenario in scenarios
        }

        missing = [
            scenario_id
            for scenario_id in scenario_ids
            if scenario_id not in found
        ]

        if missing:
            raise ValueError(
                "Unknown benchmark scenario id(s): "
                + ", ".join(
                    missing
                )
            )

    if scenario_limit is not None:
        scenarios = scenarios[
            :scenario_limit
        ]

    return scenarios


def build_candidate_payload(
    scenario: dict[str, Any],
) -> dict[str, Any]:
    """
    Build the information visible to the candidate model.

    The expected answer/rubric is intentionally excluded. Otherwise the
    benchmark would leak its answer key to the model being evaluated.
    """
    return {
        key: value
        for key, value in scenario.items()
        if key != "expected"
    }


def build_candidate_instructions() -> str:
    return """
    You are the candidate model being benchmarked as the DataPilot adaptive
    Data Engineering mentor.

    Return a structured response only.

    Rules:
    - Judge whether the learner message is learning evidence.
    - If it is evidence, judge whether it is successful.
    - Choose the minimum assistance level needed from:
      NONE, NUDGE, GUIDE, TEACH, DEMONSTRATE.
    - Choose the next learning phase from:
      observe, reason, decide, implement, validate, explain, completed.
    - If a clear reusable misconception is visible, return a short snake_case
      misconception label; otherwise null.
    - Reply in the same language as learner_message. Do not switch languages.
    - Give only ONE next small step.
    - Prefer ONE short sentence, usually phrased as one focused question.
    - Keep the mentor reply to <= 20 words whenever possible.
    - If the learner is correct, do not ask them to repeat or merely agree with
      the same conclusion; advance the reasoning by one phase.
    - If you choose next_phase=completed, close briefly and do not invent a new task.
    - Do not provide code unless the learner explicitly asks for code or the
      assistance level is DEMONSTRATE.
    - Do not add a second instruction, explanation, checklist, or follow-up task
      after the first small step.
    - Use simple language appropriate for a beginner unless the learner clearly
      demonstrates a higher level.
    - Do not give a mini-lecture, long checklist, or full solution unless the
      required assistance level is DEMONSTRATE.
    - Do not invent columns, values, business rules, or prior-project facts.
    - Do not skip ahead in the learning loop.
    - A help request or clarification question by itself is not learning evidence.
    - A learner claim, proposed decision, explanation, or attempted answer IS learning
      evidence even when it is wrong or based on a misconception. In that case set
      is_evidence=true and success=false.
    - Do not mark a genuine incorrect attempt as is_evidence=false merely because
      the learner needs correction.
    - Successful code execution alone is not validation.
    - Numeric dtype does not automatically mean measure.
    - Prior-project patterns may be transferred only when current context
      justifies them.
    """


def build_judge_instructions() -> str:
    return """
    You are scoring a candidate DataPilot mentor response.

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

    concise_stepwise_guidance = 5 only when the reply gives exactly one small
    next step, preferably in one sentence and about 20 words or fewer, without
    an added explanation, checklist, second task, or unnecessary solution.
    learner_level_fit = 5 only when the wording and amount of help match the
    learner profile and current assistance need.
    language_match = 5 only when the mentor reply uses the same language as
    learner_message.

    Structured-field correctness is scored separately by deterministic code.
    Your job here is only to score response quality.

    Evaluate only from the supplied scenario and expectation. Do not add
    outside facts.
    """


def calculate_expected_matches(
    *,
    scenario: dict[str, Any],
    candidate: CandidateResponse,
) -> dict[str, bool]:
    expected = scenario[
        "expected"
    ]

    expected_misconception = (
        expected.get(
            "misconception"
        )
    )

    candidate_misconception = (
        candidate.misconception
        if candidate.misconception
        else None
    )

    return {
        "evidence_expected_match":
            candidate.is_evidence
            == expected[
                "evidence_expected"
            ],
        "success_expected_match":
            candidate.success
            == expected[
                "success_expected"
            ],
        "assistance_allowed_match":
            candidate.assistance_level
            in expected[
                "allowed_assistance"
            ],
        "next_phase_match":
            candidate.next_phase
            == expected[
                "next_phase"
            ],
        "misconception_match":
            candidate_misconception
            == expected_misconception,
    }


def build_benchmark_plan(
    *,
    suite_path: Path,
    provider: str,
    candidate_model: str,
    judge_provider: str,
    judge_model: str,
    scenario_limit: int | None,
    scenario_ids: list[str] | None = None,
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
        "suite_version":
            suite["version"],
        "scenario_count":
            len(scenarios),
        "provider":
            provider,
        "candidate_model":
            candidate_model,
        "judge_provider":
            judge_provider,
        "judge_model":
            judge_model,
        "network_calls":
            False,
        "estimated_external_requests":
            len(scenarios) * 2,
        "scenario_ids": [
            scenario["id"]
            for scenario in scenarios
        ],
    }


def run_candidate(
    *,
    provider: str,
    model: str,
    scenario: dict[str, Any],
) -> tuple[CandidateResponse, float]:
    started = perf_counter()

    candidate = generate_benchmark_structured(
        provider=provider,
        model=model,
        purpose="mentor_benchmark_candidate",
        instructions=build_candidate_instructions(),
        input_text=json.dumps(
            {
                "scenario":
                    build_candidate_payload(
                        scenario
                    ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        text_format=CandidateResponse,
    )

    elapsed_ms = (
        perf_counter()
        - started
    ) * 1000

    return (
        candidate,
        round(
            elapsed_ms,
            2,
        ),
    )


def run_judge(
    *,
    provider: str,
    model: str,
    scenario: dict[str, Any],
    candidate: CandidateResponse,
) -> BenchmarkEvaluation:
    return generate_benchmark_structured(
        provider=provider,
        model=model,
        purpose="mentor_benchmark_judge",
        instructions=build_judge_instructions(),
        input_text=json.dumps(
            {
                "scenario": scenario,
                "candidate": candidate.model_dump(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        text_format=BenchmarkEvaluation,
    )


def run_suite(
    *,
    suite_path: Path,
    provider: str,
    candidate_model: str,
    judge_provider: str,
    judge_model: str,
    scenario_limit: int | None,
    output_path: Path,
    scenario_ids: list[str] | None = None,
) -> dict[str, Any]:
    suite = load_suite(
        suite_path
    )

    scenarios = select_scenarios(
        suite=suite,
        scenario_ids=scenario_ids,
        scenario_limit=scenario_limit,
    )

    rows: list[
        dict[str, Any]
    ] = []

    for scenario in scenarios:
        candidate, elapsed_ms = (
            run_candidate(
                provider=provider,
                model=candidate_model,
                scenario=scenario,
            )
        )

        evaluation = run_judge(
            provider=judge_provider,
            model=judge_model,
            scenario=scenario,
            candidate=candidate,
        )

        expected_matches = (
            calculate_expected_matches(
                scenario=scenario,
                candidate=candidate,
            )
        )

        mentor_reply_word_count = len(
            candidate.mentor_reply.split()
        )

        rows.append(
            {
                "scenario_id":
                    scenario["id"],
                "stage":
                    scenario["stage"],
                "skill_name":
                    scenario["skill_name"],
                "phase":
                    scenario["phase"],
                "candidate":
                    candidate.model_dump(),
                "evaluation":
                    evaluation.model_dump(),
                "expected_matches":
                    expected_matches,
                "mentor_reply_word_count":
                    mentor_reply_word_count,
                "compact_reply":
                    mentor_reply_word_count <= 20,
                "latency_ms":
                    elapsed_ms,
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

    averages = {
        field: round(
            sum(
                row[
                    "evaluation"
                ][field]
                for row in rows
            )
            / len(rows),
            2,
        )
        if rows
        else 0.0
        for field in score_fields
    }

    match_fields = [
        "evidence_expected_match",
        "success_expected_match",
        "assistance_allowed_match",
        "next_phase_match",
        "misconception_match",
    ]

    matches = {
        field: round(
            (
                sum(
                    1
                    for row in rows
                    if row[
                        "expected_matches"
                    ][field]
                )
                / len(rows)
            )
            * 100,
            1,
        )
        if rows
        else 0.0
        for field in match_fields
    }

    result = {
        "suite_id":
            suite["suite_id"],
        "suite_version":
            suite["version"],
        "provider":
            provider,
        "candidate_model":
            candidate_model,
        "judge_provider":
            judge_provider,
        "judge_model":
            judge_model,
        "scenario_count":
            len(rows),
        "average_scores":
            averages,
        "field_match_percent":
            matches,
        "compact_reply_percent":
            round(
                (
                    sum(
                        1
                        for row in rows
                        if row[
                            "compact_reply"
                        ]
                    )
                    / len(rows)
                )
                * 100,
                1,
            )
            if rows
            else 0.0,
        "average_latency_ms":
            round(
                sum(
                    row["latency_ms"]
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the DataPilot Mentor benchmark."
        )
    )

    parser.add_argument(
        "--suite",
        type=Path,
        default=DEFAULT_SUITE,
    )
    parser.add_argument(
        "--provider",
        required=True,
    )
    parser.add_argument(
        "--candidate-model",
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
        help=(
            "Run only the named scenario. Repeat this flag to "
            "select multiple scenarios without rerunning earlier cases."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Validate and print the benchmark plan without "
            "making any external AI request."
        ),
    )
    parser.add_argument(
        "--confirm-live",
        action="store_true",
        help=(
            "Required for any live benchmark run. "
            "Without this flag, external AI requests are blocked."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.dry_run:
        plan = build_benchmark_plan(
            suite_path=args.suite,
            provider=args.provider,
            candidate_model=args.candidate_model,
            judge_provider=args.judge_provider,
            judge_model=args.judge_model,
            scenario_limit=args.limit,
            scenario_ids=args.scenario_ids,
        )

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
        plan = build_benchmark_plan(
            suite_path=args.suite,
            provider=args.provider,
            candidate_model=args.candidate_model,
            judge_provider=args.judge_provider,
            judge_model=args.judge_model,
            scenario_limit=args.limit,
            scenario_ids=args.scenario_ids,
        )

        print(
            "Benchmark blocked before external AI calls. "
            "Run with --dry-run to inspect the plan, or add "
            "--confirm-live only when you intentionally want "
            "to send requests."
        )
        print(
            json.dumps(
                {
                    "scenario_count":
                        plan[
                            "scenario_count"
                        ],
                    "estimated_external_requests":
                        plan[
                            "estimated_external_requests"
                        ],
                    "provider":
                        plan[
                            "provider"
                        ],
                    "candidate_model":
                        plan[
                            "candidate_model"
                        ],
                    "judge_provider":
                        plan[
                            "judge_provider"
                        ],
                    "judge_model":
                        plan[
                            "judge_model"
                        ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        return 2

    try:
        result = run_suite(
            suite_path=args.suite,
            provider=args.provider,
            candidate_model=args.candidate_model,
            judge_provider=args.judge_provider,
            judge_model=args.judge_model,
            scenario_limit=args.limit,
            output_path=args.output,
            scenario_ids=args.scenario_ids,
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
                    result[
                        "suite_id"
                    ],
                "candidate_model":
                    result[
                        "candidate_model"
                    ],
                "scenario_count":
                    result[
                        "scenario_count"
                    ],
                "average_scores":
                    result[
                        "average_scores"
                    ],
                "field_match_percent":
                    result[
                        "field_match_percent"
                    ],
                "average_latency_ms":
                    result[
                        "average_latency_ms"
                    ],
                "output":
                    str(
                        args.output
                    ),
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
