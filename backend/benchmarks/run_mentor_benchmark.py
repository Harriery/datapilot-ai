from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import BaseModel, Field

from backend.app.ai_provider_service import (
    AIProviderConfigurationError,
    get_ai_runtime,
)
from backend.app.ai_usage_guard import (
    AIBillingPolicyError,
    AIUsageLimitError,
    guarded_responses_parse,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUITE = (
    ROOT
    / "backend"
    / "benchmarks"
    / "mentor_benchmark_v1.json"
)


class BenchmarkEvaluation(BaseModel):
    evidence_expected_match: bool
    success_expected_match: bool
    assistance_allowed_match: bool
    next_phase_match: bool
    misconception_match: bool

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
    - Write one concise mentor reply for the learner.
    - Do not invent columns, values, business rules, or prior-project facts.
    - Do not skip ahead in the learning loop.
    - A help request is not failed learning evidence.
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

    Also compare the candidate structured fields against the scenario's
    expected values. For assistance_allowed_match, the candidate assistance
    level must be one of expected.allowed_assistance.

    For misconception_match:
    - if expected.misconception is absent, candidate misconception should be
      null or empty.
    - if expected.misconception exists, it must match exactly.

    Evaluate only from the supplied scenario and expectation. Do not add
    outside facts.
    """


def run_candidate(
    *,
    provider: str,
    model: str,
    scenario: dict[str, Any],
) -> tuple[CandidateResponse, float]:
    runtime = get_ai_runtime(
        "mentor"
    )

    if runtime.provider != provider:
        raise AIProviderConfigurationError(
            "Resolved provider does not match requested benchmark provider: "
            f"{runtime.provider} != {provider}"
        )

    started = perf_counter()

    response = guarded_responses_parse(
        runtime.client,
        provider=runtime.provider,
        purpose="mentor_benchmark_candidate",
        model=model,
        instructions=build_candidate_instructions(),
        input=json.dumps(
            {
                "scenario": scenario,
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
        response.output_parsed,
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
    runtime = get_ai_runtime(
        "classifier"
    )

    if runtime.provider != provider:
        raise AIProviderConfigurationError(
            "Resolved judge provider does not match requested provider: "
            f"{runtime.provider} != {provider}"
        )

    response = guarded_responses_parse(
        runtime.client,
        provider=runtime.provider,
        purpose="mentor_benchmark_judge",
        model=model,
        instructions=build_judge_instructions(),
        input=json.dumps(
            {
                "scenario": scenario,
                "candidate": candidate.model_dump(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        text_format=BenchmarkEvaluation,
    )

    return response.output_parsed


def run_suite(
    *,
    suite_path: Path,
    provider: str,
    candidate_model: str,
    judge_provider: str,
    judge_model: str,
    scenario_limit: int | None,
    output_path: Path,
) -> dict[str, Any]:
    suite = load_suite(
        suite_path
    )

    scenarios = suite[
        "scenarios"
    ]

    if scenario_limit is not None:
        scenarios = scenarios[
            :scenario_limit
        ]

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
                        "evaluation"
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
        "--output",
        type=Path,
        required=True,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = run_suite(
            suite_path=args.suite,
            provider=args.provider,
            candidate_model=args.candidate_model,
            judge_provider=args.judge_provider,
            judge_model=args.judge_model,
            scenario_limit=args.limit,
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
