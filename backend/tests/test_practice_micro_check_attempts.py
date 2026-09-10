import backend.app.database as database

from backend.app.models import (
    PracticeChallenge,
    PracticeChallengeRecord,
    PracticeAttemptRequest,
    PracticeAttemptValidation,
    PracticeMicroCheckValidation,
)


def test_save_practice_micro_check_attempts(
    tmp_path,
):

    database.DATABASE_PATH = (
        tmp_path / "test.db"
    )

    database.init_db()

    # --------------------------------------------------
    # LEARNER
    # --------------------------------------------------

    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )

    # --------------------------------------------------
    # ORIGINAL CHALLENGE
    # --------------------------------------------------

    challenge = PracticeChallenge(
        challenge_id="challenge-001",
        skill_name="python_data_structures",
        difficulty="easy",
        challenge_type="code",
        title="Test challenge",
        instructions="Test.",
        starter_code=None,
    )

    database.save_practice_challenge(
        learner_id="learner-001",
        record=PracticeChallengeRecord(
            challenge=challenge,
            expected_outcome="2",
        ),
    )

    # --------------------------------------------------
    # ORIGINAL PRACTICE ATTEMPT
    # --------------------------------------------------

    original_attempt = (
        database.save_practice_attempt(
            attempt=PracticeAttemptRequest(
                learner_id="learner-001",
                challenge_id="challenge-001",
                answer="wrong",
            ),
            validation=PracticeAttemptValidation(
                success=False,
                feedback="Başarısız.",
            ),
        )
    )

    # --------------------------------------------------
    # MICRO-CHECK ATTEMPT 1
    # --------------------------------------------------

    saved_1 = (
        database.save_practice_micro_check_attempt(
            learner_id="learner-001",
            attempt_id=original_attempt.attempt_id,
            answer="vehicle.wheels",
            validation=PracticeMicroCheckValidation(
                success=False,
                feedback="Yanlış.",
            ),
        )
    )

    # --------------------------------------------------
    # MICRO-CHECK ATTEMPT 2
    # --------------------------------------------------

    saved_2 = (
        database.save_practice_micro_check_attempt(
            learner_id="learner-001",
            attempt_id=original_attempt.attempt_id,
            answer="vehicle['wheels']",
            validation=PracticeMicroCheckValidation(
                success=True,
                feedback="Doğru.",
            ),
        )
    )

    assert (
        saved_1.micro_check_attempt_number
        == 1
    )

    assert (
        saved_2.micro_check_attempt_number
        == 2
    )

    assert saved_1.validation.success is False
    assert saved_2.validation.success is True

    assert saved_1.micro_check_attempt_id
    assert saved_2.micro_check_attempt_id

        # --------------------------------------------------
    # LOAD MICRO-CHECK HISTORY
    # --------------------------------------------------

    loaded_attempts = (
        database.get_practice_micro_check_attempts(
            learner_id="learner-001",
            attempt_id=original_attempt.attempt_id,
        )
    )

    assert len(loaded_attempts) == 2

    assert (
        loaded_attempts[0].micro_check_attempt_number
        == 1
    )

    assert loaded_attempts[0].answer == "vehicle.wheels"
    assert loaded_attempts[0].validation.success is False

    assert (
        loaded_attempts[1].micro_check_attempt_number
        == 2
    )

    assert (
        loaded_attempts[1].answer
        == "vehicle['wheels']"
    )

    assert loaded_attempts[1].validation.success is True

    # Başka learner aynı attempt'i okuyamamalı.
    wrong_owner = (
        database.get_practice_micro_check_attempts(
            learner_id="another-learner",
            attempt_id=original_attempt.attempt_id,
        )
    )

    assert wrong_owner == []
    assert (
        saved_1.micro_check_attempt_id
        != saved_2.micro_check_attempt_id
    )