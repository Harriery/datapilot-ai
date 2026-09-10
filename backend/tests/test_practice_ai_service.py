from unittest.mock import patch, MagicMock

from backend.app.models import (
    PracticeChallenge,
    PracticeAttemptRequest,
    PracticeAttemptValidation,
    PracticeDiagnosis,
    PracticeMentorDecision,
    PracticeMentorSupport,
    PracticeMicroCheckValidation,
    PracticeMicroCheckSupport,
)

from backend.app.practice_ai_service import (
    diagnose_practice_attempt,
    generate_practice_mentor_support,
    evaluate_practice_micro_check,
    generate_practice_micro_check_support,
)


# ==================================================
# PRACTICE DIAGNOSIS
# ==================================================


def test_diagnose_practice_attempt_returns_structured_diagnosis():

    challenge = PracticeChallenge(
        challenge_id="challenge-001",
        skill_name="python_data_structures",
        difficulty="easy",
        challenge_type="code",
        title="Eksik city değerlerini bul",
        instructions="Eksik city değerlerini bul.",
        starter_code="records = []",
    )

    attempt = PracticeAttemptRequest(
        learner_id="learner-001",
        challenge_id="challenge-001",
        answer=(
            "for record in records:\n"
            "    if record.city is None:\n"
            "        print(record)"
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

    fake_diagnosis = PracticeDiagnosis(
        understood_concept_ids=[
            "iteration",
            "conditional_logic",
            "none_check",
        ],
        missing_concept_ids=[
            "dictionary_key_access",
            "counting_matches",
            "output_result",
        ],
        primary_missing_concept_id=(
            "dictionary_key_access"
        ),
        understands=[
            "iteration",
            "conditional logic",
            "None checking",
        ],
        missing_concepts=[
            "dictionary key access",
            "counting matches",
            "printing the final result",
        ],
        misconception=(
            "Dictionary değerine object attribute "
            "gibi erişmeye çalışıyor."
        ),
        needs_concept_teaching=True,
        confidence="high",
    )

    fake_response = MagicMock()
    fake_response.output_parsed = fake_diagnosis

    with patch(
        "backend.app.practice_ai_service.client.responses.parse",
        return_value=fake_response,
    ) as mock_parse:

        result = diagnose_practice_attempt(
            challenge=challenge,
            attempt=attempt,
            validation=validation,
        )

    assert result == fake_diagnosis

    assert "iteration" in (
        result.understood_concept_ids
    )

    assert "dictionary_key_access" in (
        result.missing_concept_ids
    )

    assert (
        result.primary_missing_concept_id
        == "dictionary_key_access"
    )

    assert result.needs_concept_teaching is True
    assert result.confidence == "high"

    mock_parse.assert_called_once()


# ==================================================
# PRACTICE MENTOR SUPPORT
# ==================================================


def test_generate_practice_mentor_support():

    challenge = PracticeChallenge(
        challenge_id="challenge-001",
        skill_name="python_data_structures",
        difficulty="easy",
        challenge_type="code",
        title="Eksik city değerlerini bul",
        instructions="Eksik city değerlerini bul.",
        starter_code="records = []",
    )

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
        needs_concept_teaching=False,
        confidence="high",
    )

    mentor_decision = PracticeMentorDecision(
        assistance_level="NUDGE",
        support_strategy="recall",
        reason=(
            "Junior bu skill'i daha önce "
            "başarıyla kullandı."
        ),
        needs_micro_check=False,
    )

    fake_support = PracticeMentorSupport(
        message=(
            "Daha önce dictionary içindeki değerlere "
            "key kullanarak erişmiştik. "
            "Veri yapısını tekrar düşün."
        ),
        micro_check=None,
    )

    fake_response = MagicMock()
    fake_response.output_parsed = fake_support

    with patch(
        "backend.app.practice_ai_service.client.responses.parse",
        return_value=fake_response,
    ) as mock_parse:

        result = generate_practice_mentor_support(
            challenge=challenge,
            attempt=attempt,
            diagnosis=diagnosis,
            mentor_decision=mentor_decision,
        )

    assert result == fake_support
    assert "key" in result.message
    assert result.micro_check is None

    mock_parse.assert_called_once()

# ==================================================
# PRACTICE MICRO-CHECK EVALUATION
# ==================================================


def test_evaluate_practice_micro_check():

    fake_validation = PracticeMicroCheckValidation(
        success=True,
        feedback="Doğru. Şimdi ana challenge'a geri dön.",
    )

    fake_response = MagicMock()
    fake_response.output_parsed = fake_validation

    with patch(
        "backend.app.practice_ai_service.client.responses.parse",
        return_value=fake_response,
    ) as mock_parse:

        result = evaluate_practice_micro_check(
            question=(
                "car = {'make': 'Toyota', 'year': 2020}. "
                "'year' değerine nasıl erişirsin?"
            ),
            answer="car['year']",
            primary_concept_id="dictionary_key_access",
            preferred_language="tr",
        )

    assert result.success is True

    assert (
        result.feedback
        == "Doğru. Şimdi ana challenge'a geri dön."
    )

    mock_parse.assert_called_once()

def test_generate_practice_micro_check_support():

    fake_support = PracticeMicroCheckSupport(
        message=(
            "Bir dictionary içindeki değere erişirken "
            "veri yapısının nasıl çalıştığını tekrar düşün."
        )
    )

    fake_response = MagicMock()
    fake_response.output_parsed = fake_support

    with patch(
        "backend.app.practice_ai_service.client.responses.parse",
        return_value=fake_response,
    ) as mock_parse:

        result = generate_practice_micro_check_support(
            question=(
                "vehicle sözlüğünde wheels değerine "
                "nasıl erişirsin?"
            ),
            answer="vehicle.wheels",
            primary_concept_id="dictionary_key_access",
            micro_check_attempt_number=1,
            preferred_language="tr",
        )

    assert result == fake_support
    assert result.message

    mock_parse.assert_called_once()