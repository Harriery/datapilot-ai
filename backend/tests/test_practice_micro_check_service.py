from unittest.mock import patch

from backend.app.models import (
    PracticeAttemptRequest,
    PracticeAttemptValidation,
    PracticeAttemptRecord,
    PracticeDiagnosis,
    PracticeMentorDecision,
    PracticeMentorSupport,
    PracticeMicroCheckRequest,
    PracticeMicroCheckValidation,
    PracticeMicroCheckAttemptRecord,
    PracticeMicroCheckSupport,
)

from backend.app.practice_micro_check_service import (
    review_practice_micro_check,
)


def test_correct_micro_check_returns_to_challenge():

    request = PracticeMicroCheckRequest(
        learner_id="learner-001",
        attempt_id="attempt-001",
        answer="car['year']",
    )

    attempt_record = PracticeAttemptRecord(
        attempt_id="attempt-001",
        attempt_number=1,
        attempt=PracticeAttemptRequest(
            learner_id="learner-001",
            challenge_id="challenge-001",
            answer="wrong",
        ),
        validation=PracticeAttemptValidation(
            success=False,
            feedback="Başarısız.",
        ),
        diagnosis=PracticeDiagnosis(
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
            needs_concept_teaching=True,
            confidence="high",
        ),
        mentor_decision=PracticeMentorDecision(
            assistance_level="TEACH",
            support_strategy="concept_explanation",
            reason="Kavram desteği gerekiyor.",
            needs_micro_check=True,
        ),
        mentor_support=PracticeMentorSupport(
            message="Dictionary key access açıklaması.",
            micro_check=(
                "car = {'year': 2020}. "
                "year değerine nasıl erişirsin?"
            ),
        ),
    )

    validation = PracticeMicroCheckValidation(
        success=True,
        feedback="Doğru.",
    )

    with patch(
        "backend.app.practice_micro_check_service."
        "database.get_practice_attempt_by_id",
        return_value=attempt_record,
    ), patch(
        "backend.app.practice_micro_check_service."
        "database.get_learner_profile_by_id",
        return_value={
            "learner_id": "learner-001",
            "preferred_language": "tr",
        },
    ), patch(
        "backend.app.practice_micro_check_service."
        "evaluate_practice_micro_check",
        return_value=validation,
    ) as mock_evaluate, patch(
        "backend.app.practice_micro_check_service."
        "database.save_practice_micro_check_attempt",
    ) as mock_save:

        result = review_practice_micro_check(
            request=request
        )

    mock_save.assert_called_once_with(
        learner_id="learner-001",
        attempt_id="attempt-001",
        answer="car['year']",
        validation=validation,
    )
    assert result.validation.success is True

    assert (
        result.next_action
        == "return_to_challenge"
    )
    assert result.additional_support is None

    mock_evaluate.assert_called_once_with(
        question=(
            "car = {'year': 2020}. "
            "year değerine nasıl erişirsin?"
        ),
        answer="car['year']",
        primary_concept_id="dictionary_key_access",
        preferred_language="tr",
    )

def test_wrong_micro_check_returns_more_support():

    request = PracticeMicroCheckRequest(
        learner_id="learner-001",
        attempt_id="attempt-001",
        answer="car.year",
    )

    attempt_record = PracticeAttemptRecord(
        attempt_id="attempt-001",
        attempt_number=1,
        attempt=PracticeAttemptRequest(
            learner_id="learner-001",
            challenge_id="challenge-001",
            answer="wrong",
        ),
        validation=PracticeAttemptValidation(
            success=False,
            feedback="Başarısız.",
        ),
        diagnosis=PracticeDiagnosis(
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
            needs_concept_teaching=True,
            confidence="high",
        ),
        mentor_decision=PracticeMentorDecision(
            assistance_level="TEACH",
            support_strategy="concept_explanation",
            reason="Kavram desteği gerekiyor.",
            needs_micro_check=True,
        ),
        mentor_support=PracticeMentorSupport(
            message="Dictionary key access açıklaması.",
            micro_check=(
                "car = {'year': 2020}. "
                "year değerine nasıl erişirsin?"
            ),
        ),
    )

    validation = PracticeMicroCheckValidation(
        success=False,
        feedback=(
            "Bu ifade dictionary key access "
            "kavramını doğru göstermiyor."
        ),
    )

    saved_micro_check_attempt = (
        PracticeMicroCheckAttemptRecord(
            micro_check_attempt_id="micro-001",
            learner_id="learner-001",
            attempt_id="attempt-001",
            micro_check_attempt_number=1,
            answer="car.year",
            validation=validation,
        )
    )

    additional_support = PracticeMicroCheckSupport(
        message=(
            "Dictionary erişim biçimini tekrar düşün. "
            "Bir dictionary'deki key, object attribute "
            "ile aynı şekilde kullanılmaz."
        )
    )

    with patch(
        "backend.app.practice_micro_check_service."
        "database.get_practice_attempt_by_id",
        return_value=attempt_record,
    ), patch(
        "backend.app.practice_micro_check_service."
        "database.get_learner_profile_by_id",
        return_value={
            "learner_id": "learner-001",
            "preferred_language": "tr",
        },
    ), patch(
        "backend.app.practice_micro_check_service."
        "evaluate_practice_micro_check",
        return_value=validation,
    ), patch(
    "backend.app.practice_micro_check_service."
    "database.save_practice_micro_check_attempt",
    return_value=saved_micro_check_attempt,
    ), patch(
        "backend.app.practice_micro_check_service."
        "generate_practice_micro_check_support",
        return_value=additional_support,
    ) as mock_support:
            result = review_practice_micro_check(
            request=request
        )
    assert result.validation.success is False

    assert (
        result.next_action
        == "more_support"
    )

    assert result.additional_support is not None

    assert (
        result.additional_support.message
        == additional_support.message
    )

    mock_support.assert_called_once_with(
        question=(
            "car = {'year': 2020}. "
            "year değerine nasıl erişirsin?"
        ),
        answer="car.year",
        primary_concept_id="dictionary_key_access",
        micro_check_attempt_number=1,
        preferred_language="tr",
    )