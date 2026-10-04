from pathlib import Path

from backend.benchmarks.run_mentor_benchmark import (
    CandidateResponse,
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
