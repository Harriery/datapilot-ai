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
)


# ==================================================
# SUCCESSFUL ATTEMPT
# ==================================================
#
# Junior challenge'ı doğru yaptıysa:
#
# validation
# ↓
# success = True
# ↓
# AI diagnosis ÇALIŞMAZ
# ↓
# mentor support ÇALIŞMAZ
# ↓
# attempt kaydedilir


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

    saved_record = PracticeAttemptRecord(
        attempt_id="attempt-001",
        attempt_number=1,
        attempt=attempt,
        validation=validation,
        diagnosis=None,
        mentor_decision=None,
    )

    with patch(
        "backend.app.practice_review_service.validate_practice_attempt",
        return_value=validation,
    ), patch(
        "backend.app.practice_review_service.diagnose_practice_attempt",
    ) as mock_diagnose, patch(
        "backend.app.practice_review_service.generate_practice_mentor_support",
    ) as mock_support, patch(
        "backend.app.practice_review_service.database.save_practice_attempt",
        return_value=saved_record,
    ) as mock_save:

        result = review_practice_attempt(
            attempt=attempt
        )

    assert result.validation.success is True

    assert result.attempt_id == "attempt-001"
    assert result.attempt_number == 1

    assert result.diagnosis is None
    assert result.mentor_decision is None
    assert result.mentor_support is None

    # Başarılı attempt'te AI'ya ihtiyacımız yok.
    mock_diagnose.assert_not_called()
    mock_support.assert_not_called()

    mock_save.assert_called_once_with(
        attempt=attempt,
        validation=validation,
        diagnosis=None,
        mentor_decision=None,
    )


# ==================================================
# FAILED ATTEMPT
# ==================================================
#
# Junior yanlış yaptıysa:
#
# validation
# ↓
# AI diagnosis
# ↓
# skill history
# ↓
# adaptive policy
# ↓
# mentor support
# ↓
# attempt kaydedilir


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
    )

    with patch(
        "backend.app.practice_review_service.validate_practice_attempt",
        return_value=validation,
    ), patch(
        "backend.app.practice_review_service.database.get_practice_challenge",
        return_value=challenge_record,
    ), patch(
        "backend.app.practice_review_service.diagnose_practice_attempt",
        return_value=diagnosis,
    ) as mock_diagnose, patch(
        "backend.app.practice_review_service.database.get_practice_attempts_by_skill",
        return_value=[],
    ) as mock_history, patch(
        "backend.app.practice_review_service.database.get_skill_state",
        return_value={
            "status": "learning"
        },
    ), patch(
        "backend.app.practice_review_service.choose_practice_mentor_decision",
        return_value=mentor_decision,
    ) as mock_policy, patch(
        "backend.app.practice_review_service.generate_practice_mentor_support",
        return_value=mentor_support,
    ) as mock_support, patch(
        "backend.app.practice_review_service.database.save_practice_attempt",
        return_value=saved_record,
    ) as mock_save:

        result = review_practice_attempt(
            attempt=attempt
        )

    assert result.validation.success is False

    assert (
        "dictionary key access"
        in result.diagnosis.missing_concepts
    )

    assert (
        result.mentor_decision.assistance_level
        == "TEACH"
    )

    assert (
        result.mentor_decision.support_strategy
        == "concept_explanation"
    )

    # Junior'ın göreceği gerçek destek.
    assert result.mentor_support == mentor_support

    assert "key" in result.mentor_support.message

    assert result.mentor_support.micro_check is not None

    # AI diagnosis çalıştı mı?
    mock_diagnose.assert_called_once_with(
        challenge=challenge,
        attempt=attempt,
        validation=validation,
    )

    # Aynı skill'in geçmişi getirildi mi?
    mock_history.assert_called_once_with(
        learner_id="learner-001",
        skill_name="python_data_structures",
    )

    # Adaptive policy çalıştı mı?
    mock_policy.assert_called_once_with(
        skill_status="learning",
        diagnosis=diagnosis,
        previous_attempts=[],
    )

    # Backend'in kararına göre gerçek mentor mesajı üretildi mi?
    mock_support.assert_called_once_with(
        challenge=challenge,
        attempt=attempt,
        diagnosis=diagnosis,
        mentor_decision=mentor_decision,
    )

    # Attempt tüm diagnosis ve decision bilgileriyle kaydedildi mi?
    mock_save.assert_called_once_with(
        attempt=attempt,
        validation=validation,
        diagnosis=diagnosis,
        mentor_decision=mentor_decision,
    )