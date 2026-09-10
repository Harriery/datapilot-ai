import backend.app.database as database

from backend.app.models import (
    PracticeChallenge,
    PracticeChallengeRecord,
)


def test_save_and_get_practice_challenge(tmp_path):

    database.DATABASE_PATH = tmp_path / "test.db"
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )

    challenge = PracticeChallenge(
        challenge_id="challenge-001",
        skill_name="python_data_structures",
        difficulty="easy",
        challenge_type="code",
        title="Eksik city değerlerini bul",
        instructions=(
            "Records listesinde city değeri eksik "
            "olan kayıtları bul."
        ),
        starter_code="records = []",
    )

    record = PracticeChallengeRecord(
        challenge=challenge,
        expected_outcome="Eksik city kayıtlarının sayısı 2 olmalı.",
    )

    database.save_practice_challenge(
        learner_id="learner-001",
        record=record,
    )

    loaded_record = database.get_practice_challenge(
        challenge_id="challenge-001",
        learner_id="learner-001",
    )

    assert loaded_record is not None

    assert (
        loaded_record.challenge.challenge_id
        == "challenge-001"
    )

    assert (
        loaded_record.challenge.skill_name
        == "python_data_structures"
    )

    assert loaded_record.challenge.difficulty == "easy"
    assert loaded_record.challenge.challenge_type == "code"

    assert loaded_record.expected_outcome == (
        "Eksik city kayıtlarının sayısı 2 olmalı."
    )


def test_get_practice_challenge_returns_none_for_wrong_learner(
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

    database.insert_learner_profile(
        learner_id="learner-002",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
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

    record = PracticeChallengeRecord(
        challenge=challenge,
        expected_outcome="Sonuç 2 olmalı.",
    )

    database.save_practice_challenge(
        learner_id="learner-001",
        record=record,
    )

    loaded_record = database.get_practice_challenge(
        challenge_id="challenge-001",
        learner_id="learner-002",
    )

    assert loaded_record is None