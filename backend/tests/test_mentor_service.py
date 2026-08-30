from backend.app.mentor_service import (
    build_mentor_decision_prompt,
    generate_mentor_decision,
    get_mentor_decision_for_learner,
    detect_relevant_skill,
    get_mentor_decision_from_message,
    generate_mentor_response,
    classify_learning_evidence,
    process_learning_evidence,
    refresh_skill_status,
)
from unittest.mock import patch, MagicMock
from backend.app.models import (
    MentorDecision,
    SkillDetection,
    LearningEvidenceDecision,
)
import backend.app.database as database
import pytest


# ==================================================
# TEST - MENTOR DECISION PROMPT OLUŞTURMA
# ==================================================
# Amaç:
# Learner profile, skill state, learning evidence
# ve current message bilgilerinin prompt içine eklendiğini doğrular.
def test_build_mentor_decision_prompt():
    learner_profile = {
        "answer_length": "concise",
        "learning_style": "guided",
        "code_support": "medium",
    }

    skill_state = {
        "skill_name": "python_dict",
        "status": "learning",
        "attempts": 2,
        "successful_attempts": 1,
    }

    learning_evidence = [
        {
            "assistance_level": "GUIDE",
            "success": 1,
            "evidence_type": "application",
        }
    ]

    current_message = "Dictionary nasıl oluşturuyorduk?"

    prompt = build_mentor_decision_prompt(
        learner_profile=learner_profile,
        skill_state=skill_state,
        learning_evidence=learning_evidence,
        current_message=current_message,
    )

    assert "concise" in prompt
    assert "python_dict" in prompt
    assert "GUIDE" in prompt
    assert "Dictionary nasıl oluşturuyorduk?" in prompt


# ==================================================
# TEST - AI MENTOR DECISION ÜRETİMİ
# ==================================================
# Amaç:
# Gerçek OpenAI API'sini çağırmadan sahte (mock) bir cevap kullanarak
# generate_mentor_decision() fonksiyonunun MentorDecision döndürdüğünü doğrular.
def test_generate_mentor_decision_returns_parsed_model():

    learner_profile = {
        "answer_length": "concise",
        "learning_style": "guided",
        "code_support": "medium",
    }

    skill_state = {
        "skill_name": "python_dict",
        "status": "learning",
        "attempts": 2,
        "successful_attempts": 1,
    }

    learning_evidence = [
        {
            "assistance_level": "GUIDE",
            "success": 1,
            "evidence_type": "application",
        }
    ]

    current_message = "Dictionary nasıl oluşturuyorduk?"

    expected_decision = MentorDecision(
        skill_name="python_dict",
        assistance_level="GUIDE",
        reason="Kullanıcı yönlendirmeye ihtiyaç duyuyor.",
    )

    # Gerçek OpenAI response nesnesi yerine sahte response oluşturuyoruz.
    mock_response = MagicMock()
    mock_response.output_parsed = expected_decision

    with patch(
        "backend.app.mentor_service.client.responses.parse",
        return_value=mock_response,
    ):
        decision = generate_mentor_decision(
            learner_profile,
            skill_state,
            learning_evidence,
            current_message,
        )

    assert decision == expected_decision
    assert decision.assistance_level == "GUIDE"


# ==================================================
# TEST - LEARNER İÇİN MENTOR KARARI OLUŞTURMA
# ==================================================
# Amaç:
# Learner profile ve skill state'i DB'den alıp
# mentor karar mekanizmasına gönderdiğini doğrular.
def test_get_mentor_decision_for_learner(tmp_path):
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
        skill_name="python_data_structures",
        status="learning",
    )

    expected_decision = MentorDecision(
        skill_name="python_data_structures",
        assistance_level="GUIDE",
        reason="Kullanıcı yönlendirmeye ihtiyaç duyuyor.",
    )

    mock_response = MagicMock()
    mock_response.output_parsed = expected_decision

    with patch(
        "backend.app.mentor_service.client.responses.parse",
        return_value=mock_response,
    ):
        decision = get_mentor_decision_for_learner(
            learner_id="learner-001",
            skill_name="python_data_structures",
            current_message="Dictionary nasıl oluşturuyorduk?",
        )

    assert decision == expected_decision



# ==================================================
# TEST - LEARNER PROFILE YOKSA DURDUR
# ==================================================
# Amaç:
# DB'de learner yoksa mentor kararına geçmeden
# ValueError oluştuğunu doğrular.
def test_get_mentor_decision_raises_if_learner_missing(tmp_path):
    database.DATABASE_PATH = tmp_path / "test.db"
    database.init_db()

    with pytest.raises(ValueError):
        get_mentor_decision_for_learner(
            learner_id="missing-learner",
            skill_name="python_data_structures",
            current_message="Dictionary nasıl oluşturulur?",
        )

# ==================================================
# TEST - LEARNER İÇİN İLK KEZ GÖRÜLEN SKILL OLUŞTUR
# ==================================================
# Amaç:
# Skill katalogda var ama learner için henüz skill_state yoksa
# hata vermek yerine status="new" ile yeni kayıt oluşturulduğunu doğrular.
def test_get_mentor_decision_creates_new_skill_state(tmp_path):
    database.DATABASE_PATH = tmp_path / "test.db"
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )

    expected_decision = MentorDecision(
        skill_name="python_data_structures",
        assistance_level="GUIDE",
        reason="Yeni skill için yönlendirme veriliyor.",
    )

    with patch(
        "backend.app.mentor_service.generate_mentor_decision",
        return_value=expected_decision,
    ):
        decision = get_mentor_decision_for_learner(
            learner_id="learner-001",
            skill_name="python_data_structures",
            current_message="Dictionary nasıl oluşturulur?",
        )

    skill_state = database.get_skill_state(
        "learner-001",
        "python_data_structures",
    )

    assert skill_state is not None
    assert skill_state["status"] == "new"
    assert decision == expected_decision


def test_detect_relevant_skill_returns_catalog_skill():

    expected_detection = SkillDetection(
        skill_name="python_data_structures",
        reason="Kullanıcı dictionary key/value yapısını soruyor.",
    )

    mock_response = MagicMock()
    mock_response.output_parsed = expected_detection

    with patch(
        "backend.app.mentor_service.client.responses.parse",
        return_value=mock_response,
    ):
        detection = detect_relevant_skill(
            "Dictionary'de key ve value mantığı neydi?"
        )
        assert detection.skill_name == "python_data_structures"



def test_detect_relevant_skill_returns_none_for_non_skill_message():

    expected_detection = SkillDetection(
        skill_name=None,
        reason="Bu mesaj proje navigasyonu ile ilgili.",
    )

    mock_response = MagicMock()
    mock_response.output_parsed = expected_detection

    with patch(
        "backend.app.mentor_service.client.responses.parse",
        return_value=mock_response,
    ):
        detection = detect_relevant_skill(
            "Bugün projede nerede kalmıştık?"
        )

        assert detection.skill_name is None

def test_get_mentor_decision_raises_for_skill_outside_catalog(tmp_path):
    database.DATABASE_PATH = tmp_path / "test.db"
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )

    with pytest.raises(ValueError):
        get_mentor_decision_for_learner(
            learner_id="learner-001",
            skill_name="kafka_magic",
            current_message="Kafka'yı nasıl kullanırım?",
        )


def test_get_mentor_decision_from_message_returns_decision():

    expected_detection = SkillDetection(
        skill_name="python_data_structures",
        reason="Mesaj Python veri yapıları ile ilgili.",
    )

    expected_decision = MentorDecision(
        skill_name="python_data_structures",
        assistance_level="GUIDE",
        reason="Kullanıcı yönlendirmeye ihtiyaç duyuyor.",
    )

    with patch(
        "backend.app.mentor_service.detect_relevant_skill",
        return_value=expected_detection,
    ), patch(
        "backend.app.mentor_service.get_mentor_decision_for_learner",
        return_value=expected_decision,
    ):
        decision = get_mentor_decision_from_message(
            learner_id="learner-001",
            current_message="Dictionary nasıl oluşturuyorduk?",
        )

    assert decision == expected_decision


def test_get_mentor_decision_from_message_returns_none_when_no_skill():

    expected_detection = SkillDetection(
        skill_name=None,
        reason="Mesaj belirli bir öğrenme skill'i ile ilgili değil.",
    )

    with patch(
        "backend.app.mentor_service.detect_relevant_skill",
        return_value=expected_detection,
    ):
        decision = get_mentor_decision_from_message(
            learner_id="learner-001",
            current_message="Bugün projede nerede kalmıştık?",
        )

    assert decision is None

def test_generate_mentor_response_returns_text():

    learner_profile = {
        "answer_length": "concise",
        "learning_style": "guided",
        "code_support": "medium",
    }

    mentor_decision = MentorDecision(
        skill_name="python_data_structures",
        assistance_level="GUIDE",
        reason="Kullanıcı yönlendirmeye ihtiyaç duyuyor.",
    )

    mock_response = MagicMock()
    mock_response.output_text = (
        "Dictionary key-value yapısını düşün. "
        "Önce boş bir dictionary oluşturmayı dene."
    )

    with patch(
        "backend.app.mentor_service.client.responses.create",
        return_value=mock_response,
    ):
        mentor_response = generate_mentor_response(
            learner_profile=learner_profile,
            mentor_decision=mentor_decision,
            current_message="Dictionary nasıl oluşturuyorduk?",
        )

    assert mentor_response == mock_response.output_text



def test_classify_learning_evidence_returns_non_evidence():

    expected = LearningEvidenceDecision(
        is_evidence=False,
        evidence_type=None,
        success=None,
        note="Kullanıcı yalnızca soru soruyor.",
    )

    mock_response = MagicMock()
    mock_response.output_parsed = expected

    with patch(
        "backend.app.mentor_service.client.responses.parse",
        return_value=mock_response,
    ):
        evidence = classify_learning_evidence(
            skill_name="python_data_structures",
            current_message="Dictionary nasıl oluşturuluyordu?",
        )

    assert evidence.is_evidence is False


def test_classify_learning_evidence_returns_application():

    expected = LearningEvidenceDecision(
        is_evidence=True,
        evidence_type="application",
        success=True,
        note="Junior geçerli bir dictionary oluşturdu.",
    )

    mock_response = MagicMock()
    mock_response.output_parsed = expected

    with patch(
        "backend.app.mentor_service.client.responses.parse",
        return_value=mock_response,
    ):
        evidence = classify_learning_evidence(
            skill_name="python_data_structures",
            current_message='data = {"name": "Yasin"}',
        )

    assert evidence.is_evidence is True
    assert evidence.evidence_type == "application"
    assert evidence.success is True


def test_process_learning_evidence_updates_skill_state(tmp_path):
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
        skill_name="python_data_structures",
        status="new",
    )

    mentor_decision = MentorDecision(
        skill_name="python_data_structures",
        assistance_level="GUIDE",
        reason="Yönlendirme gerekli.",
    )

    expected_evidence = LearningEvidenceDecision(
        is_evidence=True,
        evidence_type="application",
        success=True,
        note="Doğru uygulama.",
    )

    with patch(
        "backend.app.mentor_service.classify_learning_evidence",
        return_value=expected_evidence,
    ):
        process_learning_evidence(
            learner_id="learner-001",
            mentor_decision=mentor_decision,
            current_message='data = {"name": "Yasin"}',
        )

    state = database.get_skill_state(
        "learner-001",
        "python_data_structures",
    )

    assert state["attempts"] == 1
    assert state["successful_attempts"] == 1
    assert state["status"] == "learning"
