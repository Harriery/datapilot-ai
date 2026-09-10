import backend.app.database as database

from backend.app.models import (
    PracticeChallenge,
    PracticeChallengeRecord,
    PracticeAttemptRequest,
    PracticeAttemptValidation,
    PracticeDiagnosis,
    PracticeMentorDecision,
    PracticeMentorSupport,
)


def test_save_and_get_practice_attempts(tmp_path):

    database.DATABASE_PATH = tmp_path / "test.db"
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
    # CHALLENGE
    # --------------------------------------------------

    challenge = PracticeChallenge(
        challenge_id="challenge-001",
        skill_name="python_data_structures",
        difficulty="easy",
        challenge_type="code",
        title="Eksik city değerlerini bul",
        instructions="Eksik city değerlerini bul.",
        starter_code="records = []",
    )

    challenge_record = PracticeChallengeRecord(
        challenge=challenge,
        expected_outcome="Sonuç 2 olmalı.",
    )

    database.save_practice_challenge(
        learner_id="learner-001",
        record=challenge_record,
    )

    # --------------------------------------------------
    # ATTEMPT 1
    # --------------------------------------------------

    attempt_1 = PracticeAttemptRequest(
        learner_id="learner-001",
        challenge_id="challenge-001",
        answer="print(record.city)",
        execution_output=None,
        execution_error=(
            "AttributeError: 'dict' object "
            "has no attribute 'city'"
        ),
    )

    validation_1 = PracticeAttemptValidation(
        success=False,
        feedback="Kod çalışırken bir hata oluştu.",
    )

    diagnosis_1 = PracticeDiagnosis(
        understands=[
            "iteration",
        ],
        missing_concepts=[
            "dictionary key access",
        ],
        misconception=(
            "Dictionary değerine object attribute "
            "gibi erişmeye çalışıyor."
        ),
        needs_concept_teaching=True,
        confidence="high",
    )

    mentor_decision_1 = PracticeMentorDecision(
        assistance_level="GUIDE",
        support_strategy="focus",
        reason=(
            "Junior dictionary access konusunda "
            "yönlendirmeye ihtiyaç duyuyor."
        ),
        needs_micro_check=False,
    )

    mentor_support_1 = PracticeMentorSupport(
        message="Dictionary key access açıklaması.",
        micro_check=(
            "car = {'year': 2020} sözlüğünde "
            "year değerine nasıl erişirsin?"
        ),
    )

    saved_1 = database.save_practice_attempt(
        attempt=attempt_1,
        validation=validation_1,
        diagnosis=diagnosis_1,
        mentor_decision=mentor_decision_1,
        mentor_support=mentor_support_1,
    )

    # --------------------------------------------------
    # ATTEMPT 2
    # --------------------------------------------------

    attempt_2 = PracticeAttemptRequest(
        learner_id="learner-001",
        challenge_id="challenge-001",
        answer=(
            "count = 2\n"
            "print(count)"
        ),
        execution_output="2",
        execution_error=None,
    )

    validation_2 = PracticeAttemptValidation(
        success=True,
        feedback="Challenge başarıyla tamamlandı.",
    )

    saved_2 = database.save_practice_attempt(
        attempt=attempt_2,
        validation=validation_2,
        diagnosis=None,
        mentor_decision=None,
    )

    # --------------------------------------------------
    # SAVE ASSERTIONS
    # --------------------------------------------------

    assert saved_1.attempt_number == 1
    assert saved_2.attempt_number == 2

    assert saved_1.attempt_id
    assert saved_2.attempt_id

    assert saved_1.attempt_id != saved_2.attempt_id


    # --------------------------------------------------
    # LOAD
    # --------------------------------------------------

    loaded_attempts = database.get_practice_attempts(
        learner_id="learner-001",
        challenge_id="challenge-001",
    )

    assert len(loaded_attempts) == 2

    first = loaded_attempts[0]
    second = loaded_attempts[1]

    # Attempt sırası korunmalı.
    assert first.attempt_number == 1
    assert second.attempt_number == 2

    # İlk attempt başarısızdı.
    assert first.validation.success is False

    assert (
        "dictionary key access"
        in first.diagnosis.missing_concepts
    )

    assert (
        first.mentor_decision.assistance_level
        == "GUIDE"
    )

    assert (
        first.mentor_decision.support_strategy
        == "focus"
    )

    assert first.mentor_support is not None

    assert (
        first.mentor_support.message
        == "Dictionary key access açıklaması."
    )
    
    assert (
        "year değerine"
        in first.mentor_support.micro_check
    )

    # İkinci attempt başarılıydı.
    assert second.validation.success is True

    # Başarılı attempt için henüz diagnosis/mentor
    # kararı üretmedik.
    assert second.diagnosis is None
    assert second.mentor_decision is None

    # --------------------------------------------------
    # GET SINGLE ATTEMPT BY ID
    # --------------------------------------------------

    loaded_single = database.get_practice_attempt_by_id(
        attempt_id=saved_1.attempt_id,
        learner_id="learner-001",
    )

    assert loaded_single is not None

    assert (
        loaded_single.attempt_id
        == saved_1.attempt_id
    )

    assert loaded_single.mentor_support is not None

    assert (
        "year değerine"
        in loaded_single.mentor_support.micro_check
    )

    wrong_owner = database.get_practice_attempt_by_id(
    attempt_id=saved_1.attempt_id,
    learner_id="another-learner",
    )
    
    assert wrong_owner is None

def test_get_practice_attempts_by_skill_across_challenges(
    tmp_path,
):

    database.DATABASE_PATH = tmp_path / "test.db"
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )

    # --------------------------------------------------
    # CHALLENGE 1
    # --------------------------------------------------

    challenge_1 = PracticeChallenge(
        challenge_id="challenge-001",
        skill_name="python_data_structures",
        difficulty="easy",
        challenge_type="code",
        title="Challenge 1",
        instructions="Test.",
        starter_code=None,
    )

    database.save_practice_challenge(
        learner_id="learner-001",
        record=PracticeChallengeRecord(
            challenge=challenge_1,
            expected_outcome="2",
        ),
    )

    # --------------------------------------------------
    # CHALLENGE 2
    # --------------------------------------------------

    challenge_2 = PracticeChallenge(
        challenge_id="challenge-002",
        skill_name="python_data_structures",
        difficulty="easy",
        challenge_type="code",
        title="Challenge 2",
        instructions="Test.",
        starter_code=None,
    )

    database.save_practice_challenge(
        learner_id="learner-001",
        record=PracticeChallengeRecord(
            challenge=challenge_2,
            expected_outcome="3",
        ),
    )

    # --------------------------------------------------
    # ATTEMPT CHALLENGE 1
    # --------------------------------------------------

    database.save_practice_attempt(
        attempt=PracticeAttemptRequest(
            learner_id="learner-001",
            challenge_id="challenge-001",
            answer="print(2)",
            execution_output="2",
            execution_error=None,
        ),
        validation=PracticeAttemptValidation(
            success=True,
            feedback="Başarılı.",
        ),
    )

    # --------------------------------------------------
    # ATTEMPT CHALLENGE 2
    # --------------------------------------------------

    database.save_practice_attempt(
        attempt=PracticeAttemptRequest(
            learner_id="learner-001",
            challenge_id="challenge-002",
            answer="print(1)",
            execution_output="1",
            execution_error=None,
        ),
        validation=PracticeAttemptValidation(
            success=False,
            feedback="Yanlış sonuç.",
        ),
    )

    history = database.get_practice_attempts_by_skill(
        learner_id="learner-001",
        skill_name="python_data_structures",
    )

    assert len(history) == 2

    assert (
        history[0].attempt.challenge_id
        == "challenge-001"
    )

    assert history[0].validation.success is True

    assert (
        history[1].attempt.challenge_id
        == "challenge-002"
    )

    assert history[1].validation.success is False