from backend.app.mentor_service import (
    build_mentor_decision_prompt,
    generate_mentor_decision,
     get_mentor_decision_for_learner,
)
from unittest.mock import patch, MagicMock
from backend.app.models import MentorDecision
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
        skill_name="python_dict",
        status="learning",
    )

    expected_decision = MentorDecision(
        skill_name="python_dict",
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
            skill_name="python_dict",
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
            skill_name="python_dict",
            current_message="Dictionary nasıl oluşturulur?",
        )

# ==================================================
# TEST - SKILL STATE YOKSA DURDUR
# ==================================================
# Amaç:
# Learner var ama ilgili skill state yoksa
# ValueError oluştuğunu doğrular.
def test_get_mentor_decision_raises_if_skill_missing(tmp_path):
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
            skill_name="python_dict",
            current_message="Dictionary nasıl oluşturulur?",
        )

