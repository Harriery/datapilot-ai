import backend.app.database as database

from backend.app.practice_review_service import (
    record_practice_learning_evidence,
)

from backend.app.progress_service import (
    get_learner_progress,
)


def test_practice_evidence_updates_real_learner_progress(
    tmp_path,
):

    # --------------------------------------------------
    # TEST DATABASE
    # --------------------------------------------------

    database.DATABASE_PATH = (
        tmp_path / "practice_progress.db"
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
        preferred_language="tr",
    )

    # --------------------------------------------------
    # INITIAL SKILL STATE
    # --------------------------------------------------

    database.insert_skill_state(
        learner_id="learner-001",
        skill_name="python_data_structures",
        status="new",
    )

    initial_state = database.get_skill_state(
        learner_id="learner-001",
        skill_name="python_data_structures",
    )

    assert initial_state["status"] == "new"
    assert initial_state["attempts"] == 0
    assert initial_state["successful_attempts"] == 0

    # --------------------------------------------------
    # ATTEMPT 1
    # --------------------------------------------------
    #
    # İlk deneme yardımsız başarısız.
    #
    # new
    # ↓
    # learning

    status_1 = record_practice_learning_evidence(
        learner_id="learner-001",
        skill_name="python_data_structures",
        challenge_id="challenge-001",
        challenge_type="code",
        success=False,
        assistance_level="NONE",
    )

    state_1 = database.get_skill_state(
        learner_id="learner-001",
        skill_name="python_data_structures",
    )

    assert status_1 == "learning"

    assert state_1["attempts"] == 1
    assert state_1["successful_attempts"] == 0
    assert state_1["status"] == "learning"

    # --------------------------------------------------
    # ATTEMPT 2
    # --------------------------------------------------
    #
    # TEACH desteğinden sonra junior başarılı.

    status_2 = record_practice_learning_evidence(
        learner_id="learner-001",
        skill_name="python_data_structures",
        challenge_id="challenge-001",
        challenge_type="code",
        success=True,
        assistance_level="TEACH",
    )

    state_2 = database.get_skill_state(
        learner_id="learner-001",
        skill_name="python_data_structures",
    )

    assert status_2 == "learning"

    assert state_2["attempts"] == 2
    assert state_2["successful_attempts"] == 1
    assert state_2["status"] == "learning"

    # --------------------------------------------------
    # ATTEMPT 3
    # --------------------------------------------------
    #
    # Üçüncü attempt ile practicing.

    status_3 = record_practice_learning_evidence(
        learner_id="learner-001",
        skill_name="python_data_structures",
        challenge_id="challenge-002",
        challenge_type="code",
        success=True,
        assistance_level="GUIDE",
    )

    state_3 = database.get_skill_state(
        learner_id="learner-001",
        skill_name="python_data_structures",
    )

    assert status_3 == "practicing"

    assert state_3["attempts"] == 3
    assert state_3["successful_attempts"] == 2
    assert state_3["status"] == "practicing"

    # --------------------------------------------------
    # REAL LEARNING EVIDENCE HISTORY
    # --------------------------------------------------

    evidence = database.get_learning_evidence_by_skill(
        learner_id="learner-001",
        skill_name="python_data_structures",
    )

    assert len(evidence) == 3

    assert evidence[0]["success"] == 0
    assert evidence[0]["assistance_level"] == "NONE"
    assert evidence[0]["evidence_type"] == "application"

    assert evidence[1]["success"] == 1
    assert evidence[1]["assistance_level"] == "TEACH"

    assert evidence[2]["success"] == 1
    assert evidence[2]["assistance_level"] == "GUIDE"

    # --------------------------------------------------
    # FRONTEND LEARNER PROGRESS
    # --------------------------------------------------
    #
    # Şimdi DB'deki ham state yerine,
    # frontend'in kullanacağı gerçek progress modelini
    # kontrol ediyoruz.

    progress = get_learner_progress(
        learner_id="learner-001"
    )

    assert progress.learner_id == "learner-001"
    assert len(progress.skills) == 1

    skill = progress.skills[0]

    assert (
        skill.skill_name
        == "python_data_structures"
    )

    assert skill.status == "practicing"

    assert skill.attempts == 3
    assert skill.successful_attempts == 2

    # 2 / 3 = 0.666...
    # progress service iki basamağa yuvarlıyor.
    assert skill.success_rate == 0.67

    # Son attempt GUIDE ile yapılmıştı.
    assert skill.last_assistance_level == "GUIDE"

    # İlk evidence NONE idi.
    # Son evidence GUIDE.
    #
    # Yani junior başlangıca göre daha fazla
    # yardıma ihtiyaç duyuyor:
    #
    # NONE  → independence score 4
    # GUIDE → independence score 2
    #
    # Bu yüzden trend = declining.
    assert skill.independence_trend == "declining"

    # practicing + declining
    # → medium practice priority
    assert skill.practice_priority == "medium"