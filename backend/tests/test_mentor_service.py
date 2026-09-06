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
    get_skill_for_data_quality_issue,
    get_mentor_decision_for_data_quality_finding,
    get_mentor_response_for_data_quality_finding,
    evaluate_data_quality_attempt,
    review_data_quality_attempt,
    generate_data_quality_attempt_response,
    review_data_quality_transformation,
)
from unittest.mock import patch, MagicMock
from backend.app.models import (
    MentorDecision,
    SkillDetection,
    LearningEvidenceDecision,
    DataQualityFinding,
)
import backend.app.database as database
import pytest
import pandas as pd

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

def test_get_skill_for_data_quality_issue():
    skill = get_skill_for_data_quality_issue("missing_values")

    assert skill == "null_analysis"

def test_get_mentor_decision_for_data_quality_finding():
    finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="age sütununda eksik değer var.",
        suggested_action="Eksik değerin nedenini inceleyin.",
    )

    with patch(
        "backend.app.mentor_service.get_mentor_decision_for_learner"
    ) as mock_get_decision:

        mock_get_decision.return_value = "test-decision"

        result = get_mentor_decision_for_data_quality_finding(
            learner_id="learner-1",
            finding=finding,
        )

        assert result == "test-decision"

        mock_get_decision.assert_called_once_with(
            learner_id="learner-1",
            skill_name="null_analysis",
            current_message="age sütununda eksik değer var.",
        )

def test_get_mentor_response_for_data_quality_finding():
    finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="age sütununda eksik değer var.",
        suggested_action="Eksik değerin nedenini inceleyin.",
    )

    fake_decision = MagicMock()

    learner_profile = {
        "answer_length": "concise",
        "learning_style": "guided",
        "code_support": "medium",
    }

    with patch(
        "backend.app.mentor_service.get_mentor_decision_for_data_quality_finding",
        return_value=fake_decision,
    ), patch(
        "backend.app.mentor_service.database.get_learner_profile_by_id",
        return_value=learner_profile,
    ), patch(
        "backend.app.mentor_service.generate_mentor_response",
        return_value="Test mentor cevabı.",
    ) as mock_generate_response:

        result = get_mentor_response_for_data_quality_finding(
            learner_id="learner-1",
            finding=finding,
        )

        assert result == "Test mentor cevabı."

        mock_generate_response.assert_called_once_with(
            learner_profile=learner_profile,
            mentor_decision=fake_decision,
        current_message=(
            "Problem: age sütununda eksik değer var.\n"
            "Suggested action: Eksik değerin nedenini inceleyin.\n"
            "Sadece bu finding içinde verilen bilgilere dayan. "
            "Veride olmayan kolon, değer veya metadata uydurma."
            ),
        )

def test_evaluate_data_quality_attempt_returns_evidence():
    finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="age sütununda eksik değer var.",
        suggested_action="Eksik değerin nedenini inceleyin.",
    )

    fake_evidence = LearningEvidenceDecision(
        is_evidence=True,
        evidence_type="application",
        success=True,
        note="Junior null kontrolü için uygun bir adım önerdi.",
    )

    with patch(
        "backend.app.mentor_service.client.responses.parse"
    ) as mock_parse:

        mock_parse.return_value.output_parsed = fake_evidence

        result = evaluate_data_quality_attempt(
            skill_name="null_analysis",
            finding=finding,
            attempt="df['age'].isna().sum() ile eksik sayısını kontrol ederim.",
        )

        assert result == fake_evidence
        assert result.is_evidence is True
        assert result.success is True

        mock_parse.assert_called_once()

def test_review_data_quality_attempt_records_evidence_and_returns_response():
    finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="age sütununda eksik değer var.",
        suggested_action="Eksik değerin nedenini inceleyin.",
    )

    fake_decision = MentorDecision(
        skill_name="null_analysis",
        assistance_level="GUIDE",
        reason="Learner yönlendirmeye ihtiyaç duyuyor.",
    )

    fake_evidence = LearningEvidenceDecision(
        is_evidence=True,
        evidence_type="application",
        success=True,
        note="Junior uygun bir null kontrolü önerdi.",
    )

    learner_profile = {
        "answer_length": "concise",
        "learning_style": "guided",
        "code_support": "medium",
    }

    with patch(
        "backend.app.mentor_service.get_mentor_decision_for_data_quality_finding",
        return_value=fake_decision,
    ), patch(
        "backend.app.mentor_service.evaluate_data_quality_attempt",
        return_value=fake_evidence,
    ), patch(
        "backend.app.mentor_service.database.record_learning_evidence"
    ) as mock_record, patch(
        "backend.app.mentor_service.refresh_skill_status",
        return_value="learning",
    ), patch(
        "backend.app.mentor_service.database.get_learner_profile_by_id",
        return_value=learner_profile,
    ), patch(
    "backend.app.mentor_service.generate_data_quality_attempt_response",
    return_value="Doğru. Şimdi null oranını kontrol et.",
        ):

        result = review_data_quality_attempt(
            learner_id="demo-learner",
            finding=finding,
            attempt="df['age'].isna().sum() ile eksik sayısını kontrol ederim.",
        )

        assert result.mentor_response == (
            "Doğru. Şimdi null oranını kontrol et."
        )

        assert result.skill_name == "null_analysis"
        assert result.skill_status == "learning"
        assert result.evidence.success is True

        mock_record.assert_called_once_with(
            learner_id="demo-learner",
            skill_name="null_analysis",
            assistance_level="GUIDE",
            success=True,
            evidence_type="application",
            note="Junior uygun bir null kontrolü önerdi.",
            session_id=None,
        )

def test_generate_data_quality_attempt_response_returns_text():

    learner_profile = {
        "answer_length": "concise",
        "learning_style": "guided",
        "code_support": "medium",
    }

    mentor_decision = MentorDecision(
        skill_name="null_analysis",
        assistance_level="GUIDE",
        reason="Junior yönlendirmeye ihtiyaç duyuyor.",
    )

    finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="age sütununda eksik değer var.",
        suggested_action="Eksik değerin nedenini inceleyin.",
    )

    evidence = LearningEvidenceDecision(
        is_evidence=True,
        evidence_type="application",
        success=True,
        note="Junior doğru bir adım uyguladı.",
    )

    mock_response = MagicMock()
    mock_response.output_parsed.next_step = (
        "Eksik age değerlerinin bulunduğu örnek satırları inceleyin."
    )

    with patch(
        "backend.app.mentor_service.client.responses.parse",
        return_value=mock_response,
    ) as mock_parse:

        result = generate_data_quality_attempt_response(
            learner_profile=learner_profile,
            mentor_decision=mentor_decision,
            finding=finding,
            attempt="Eksik age değerlerinin bulunduğu satırları inceleyeceğim.",
            evidence=evidence,
        )

    assert result == (
        "Evet, bu doğru bir adım. "
        "Eksik age değerlerinin bulunduğu örnek satırları inceleyin."
    )

    mock_parse.assert_called_once()


def test_review_data_quality_transformation_records_real_validation_evidence():

    # Transformation öncesinde age kolonunda 2 null var.
    before_df = pd.DataFrame(
        {
            "name": ["Ali", "Ayse", "Mehmet"],
            "age": [30, None, None],
        }
    )

    # Transformation sonrasında 1 null kalmış.
    after_df = pd.DataFrame(
        {
            "name": ["Ali", "Ayse", "Mehmet"],
            "age": [30, 25, None],
        }
    )

    finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="age sütununda eksik değerler var.",
        suggested_action="Eksik değerleri inceleyin.",
    )

    fake_decision = MentorDecision(
        skill_name="null_analysis",
        assistance_level="GUIDE",
        reason="Learner yönlendirmeye ihtiyaç duyuyor.",
    )

    with patch(
        "backend.app.mentor_service.get_mentor_decision_for_data_quality_finding",
        return_value=fake_decision,
    ), patch(
        "backend.app.mentor_service.database.record_learning_evidence"
    ) as mock_record, patch(
        "backend.app.mentor_service.refresh_skill_status",
        return_value="learning",
    ):

        result = review_data_quality_transformation(
            learner_id="demo-learner",
            finding=finding,
            before_df=before_df,
            after_df=after_df,
        )

    # Finding doğru skill'e bağlandı.
    assert result.skill_name == "null_analysis"

    # Gerçek before/after data validation sonucu.
    assert result.validation.column == "age"
    assert result.validation.before_null_count == 2
    assert result.validation.after_null_count == 1
    assert result.validation.success is True

    # Validation sonucu learning evidence'a dönüştürüldü.
    assert result.evidence.is_evidence is True
    assert result.evidence.evidence_type == "application"
    assert result.evidence.success is True

    # Evidence sonrası skill status döndü.
    assert result.skill_status == "learning"

    # Gerçek validation sonucu DB'ye learning evidence olarak gönderildi.
    mock_record.assert_called_once_with(
        learner_id="demo-learner",
        skill_name="null_analysis",
        assistance_level="GUIDE",
        success=True,
        evidence_type="application",
        note=(
            "age kolonundaki null sayısı "
            "2 değerinden 1 değerine değişti."
        ),
        session_id=None,
    )