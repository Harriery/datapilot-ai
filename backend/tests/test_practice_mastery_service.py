import json

import backend.app.database as database

from backend.app.practice_mastery_service import (
    calculate_practice_mastery,
)


def _seed_learner(tmp_path):
    database.DATABASE_PATH = (
        tmp_path / "practice_mastery.db"
    )
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-mastery",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
        preferred_language="en",
    )
    database.insert_skill_state(
        learner_id="learner-mastery",
        skill_name="python_data_structures",
        status="new",
    )


def _record(
    *,
    success: bool,
    assistance_level: str,
    signals: list[str],
    source_exercise_id: str,
):
    database.record_learning_evidence(
        learner_id="learner-mastery",
        skill_name="python_data_structures",
        assistance_level=assistance_level,
        success=success,
        evidence_type="application",
        note="practice mastery test",
        session_id=None,
        context={
            "stage": "practice",
            "task_type": "practice_challenge",
            "topic_id": "python",
            "subtopic_id": "loops",
            "practice_mode": "code",
            "difficulty": "easy",
            "source_id": "exercism-python",
            "source_exercise_id": source_exercise_id,
            "mastery_signals": signals,
            "deterministic_validation": True,
        },
    )


def test_mastery_is_not_started_without_matching_evidence(
    tmp_path,
):
    _seed_learner(tmp_path)

    result = calculate_practice_mastery(
        learner_id="learner-mastery",
        topic_id="python",
        subtopic_id="loops",
        practice_mode="code",
        difficulty="easy",
    )

    assert result.status == "not_started"
    assert result.successful_evidence_count == 0
    assert all(
        not signal.demonstrated
        for signal in result.signals
    )


def test_mastery_builds_from_successful_signal_evidence(
    tmp_path,
):
    _seed_learner(tmp_path)

    _record(
        success=True,
        assistance_level="GUIDE",
        signals=[
            "concept_coverage",
            "correct_application",
        ],
        source_exercise_id="exercise-1",
    )

    result = calculate_practice_mastery(
        learner_id="learner-mastery",
        topic_id="python",
        subtopic_id="loops",
        practice_mode="code",
        difficulty="easy",
    )

    signal_map = {
        item.signal: item
        for item in result.signals
    }

    assert result.status == "building"
    assert result.successful_evidence_count == 1
    assert signal_map[
        "concept_coverage"
    ].demonstrated is True
    assert signal_map[
        "correct_application"
    ].demonstrated is True
    assert signal_map[
        "transfer_to_new_context"
    ].demonstrated is False
    assert signal_map[
        "independent_completion"
    ].demonstrated is False


def test_mastery_requires_all_signals_not_question_quota(
    tmp_path,
):
    _seed_learner(tmp_path)

    _record(
        success=True,
        assistance_level="GUIDE",
        signals=[
            "concept_coverage",
            "correct_application",
        ],
        source_exercise_id="exercise-1",
    )
    _record(
        success=True,
        assistance_level="NONE",
        signals=[
            "transfer_to_new_context",
        ],
        source_exercise_id="exercise-2",
    )

    result = calculate_practice_mastery(
        learner_id="learner-mastery",
        topic_id="python",
        subtopic_id="loops",
        practice_mode="code",
        difficulty="easy",
    )

    assert result.status == "demonstrated"
    assert result.successful_evidence_count == 2
    assert result.independent_success_count == 1
    assert all(
        signal.demonstrated
        for signal in result.signals
    )


def test_failed_attempt_does_not_demonstrate_mastery(
    tmp_path,
):
    _seed_learner(tmp_path)

    _record(
        success=False,
        assistance_level="NONE",
        signals=[
            "concept_coverage",
            "correct_application",
            "transfer_to_new_context",
        ],
        source_exercise_id="exercise-failed",
    )

    result = calculate_practice_mastery(
        learner_id="learner-mastery",
        topic_id="python",
        subtopic_id="loops",
        practice_mode="code",
        difficulty="easy",
    )

    assert result.status == "building"
    assert result.successful_evidence_count == 0
    assert result.independent_success_count == 0
    assert all(
        not signal.demonstrated
        for signal in result.signals
    )
