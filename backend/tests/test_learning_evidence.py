import backend.app.database as database
import pytest


# ==================================================
# TEST 1 - LEARNING EVIDENCE KAYDETME VE OKUMA
# ==================================================
# Amaç:
# Bir learner ve skill için learning evidence kaydedilebildiğini
# ve aynı evidence'ın veritabanından doğru şekilde okunabildiğini doğrular.
def test_insert_and_get_learning_evidence(tmp_path):
    database.DATABASE_PATH = tmp_path / "test.db"
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )

    database.insert_skill_state(
        learner_id="learner-001",
        skill_name="python_dict",
        status="learning",
    )

    database.insert_skill_state(
        learner_id="learner-001",
        skill_name="null_analysis",
        status="practicing",
    )

    database.insert_learning_evidence(
        learner_id="learner-001",
        skill_name="python_dict",
        assistance_level="GUIDE",
        success=True,
        evidence_type="application",
        note="Dictionary key ve value mantığını doğru kullandı.",
    )

    database.insert_learning_evidence(
        learner_id="learner-001",
        skill_name="null_analysis",
        assistance_level="GUIDE",
        success=True,
        evidence_type="application",
        note="Null analizini yönlendirmeyle doğru yaptı.",
    )

    evidence = database.get_learning_evidence_by_skill(
        "learner-001",
        "python_dict",
    )

    assert len(evidence) == 1
    assert evidence[0]["skill_name"] == "python_dict"
    assert evidence[0]["assistance_level"] == "GUIDE"
    assert evidence[0]["success"] == 1
    assert evidence[0]["evidence_type"] == "application"


# ==================================================
# TEST 2 - BAŞARILI DENEME SONRASI SKILL STATE UPDATE
# ==================================================
# Amaç:
# success=True olduğunda:
# attempts +1
# successful_attempts +1
# olduğunu doğrular.
def test_update_skill_state_after_successful_evidence(tmp_path):
    database.DATABASE_PATH = tmp_path / "test.db"
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )

    database.insert_skill_state(
        learner_id="learner-001",
        skill_name="python_dict",
        status="learning",
    )

    database.update_skill_state_after_evidence(
        learner_id="learner-001",
        skill_name="python_dict",
        success=True,
    )

    skill = database.get_skill_state(
        "learner-001",
        "python_dict",
    )

    assert skill["attempts"] == 1
    assert skill["successful_attempts"] == 1


# ==================================================
# TEST 3 - BAŞARISIZ DENEME SONRASI SKILL STATE UPDATE
# ==================================================
# Amaç:
# success=False olduğunda:
# attempts +1
# successful_attempts değişmez
# olduğunu doğrular.
def test_update_skill_state_after_failed_evidence(tmp_path):
    database.DATABASE_PATH = tmp_path / "test.db"
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )

    database.insert_skill_state(
        learner_id="learner-001",
        skill_name="python_dict",
        status="learning",
    )

    database.update_skill_state_after_evidence(
        learner_id="learner-001",
        skill_name="python_dict",
        success=False,
    )

    skill = database.get_skill_state(
        "learner-001",
        "python_dict",
    )

    assert skill["attempts"] == 1
    assert skill["successful_attempts"] == 0


# ==================================================
# TEST 4 - TRANSACTION: İKİ TABLOYU BİRLİKTE GÜNCELLEME
# ==================================================
# Amaç:
# record_learning_evidence() çağrısının tek işlem içinde:
# 1. learning_evidence kaydı oluşturduğunu
# 2. skill_states sayaçlarını güncellediğini
# doğrular.
def test_record_learning_evidence_updates_both_tables(tmp_path):
    database.DATABASE_PATH = tmp_path / "test.db"
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )

    database.insert_skill_state(
        learner_id="learner-001",
        skill_name="python_dict",
        status="learning",
    )

    database.record_learning_evidence(
        learner_id="learner-001",
        skill_name="python_dict",
        assistance_level="GUIDE",
        success=True,
        evidence_type="application",
        note="Dictionary mantığını doğru uyguladı.",
    )

    evidence = database.get_learning_evidence_by_skill(
        "learner-001",
        "python_dict",
    )

    skill = database.get_skill_state(
        "learner-001",
        "python_dict",
    )

    assert len(evidence) == 1
    assert skill["attempts"] == 1
    assert skill["successful_attempts"] == 1


# ==================================================
# TEST 5 - TRANSACTION ROLLBACK
# ==================================================
# Amaç:
# Skill state bulunamazsa transaction'ın hata vermesini
# ve önce eklenen evidence kaydının rollback ile geri alınmasını doğrular.
#
# rollback:
# Transaction tamamlanamazsa commit edilmemiş değişiklikleri geri alır.
def test_record_learning_evidence_rolls_back_if_skill_missing(tmp_path):
    database.DATABASE_PATH = tmp_path / "test.db"
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )

    with pytest.raises(ValueError):
        database.record_learning_evidence(
            learner_id="learner-001",
            skill_name="python_dict",
            assistance_level="GUIDE",
            success=True,
            evidence_type="application",
            note="Bu kayıt rollback testinde geri alınmalı.",
        )

    evidence = database.get_learning_evidence_by_skill(
        "learner-001",
        "python_dict",
    )

    assert len(evidence) == 0





