import backend.app.database as database

from backend.app.models import (
    ExternalPracticeValidationEvent,
    PracticeExerciseSourceItem,
)
from backend.app.practice_progression_service import (
    choose_next_external_exercise,
)


def _seed(tmp_path):
    database.DATABASE_PATH = (
        tmp_path / "practice_progression.db"
    )
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-progression",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
        preferred_language="en",
    )


def _exercise(
    exercise_id: str,
) -> PracticeExerciseSourceItem:
    return PracticeExerciseSourceItem(
        source_id="exercism-python",
        source_exercise_id=exercise_id,
        title=exercise_id,
        source_difficulty=1,
        difficulty="easy",
        practices=["loops"],
        prerequisites=[],
        mastery_signals=[
            "correct_application"
        ],
        attribution="Exercism",
    )


def _event(
    *,
    exercise_id: str,
    success: bool,
    index: int,
):
    return ExternalPracticeValidationEvent(
        event_id=f"event-{index}",
        learner_id="learner-progression",
        source_id="exercism-python",
        source_exercise_id=exercise_id,
        topic_id="python",
        subtopic_id="loops",
        practice_mode="code",
        difficulty="easy",
        content_hash="content",
        validation_bundle_hash="bundle",
        solution_hash=f"solution-{index}",
        client_reported_success=success,
        tests_run=5,
        trust_level="client_sandbox",
    )


def _choose():
    return choose_next_external_exercise(
        learner_id="learner-progression",
        topic_id="python",
        subtopic_id="loops",
        practice_mode="code",
        difficulty="easy",
        source_id="exercism-python",
        exercises=[
            _exercise("one"),
            _exercise("two"),
        ],
    )


def test_progression_starts_with_first_unseen_exercise(
    tmp_path,
):
    _seed(tmp_path)

    result = _choose()

    assert result.status == "new"
    assert result.exercise is not None
    assert (
        result.exercise.source_exercise_id
        == "one"
    )
    assert result.completed_exercise_count == 0


def test_progression_resumes_last_failed_exercise(
    tmp_path,
):
    _seed(tmp_path)

    database.record_external_practice_validation_event(
        event=_event(
            exercise_id="one",
            success=False,
            index=1,
        )
    )

    result = _choose()

    assert result.status == "resume"
    assert result.exercise is not None
    assert (
        result.exercise.source_exercise_id
        == "one"
    )


def test_progression_moves_after_success(
    tmp_path,
):
    _seed(tmp_path)

    database.record_external_practice_validation_event(
        event=_event(
            exercise_id="one",
            success=True,
            index=1,
        )
    )

    result = _choose()

    assert result.status == "next"
    assert result.exercise is not None
    assert (
        result.exercise.source_exercise_id
        == "two"
    )
    assert result.completed_exercise_count == 1


def test_progression_reports_cycle_complete(
    tmp_path,
):
    _seed(tmp_path)

    database.record_external_practice_validation_event(
        event=_event(
            exercise_id="one",
            success=True,
            index=1,
        )
    )
    database.record_external_practice_validation_event(
        event=_event(
            exercise_id="two",
            success=True,
            index=2,
        )
    )

    result = _choose()

    assert result.status == "cycle_complete"
    assert result.exercise is None
    assert result.completed_exercise_count == 2
    assert result.available_exercise_count == 2
