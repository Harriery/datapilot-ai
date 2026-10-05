import hashlib

import backend.app.database as database

from backend.app.external_practice_validation_service import (
    record_client_validation_event,
)
from backend.app.models import (
    ExternalPracticeValidationEventRequest,
)
from backend.app.practice_mastery_service import (
    calculate_practice_mastery,
)


def _seed(tmp_path):
    database.DATABASE_PATH = (
        tmp_path / "external_practice_events.db"
    )
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-external",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
        preferred_language="en",
    )
    database.insert_skill_state(
        learner_id="learner-external",
        skill_name="python_data_structures",
        status="new",
    )


def test_client_validation_event_stores_solution_hash_not_answer(
    tmp_path,
):
    _seed(tmp_path)

    answer = (
        "def leap_year(year):\n"
        "    return year % 4 == 0\n"
    )

    event = record_client_validation_event(
        request=ExternalPracticeValidationEventRequest(
            learner_id="learner-external",
            source_id="exercism-python",
            source_exercise_id="leap",
            topic_id="python",
            subtopic_id="variables_types",
            practice_mode="code",
            difficulty="easy",
            content_hash="content-hash",
            validation_bundle_hash="bundle-hash",
            client_reported_success=True,
            tests_run=9,
            answer=answer,
        )
    )

    assert event.trust_level == "client_sandbox"
    assert event.solution_hash == hashlib.sha256(
        answer.encode("utf-8")
    ).hexdigest()

    rows = database.list_external_practice_validation_events(
        learner_id="learner-external",
        source_id="exercism-python",
        source_exercise_id="leap",
    )

    assert len(rows) == 1
    assert rows[0].client_reported_success is True
    assert rows[0].tests_run == 9


def test_client_validation_event_does_not_create_mastery_evidence(
    tmp_path,
):
    _seed(tmp_path)

    record_client_validation_event(
        request=ExternalPracticeValidationEventRequest(
            learner_id="learner-external",
            source_id="exercism-python",
            source_exercise_id="leap",
            topic_id="python",
            subtopic_id="variables_types",
            practice_mode="code",
            difficulty="easy",
            content_hash="content-hash",
            validation_bundle_hash="bundle-hash",
            client_reported_success=True,
            tests_run=9,
            answer="def leap_year(year): return True",
        )
    )

    evidence = (
        database.get_learning_evidence_by_learner(
            "learner-external"
        )
    )

    assert evidence == []

    mastery = calculate_practice_mastery(
        learner_id="learner-external",
        topic_id="python",
        subtopic_id="variables_types",
        practice_mode="code",
        difficulty="easy",
    )

    assert mastery.status == "not_started"
    assert mastery.successful_evidence_count == 0


def test_client_validation_events_keep_attempt_history(
    tmp_path,
):
    _seed(tmp_path)

    for success in (False, True):
        record_client_validation_event(
            request=ExternalPracticeValidationEventRequest(
                learner_id="learner-external",
                source_id="exercism-python",
                source_exercise_id="leap",
                topic_id="python",
                subtopic_id="variables_types",
                practice_mode="code",
                difficulty="easy",
                content_hash="content-hash",
                validation_bundle_hash="bundle-hash",
                client_reported_success=success,
                tests_run=9,
                answer=(
                    "def leap_year(year): "
                    + ("return False" if not success else "return True")
                ),
            )
        )

    rows = database.list_external_practice_validation_events(
        learner_id="learner-external",
        source_id="exercism-python",
        source_exercise_id="leap",
    )

    assert len(rows) == 2
    assert [
        row.client_reported_success
        for row in rows
    ] == [False, True]
