from unittest.mock import patch

from backend.app.models import (
    PracticeAttemptRequest,
    PracticeAttemptValidation,
    PracticeAttemptRecord,
    PracticeChallenge,
    PracticeChallengeRecord,
    PracticeDiagnosis,
    PracticeMentorDecision,
    PracticeMentorSupport,
)

from backend.app.practice_review_service import (
    review_practice_attempt,
    get_practice_attempt_assistance_level,
    get_practice_evidence_type,
    record_practice_learning_evidence,
)


# ==================================================
# SUCCESSFUL ATTEMPT
# ==================================================


def test_review_practice_attempt_success_skips_ai():

    attempt = PracticeAttemptRequest(
        learner_id="learner-001",
        challenge_id="challenge-001",
        answer="print(2)",
        execution_output="2",
        execution_error=None,
    )

    validation = PracticeAttemptValidation(
        success=True,
        feedback="Challenge başarıyla tamamlandı.",
    )

    challenge = PracticeChallenge(
        challenge_id="challenge-001",
        skill_name="python_data_structures",
        difficulty="easy",
        challenge_type="code",
        title="Test challenge",
        instructions="Test.",
        starter_code=None,
    )

    challenge_record = PracticeChallengeRecord(
        challenge=challenge,
        expected_outcome="2",
    )

    saved_record = PracticeAttemptRecord(
        attempt_id="attempt-001",
        attempt_number=1,
        attempt=attempt,
        validation=validation,
        diagnosis=None,
        mentor_decision=None,
    )

    with patch(
        "backend.app.practice_review_service."
        "validate_practice_attempt",
        return_value=validation,
    ), patch(
        "backend.app.practice_review_service."
        "database.get_practice_challenge",
        return_value=challenge_record,
    ), patch(
        "backend.app.practice_review_service."
        "database.get_practice_attempts_by_skill",
        return_value=[],
    ), patch(
        "backend.app.practice_review_service."
        "diagnose_practice_attempt",
    ) as mock_diagnose, patch(
        "backend.app.practice_review_service."
        "generate_practice_mentor_support",
    ) as mock_support, patch(
        "backend.app.practice_review_service."
        "database.save_practice_attempt",
        return_value=saved_record,
    ) as mock_save, patch(
        "backend.app.practice_review_service."
        "record_practice_learning_evidence",
        return_value="learning",
    ) as mock_evidence:

        result = review_practice_attempt(
            attempt=attempt
        )

    assert result.validation.success is True

    assert result.attempt_id == "attempt-001"
    assert result.attempt_number == 1

    assert result.diagnosis is None
    assert result.mentor_decision is None
    assert result.mentor_support is None

    mock_diagnose.assert_not_called()
    mock_support.assert_not_called()

    mock_save.assert_called_once_with(
        attempt=attempt,
        validation=validation,
        diagnosis=None,
        mentor_decision=None,
    )

    mock_evidence.assert_called_once_with(
        learner_id="learner-001",
        skill_name="python_data_structures",
        challenge_id="challenge-001",
        challenge_type="code",
        success=True,
        assistance_level="NONE",
    )


# ==================================================
# FAILED ATTEMPT
# ==================================================


def test_review_practice_attempt_failure_uses_diagnosis_and_policy():

    attempt = PracticeAttemptRequest(
        learner_id="learner-001",
        challenge_id="challenge-001",
        answer=(
            "for record in records:\n"
            "    print(record.city)"
        ),
        execution_output=None,
        execution_error=(
            "AttributeError: 'dict' object "
            "has no attribute 'city'"
        ),
    )

    validation = PracticeAttemptValidation(
        success=False,
        feedback="Kod çalışırken bir hata oluştu.",
    )

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

    diagnosis = PracticeDiagnosis(
        understood_concept_ids=[
            "iteration",
        ],
        missing_concept_ids=[
            "dictionary_key_access",
        ],
        primary_missing_concept_id=(
            "dictionary_key_access"
        ),
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

    mentor_decision = PracticeMentorDecision(
        assistance_level="TEACH",
        support_strategy="concept_explanation",
        reason=(
            "Junior dictionary key access "
            "kavramını öğrenmeli."
        ),
        needs_micro_check=True,
    )

    mentor_support = PracticeMentorSupport(
        message=(
            "Dictionary içindeki değerlere key üzerinden "
            "erişildiğini hatırla."
        ),
        micro_check=(
            "person = {'age': 30} yapısında "
            "30 değerine nasıl ulaşırsın?"
        ),
    )

    saved_record = PracticeAttemptRecord(
        attempt_id="attempt-002",
        attempt_number=2,
        attempt=attempt,
        validation=validation,
        diagnosis=diagnosis,
        mentor_decision=mentor_decision,
        mentor_support=mentor_support,
    )

    with patch(
        "backend.app.practice_review_service."
        "validate_practice_attempt",
        return_value=validation,
    ), patch(
        "backend.app.practice_review_service."
        "database.get_practice_challenge",
        return_value=challenge_record,
    ), patch(
        "backend.app.practice_review_service."
        "diagnose_practice_attempt",
        return_value=diagnosis,
    ) as mock_diagnose, patch(
        "backend.app.practice_review_service."
        "database.get_practice_attempts_by_skill",
        return_value=[],
    ) as mock_history, patch(
        "backend.app.practice_review_service."
        "database.get_skill_state",
        return_value={
            "status": "learning"
        },
    ), patch(
        "backend.app.practice_review_service."
        "database.get_learner_profile_by_id",
        return_value={
            "learner_id": "learner-001",
            "preferred_language": "tr",
        },
    ) as mock_get_profile, patch(
        "backend.app.practice_review_service."
        "choose_practice_mentor_decision",
        return_value=mentor_decision,
    ) as mock_policy, patch(
        "backend.app.practice_review_service."
        "generate_practice_mentor_support",
        return_value=mentor_support,
    ) as mock_support, patch(
        "backend.app.practice_review_service."
        "database.save_practice_attempt",
        return_value=saved_record,
    ) as mock_save, patch(
        "backend.app.practice_review_service."
        "record_practice_learning_evidence",
        return_value="learning",
    ) as mock_evidence:

        result = review_practice_attempt(
            attempt=attempt
        )

    assert result.validation.success is False

    assert (
        result.diagnosis.primary_missing_concept_id
        == "dictionary_key_access"
    )

    assert (
        result.mentor_decision.assistance_level
        == "TEACH"
    )

    assert (
        result.mentor_decision.support_strategy
        == "concept_explanation"
    )

    assert result.mentor_support == mentor_support

    mock_diagnose.assert_called_once_with(
        challenge=challenge,
        attempt=attempt,
        validation=validation,
    )

    mock_history.assert_called_once_with(
        learner_id="learner-001",
        skill_name="python_data_structures",
    )

    mock_get_profile.assert_called_once_with(
        "learner-001"
    )

    mock_policy.assert_called_once_with(
        skill_status="learning",
        diagnosis=diagnosis,
        previous_attempts=[],
        current_challenge_id="challenge-001",
    )

    mock_support.assert_called_once_with(
        challenge=challenge,
        attempt=attempt,
        diagnosis=diagnosis,
        mentor_decision=mentor_decision,
        preferred_language="tr",
    )

    mock_save.assert_called_once_with(
        attempt=attempt,
        validation=validation,
        diagnosis=diagnosis,
        mentor_decision=mentor_decision,
        mentor_support=mentor_support,
    )

    mock_evidence.assert_called_once_with(
        learner_id="learner-001",
        skill_name="python_data_structures",
        challenge_id="challenge-001",
        challenge_type="code",
        success=False,
        assistance_level="NONE",
    )


# ==================================================
# PRACTICE ATTEMPT ASSISTANCE LEVEL
# ==================================================


def test_first_practice_attempt_has_no_assistance():

    result = get_practice_attempt_assistance_level(
        previous_attempts=[],
        current_challenge_id="challenge-001",
    )

    assert result == "NONE"


def test_practice_attempt_uses_previous_support_level():

    previous_request = PracticeAttemptRequest(
        learner_id="learner-001",
        challenge_id="challenge-001",
        answer="wrong",
    )

    previous_validation = PracticeAttemptValidation(
        success=False,
        feedback="Başarısız.",
    )

    previous_decision = PracticeMentorDecision(
        assistance_level="TEACH",
        support_strategy="concept_explanation",
        reason="Kavram desteği gerekiyor.",
        needs_micro_check=True,
    )

    previous_record = PracticeAttemptRecord(
        attempt_id="attempt-001",
        attempt_number=1,
        attempt=previous_request,
        validation=previous_validation,
        mentor_decision=previous_decision,
    )

    result = get_practice_attempt_assistance_level(
        previous_attempts=[
            previous_record
        ],
        current_challenge_id="challenge-001",
    )

    assert result == "TEACH"


# ==================================================
# PRACTICE EVIDENCE TYPE
# ==================================================


def test_practice_code_maps_to_application_evidence():

    result = get_practice_evidence_type(
        "code"
    )

    assert result == "application"


# ==================================================
# PRACTICE LEARNING EVIDENCE
# ==================================================


def test_record_practice_learning_evidence():

    with patch(
        "backend.app.practice_review_service."
        "database.record_learning_evidence",
    ) as mock_record, patch(
        "backend.app.practice_review_service."
        "refresh_skill_status",
        return_value="learning",
    ) as mock_refresh:

        status = record_practice_learning_evidence(
            learner_id="learner-001",
            skill_name="python_data_structures",
            challenge_id="challenge-001",
            challenge_type="code",
            success=True,
            assistance_level="TEACH",
        )

    assert status == "learning"

    mock_record.assert_called_once_with(
        learner_id="learner-001",
        skill_name="python_data_structures",
        assistance_level="TEACH",
        success=True,
        evidence_type="application",
        note=(
            "Practice challenge challenge-001 "
            "deterministic validation sonucu: "
            "success."
        ),
        session_id=None,
    )

    mock_refresh.assert_called_once_with(
        learner_id="learner-001",
        skill_name="python_data_structures",
    )