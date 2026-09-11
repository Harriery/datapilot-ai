from unittest.mock import patch

from backend.app.models import (
    LearnerProgressResponse,
    LearnerSkillProgress,
    PracticeRecommendation,
    PracticeRecommendationResponse,
    PracticeAttemptRequest,
    PracticeChallengeRecord,
    PracticeChallenge,
    PracticeValidationSpec,
    
)
import pytest

import backend.app.database as database

from backend.app.practice_service import (
    get_practice_difficulty,
    get_practice_recommendation,
    create_practice_challenge,
    validate_practice_attempt,
    get_python_data_structure_variant,
)

def test_get_practice_difficulty_for_new_skill():
    result = get_practice_difficulty("new")

    assert result == "foundation"


def test_get_practice_difficulty_for_learning_skill():
    result = get_practice_difficulty("learning")

    assert result == "easy"


def test_get_practice_difficulty_for_practicing_skill():
    result = get_practice_difficulty("practicing")

    assert result == "medium"


def test_get_practice_difficulty_for_comfortable_skill():
    result = get_practice_difficulty("comfortable")

    assert result == "hard"

def test_get_practice_recommendation_selects_highest_priority_skill():

    fake_progress = LearnerProgressResponse(
        learner_id="learner-001",
        skills=[
            LearnerSkillProgress(
                skill_name="null_analysis",
                status="practicing",
                attempts=4,
                successful_attempts=4,
                success_rate=1.0,
                last_assistance_level="NUDGE",
                independence_trend="improving",
                practice_priority="low",
            ),
            LearnerSkillProgress(
                skill_name="python_data_structures",
                status="learning",
                attempts=2,
                successful_attempts=1,
                success_rate=0.5,
                last_assistance_level="GUIDE",
                independence_trend="stable",
                practice_priority="high",
            ),
            LearnerSkillProgress(
                skill_name="duplicate_analysis",
                status="learning",
                attempts=2,
                successful_attempts=2,
                success_rate=1.0,
                last_assistance_level="NUDGE",
                independence_trend="improving",
                practice_priority="medium",
            ),
        ],
    )

    with patch(
        "backend.app.practice_service.get_learner_progress",
        return_value=fake_progress,
    ) as mock_get_progress:

        result = get_practice_recommendation(
            learner_id="learner-001"
        )

    assert result.learner_id == "learner-001"
    assert result.recommendation is not None

    recommendation = result.recommendation

    assert recommendation.skill_name == "python_data_structures"
    assert recommendation.priority == "high"
    assert recommendation.difficulty == "easy"

    mock_get_progress.assert_called_once_with(
        learner_id="learner-001"
    )

def test_get_practice_recommendation_returns_none_when_no_skill_needs_practice():

    fake_progress = LearnerProgressResponse(
        learner_id="learner-001",
        skills=[
            LearnerSkillProgress(
                skill_name="null_analysis",
                status="comfortable",
                attempts=6,
                successful_attempts=6,
                success_rate=1.0,
                last_assistance_level="NONE",
                independence_trend="stable",
                practice_priority="none",
            ),
            LearnerSkillProgress(
                skill_name="duplicate_analysis",
                status="comfortable",
                attempts=5,
                successful_attempts=5,
                success_rate=1.0,
                last_assistance_level="NONE",
                independence_trend="improving",
                practice_priority="none",
            ),
        ],
    )

    with patch(
        "backend.app.practice_service.get_learner_progress",
        return_value=fake_progress,
    ):

        result = get_practice_recommendation(
            learner_id="learner-001"
        )

    assert result.learner_id == "learner-001"
    assert result.recommendation is None

def test_get_practice_recommendation_uses_lower_success_rate_as_tiebreaker():

    fake_progress = LearnerProgressResponse(
        learner_id="learner-001",
        skills=[
            LearnerSkillProgress(
                skill_name="duplicate_analysis",
                status="learning",
                attempts=4,
                successful_attempts=4,
                success_rate=1.0,
                last_assistance_level="NUDGE",
                independence_trend="improving",
                practice_priority="medium",
            ),
            LearnerSkillProgress(
                skill_name="python_data_structures",
                status="learning",
                attempts=5,
                successful_attempts=3,
                success_rate=0.6,
                last_assistance_level="GUIDE",
                independence_trend="stable",
                practice_priority="medium",
            ),
        ],
    )

    with patch(
        "backend.app.practice_service.get_learner_progress",
        return_value=fake_progress,
    ):

        result = get_practice_recommendation(
            learner_id="learner-001"
        )

    assert result.recommendation is not None
    assert (
        result.recommendation.skill_name
        == "python_data_structures"
    )
    assert result.recommendation.priority == "medium"


def test_create_practice_challenge_for_python_data_structures():

    fake_recommendation = PracticeRecommendationResponse(
        learner_id="learner-001",
        recommendation=PracticeRecommendation(
            skill_name="python_data_structures",
            priority="medium",
            difficulty="easy",
            reason=(
                "python_data_structures skill'i "
                "learning seviyesinde ve "
                "practice priority medium."
            ),
        ),
    )

    with patch(
        "backend.app.practice_service.get_practice_recommendation",
        return_value=fake_recommendation,
    ), patch(
        "backend.app.practice_service."
        "database.get_practice_challenge_count_by_skill",
        return_value=0,
    ), patch(
        "backend.app.practice_service.database.save_practice_challenge",
    ) as mock_save:

        result = create_practice_challenge(
            learner_id="learner-001"
        )

    assert result.learner_id == "learner-001"

    challenge = result.challenge

    assert challenge.skill_name == "python_data_structures"
    assert challenge.difficulty == "easy"
    assert challenge.challenge_type == "code"
    assert challenge.title == "Eksik city değerlerini bul"

    assert challenge.starter_code is not None
    assert "records" in challenge.starter_code

    assert challenge.challenge_id

    mock_save.assert_called_once()

    save_args = mock_save.call_args.kwargs

    assert save_args["learner_id"] == "learner-001"

    record = save_args["record"]

    assert record.challenge.challenge_id == challenge.challenge_id
    assert record.challenge.skill_name == "python_data_structures"

    # Bu bilgi PUBLIC challenge içinde yok.
    assert not hasattr(
        record.challenge,
        "expected_outcome",
    )

    # Ama INTERNAL record içinde var.
    assert "2" in record.expected_outcome



def test_create_practice_challenge_raises_error_when_no_recommendation():

    fake_recommendation = PracticeRecommendationResponse(
        learner_id="learner-001",
        recommendation=None,
    )

    with patch(
        "backend.app.practice_service.get_practice_recommendation",
        return_value=fake_recommendation,
    ):

        try:
            create_practice_challenge(
                learner_id="learner-001"
            )

            assert False, "ValueError bekleniyordu."

        except ValueError as exc:
            assert str(exc) == (
                "Bu learner için şu anda practice recommendation yok."
            )

def test_create_practice_challenge_for_null_analysis():

    fake_recommendation = PracticeRecommendationResponse(
        learner_id="learner-001",
        recommendation=PracticeRecommendation(
            skill_name="null_analysis",
            priority="low",
            difficulty="medium",
            reason=(
                "null_analysis skill'i practicing seviyesinde "
                "ve practice priority low."
            ),
        ),
    )

    with patch(
        "backend.app.practice_service.get_practice_recommendation",
        return_value=fake_recommendation,
    ), patch(
        "backend.app.practice_service.database.save_practice_challenge",
    ) as mock_save:

        result = create_practice_challenge(
            learner_id="learner-001"
        )

    challenge = result.challenge

    assert challenge.skill_name == "null_analysis"
    assert challenge.difficulty == "medium"
    assert challenge.challenge_type == "transformation"
    assert "age" in challenge.title

    record = mock_save.call_args.kwargs["record"]

    assert "null" in record.expected_outcome.lower()


def test_create_practice_challenge_for_duplicate_analysis():

    fake_recommendation = PracticeRecommendationResponse(
        learner_id="learner-001",
        recommendation=PracticeRecommendation(
            skill_name="duplicate_analysis",
            priority="medium",
            difficulty="easy",
            reason=(
                "duplicate_analysis skill'i learning seviyesinde "
                "ve practice priority medium."
            ),
        ),
    )

    with patch(
        "backend.app.practice_service.get_practice_recommendation",
        return_value=fake_recommendation,
    ), patch(
        "backend.app.practice_service.database.save_practice_challenge",
    ) as mock_save:

        result = create_practice_challenge(
            learner_id="learner-001"
        )

    challenge = result.challenge

    assert challenge.skill_name == "duplicate_analysis"
    assert challenge.difficulty == "easy"
    assert challenge.challenge_type == "transformation"
    assert "Duplicate" in challenge.title

    record = mock_save.call_args.kwargs["record"]

    assert "duplicate" in record.expected_outcome.lower()


def test_validate_practice_attempt_returns_success():

    challenge = PracticeChallenge(
        challenge_id="challenge-001",
        skill_name="python_data_structures",
        difficulty="easy",
        challenge_type="code",
        title="Eksik city değerlerini bul",
        instructions="Eksik city değerlerini bul.",
        starter_code="records = []",
    )

    record = PracticeChallengeRecord(
        challenge=challenge,
        expected_outcome="Sonuç 2 olmalı.",
        validation_spec=PracticeValidationSpec(
            validation_type="exact_output",
            expected_output="2",
        ),
    )

    attempt = PracticeAttemptRequest(
        learner_id="learner-001",
        challenge_id="challenge-001",
        answer=(
            "count = sum("
            "1 for record in records "
            "if record['city'] is None"
            ")\nprint(count)"
        ),
        execution_output="2",
        execution_error=None,
    )

    with patch(
        "backend.app.practice_service.database.get_practice_challenge",
        return_value=record,
    ) as mock_get_challenge:

        result = validate_practice_attempt(
            attempt=attempt
        )

    assert result.success is True
    assert result.feedback == (
        "Challenge başarıyla tamamlandı."
    )

    mock_get_challenge.assert_called_once_with(
        challenge_id="challenge-001",
        learner_id="learner-001",
    )

def test_validate_practice_attempt_returns_failure_for_wrong_output():

    challenge = PracticeChallenge(
        challenge_id="challenge-001",
        skill_name="python_data_structures",
        difficulty="easy",
        challenge_type="code",
        title="Eksik city değerlerini bul",
        instructions="Eksik city değerlerini bul.",
        starter_code="records = []",
    )

    record = PracticeChallengeRecord(
        challenge=challenge,
        expected_outcome="Sonuç 2 olmalı.",
        validation_spec=PracticeValidationSpec(
            validation_type="exact_output",
            expected_output="2",
        ),
    )

    attempt = PracticeAttemptRequest(
        learner_id="learner-001",
        challenge_id="challenge-001",
        answer="print(1)",
        execution_output="1",
        execution_error=None,
    )

    with patch(
        "backend.app.practice_service.database.get_practice_challenge",
        return_value=record,
    ):

        result = validate_practice_attempt(
            attempt=attempt
        )

    assert result.success is False
    assert result.feedback == (
        "Kod çalıştı ancak beklenen sonuç elde edilmedi."
    )

def test_validate_practice_attempt_returns_failure_for_execution_error():

    challenge = PracticeChallenge(
        challenge_id="challenge-001",
        skill_name="python_data_structures",
        difficulty="easy",
        challenge_type="code",
        title="Eksik city değerlerini bul",
        instructions="Eksik city değerlerini bul.",
        starter_code="records = []",
    )

    record = PracticeChallengeRecord(
        challenge=challenge,
        expected_outcome="Sonuç 2 olmalı.",
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

    with patch(
        "backend.app.practice_service.database.get_practice_challenge",
        return_value=record,
    ):

        result = validate_practice_attempt(
            attempt=attempt
        )

    assert result.success is False
    assert result.feedback == (
        "Kod çalışırken bir hata oluştu."
    )


def test_validate_practice_attempt_raises_error_when_challenge_not_found():

    attempt = PracticeAttemptRequest(
        learner_id="learner-001",
        challenge_id="missing-challenge",
        answer="print(2)",
        execution_output="2",
        execution_error=None,
    )

    with patch(
        "backend.app.practice_service.database.get_practice_challenge",
        return_value=None,
    ):

        with pytest.raises(
            ValueError,
            match="Practice challenge bulunamadı.",
        ):
            validate_practice_attempt(
                attempt=attempt
            )

def test_validate_practice_attempt_uses_validation_spec_expected_output():

    challenge = PracticeChallenge(
        challenge_id="challenge-003",
        skill_name="python_data_structures",
        difficulty="easy",
        challenge_type="code",
        title="Test challenge",
        instructions="Sonucu yazdır.",
        starter_code=None,
    )

    record = PracticeChallengeRecord(
        challenge=challenge,
        expected_outcome="Sonuç 3 olmalı.",
        validation_spec=PracticeValidationSpec(
            validation_type="exact_output",
            expected_output="3",
        ),
    )

    attempt = PracticeAttemptRequest(
        learner_id="learner-001",
        challenge_id="challenge-003",
        answer="print(3)",
        execution_output="3",
        execution_error=None,
    )

    with patch(
        "backend.app.practice_service.database.get_practice_challenge",
        return_value=record,
    ):

        result = validate_practice_attempt(
            attempt=attempt
        )

    assert result.success is True

def test_python_data_structure_variants_are_different():

    first = get_python_data_structure_variant(0)
    second = get_python_data_structure_variant(1)
    third = get_python_data_structure_variant(2)

    assert first["title"] != second["title"]
    assert second["title"] != third["title"]

    assert first["expected_output"] == "2"
    assert second["expected_output"] == "3"


def test_python_data_structure_variants_cycle():

    first = get_python_data_structure_variant(0)
    repeated = get_python_data_structure_variant(3)

    assert repeated == first

def test_create_practice_challenge_uses_next_variant():

    fake_recommendation = PracticeRecommendationResponse(
        learner_id="learner-001",
        recommendation=PracticeRecommendation(
            skill_name="python_data_structures",
            priority="medium",
            difficulty="easy",
            reason="Practice gerekli.",
        ),
    )

    with patch(
        "backend.app.practice_service.get_practice_recommendation",
        return_value=fake_recommendation,
    ), patch(
        "backend.app.practice_service."
        "database.get_practice_challenge_count_by_skill",
        return_value=1,
    ), patch(
        "backend.app.practice_service.database.save_practice_challenge",
    ) as mock_save:

        result = create_practice_challenge(
            learner_id="learner-001"
        )

    assert result.challenge.title == (
        "Aktif kullanıcıları say"
    )

    record = mock_save.call_args.kwargs["record"]

    assert (
        record.validation_spec.expected_output
        == "3"
    )

def test_create_practice_challenge_cycles_variants_with_real_db(
    tmp_path,
):

    database.DATABASE_PATH = (
        tmp_path / "practice_variants.db"
    )

    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )

    fake_recommendation = PracticeRecommendationResponse(
        learner_id="learner-001",
        recommendation=PracticeRecommendation(
            skill_name="python_data_structures",
            priority="medium",
            difficulty="easy",
            reason="Practice gerekli.",
        ),
    )

    with patch(
        "backend.app.practice_service."
        "get_practice_recommendation",
        return_value=fake_recommendation,
    ):

        first = create_practice_challenge(
            learner_id="learner-001"
        )

        second = create_practice_challenge(
            learner_id="learner-001"
        )

    # İlk challenge ilk variant.
    assert first.challenge.title == (
        "Eksik city değerlerini bul"
    )

    # İkinci challenge otomatik olarak
    # ikinci variant olmalı.
    assert second.challenge.title == (
        "Aktif kullanıcıları say"
    )

    assert (
        first.challenge.challenge_id
        != second.challenge.challenge_id
    )

    second_record = database.get_practice_challenge(
        challenge_id=second.challenge.challenge_id,
        learner_id="learner-001",
    )

    assert second_record is not None
    assert second_record.validation_spec is not None

    assert (
        second_record.validation_spec.validation_type
        == "exact_output"
    )

    assert (
        second_record.validation_spec.expected_output
        == "3"
    )

def test_validate_null_reduction_returns_success():

    challenge = PracticeChallenge(
        challenge_id="null-001",
        skill_name="null_analysis",
        difficulty="easy",
        challenge_type="transformation",
        title="Null test",
        instructions="Null değerleri azalt.",
        input_rows=[
            {"name": "Ali", "age": 30},
            {"name": "Ayse", "age": None},
            {"name": "Mehmet", "age": None},
        ],
    )

    record = PracticeChallengeRecord(
        challenge=challenge,
        validation_spec=PracticeValidationSpec(
            validation_type="null_count_reduction",
            column="age",
        ),
    )

    attempt = PracticeAttemptRequest(
        learner_id="learner-001",
        challenge_id="null-001",
        answer="Eksik age değerlerinden birini doldurdum.",
        result_rows=[
            {"name": "Ali", "age": 30},
            {"name": "Ayse", "age": 25},
            {"name": "Mehmet", "age": None},
        ],
    )

    with patch(
        "backend.app.practice_service."
        "database.get_practice_challenge",
        return_value=record,
    ):

        result = validate_practice_attempt(
            attempt=attempt
        )

    assert result.success is True


def test_validate_null_reduction_returns_failure_when_nulls_do_not_change():

    challenge = PracticeChallenge(
        challenge_id="null-002",
        skill_name="null_analysis",
        difficulty="easy",
        challenge_type="transformation",
        title="Null test",
        instructions="Null değerleri azalt.",
        input_rows=[
            {"name": "Ali", "age": 30},
            {"name": "Ayse", "age": None},
            {"name": "Mehmet", "age": None},
        ],
    )

    record = PracticeChallengeRecord(
        challenge=challenge,
        validation_spec=PracticeValidationSpec(
            validation_type="null_count_reduction",
            column="age",
        ),
    )

    attempt = PracticeAttemptRequest(
        learner_id="learner-001",
        challenge_id="null-002",
        answer="Transformation yaptım.",
        result_rows=[
            {"name": "Ali", "age": 30},
            {"name": "Ayse", "age": None},
            {"name": "Mehmet", "age": None},
        ],
    )

    with patch(
        "backend.app.practice_service."
        "database.get_practice_challenge",
        return_value=record,
    ):

        result = validate_practice_attempt(
            attempt=attempt
        )

    assert result.success is False

def test_validate_duplicate_reduction_returns_success():

    challenge = PracticeChallenge(
        challenge_id="duplicate-001",
        skill_name="duplicate_analysis",
        difficulty="easy",
        challenge_type="transformation",
        title="Duplicate test",
        instructions="Duplicate kayıtları azalt.",
        input_rows=[
            {"id": 1, "name": "Ali"},
            {"id": 2, "name": "Ayse"},
            {"id": 2, "name": "Ayse"},
        ],
    )

    record = PracticeChallengeRecord(
        challenge=challenge,
        validation_spec=PracticeValidationSpec(
            validation_type="duplicate_count_reduction",
        ),
    )

    attempt = PracticeAttemptRequest(
        learner_id="learner-001",
        challenge_id="duplicate-001",
        answer="Duplicate kaydı kaldırdım.",
        result_rows=[
            {"id": 1, "name": "Ali"},
            {"id": 2, "name": "Ayse"},
        ],
    )

    with patch(
        "backend.app.practice_service."
        "database.get_practice_challenge",
        return_value=record,
    ):

        result = validate_practice_attempt(
            attempt=attempt
        )

    assert result.success is True


def test_validate_duplicate_reduction_returns_failure_when_duplicates_remain():

    challenge = PracticeChallenge(
        challenge_id="duplicate-002",
        skill_name="duplicate_analysis",
        difficulty="easy",
        challenge_type="transformation",
        title="Duplicate test",
        instructions="Duplicate kayıtları azalt.",
        input_rows=[
            {"id": 1, "name": "Ali"},
            {"id": 2, "name": "Ayse"},
            {"id": 2, "name": "Ayse"},
        ],
    )

    record = PracticeChallengeRecord(
        challenge=challenge,
        validation_spec=PracticeValidationSpec(
            validation_type="duplicate_count_reduction",
        ),
    )

    attempt = PracticeAttemptRequest(
        learner_id="learner-001",
        challenge_id="duplicate-002",
        answer="Transformation yaptım.",
        result_rows=[
            {"id": 1, "name": "Ali"},
            {"id": 2, "name": "Ayse"},
            {"id": 2, "name": "Ayse"},
        ],
    )

    with patch(
        "backend.app.practice_service."
        "database.get_practice_challenge",
        return_value=record,
    ):

        result = validate_practice_attempt(
            attempt=attempt
        )

    assert result.success is False