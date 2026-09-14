from fastapi.testclient import TestClient

from backend.app.main import app
from unittest.mock import patch
import pytest
import backend.app.database as database

client = TestClient(app)    # FastAPI uygulamamıza test amaçlı sahte bir kullanıcı oluşturuyoruz.

# Her chat testi için temiz bir test DB oluşturur.
# /chat artık learner_profiles ve skill_states tablolarını da kullandığı
# için init_db() ile bütün tabloları hazırlıyoruz.
@pytest.fixture(autouse=True)
def setup_test_database(tmp_path):
    database.DATABASE_PATH = tmp_path / "test.db"
    database.init_db()

# Boşluklardan oluşan mesaj gönder
# ↓
# strip() bunu boş metne çevirir
# ↓
# API 400 döndürmeli
def test_empty_message_returns_400():
    response = client.post(
        "/chat",
        json={
            "session_id": "test-session",
            "message": "   ",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Mesaj boş olamaz."


# Geçerli bir mesaj gönder
# ↓
# Session bulunamaz
# ↓
# OpenAI çağrılmadan 404 dönmeli
def test_chat_with_nonexistent_session_returns_404():
    response = client.post(
        "/chat",
        json={
            "session_id": "olmayan-session",
            "message": "Merhaba",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Session bulunamadı. Önce yeni bir session oluşturun."
    )



# Gerçek OpenAI çağrısı
# ↓
# Test sırasında çalışmaz
# ↓
# "Test AI cevabı" döner
def test_chat_returns_ai_response():
    create_response = client.post("/sessions")
    session_id = create_response.json()["session_id"]

    with patch(
        "backend.app.chat_routes.get_mentor_response_from_message",
        return_value=None,
    ), patch(
        "backend.app.chat_routes.client.responses.create"
    ) as mock_create:

        mock_create.return_value.output_text = "Test AI cevabı"

        response = client.post(
            "/chat",
            json={
                "session_id": session_id,
                "message": "Merhaba",
            },
        )

    assert response.status_code == 200
    assert response.json()["reply"] == "Test AI cevabı"





# Session oluşturuluyor
# ↓
# Gerçek OpenAI çağrısı yerine bilerek hata oluşturuluyor
# ↓
# API 500 hatası döndürüyor
# ↓
# Cevapsız kullanıcı mesajının geçmişten silindiği kontrol ediliyor
def test_chat_returns_500_when_openai_fails():
    create_response = client.post("/sessions")
    session_id = create_response.json()["session_id"]

    with patch(
        "backend.app.chat_routes.get_mentor_response_from_message",
        return_value=None,
    ), patch(
        "backend.app.chat_routes.client.responses.create"
    ) as mock_create:
    
        mock_create.side_effect = Exception("Test hatası")
    
        response = client.post(
            "/chat",
            json={
                "session_id": session_id,
                "message": "Merhaba",
            },
        )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Beklenmeyen bir sunucu hatası oluştu."
    )

    ## Hata sonrası kullanıcı mesajının history.pop() ile silindiğini kontrol eder.
    session_response = client.get(f"/sessions/{session_id}")
    assert session_response.json()["history"] == []

def test_chat_passes_workspace_context_to_mentor():
    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Data Quality",
            "workspace_type": "data_engineering",
        },
    )

    assert create_response.status_code == 200

    workspace = create_response.json()

    workspace_id = workspace["workspace_id"]
    mentor_session_id = workspace["mentor_session_id"]

    checkpoint_response = client.put(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/checkpoint"
        ),
        json={
            "checkpoint": {
                "completed_items": [
                    "Duplicate kayıtlar temizlendi."
                ],
                "current_focus": (
                    "age kolonundaki null değerler"
                ),
                "blocked_reason": None,
                "last_error": (
                    "Null sayısı azalmadı."
                ),
                "next_actions": [
                    "age dağılımını incele"
                ],
            }
        },
    )

    assert checkpoint_response.status_code == 200

    with patch(
        "backend.app.chat_routes."
        "get_mentor_response_from_message",
        return_value="Mentor cevabı",
    ) as mock_mentor:

        response = client.post(
            "/chat",
            json={
                "session_id": mentor_session_id,
                "learner_id": "learner-001",
                "workspace_id": workspace_id,
                "message": (
                    "Tam olarak nereyi diyorsun?"
                ),
            },
        )

    assert response.status_code == 200

    call_kwargs = (
        mock_mentor.call_args.kwargs
    )

    workspace_context = (
        call_kwargs["workspace_context"]
    )

    assert (
        workspace_context["workspace_id"]
        == workspace_id
    )

    assert (
        workspace_context["title"]
        == "Customer Data Quality"
    )

    assert (
        workspace_context[
            "checkpoint"
        ]["current_focus"]
        == "age kolonundaki null değerler"
    )

    assert (
        workspace_context[
            "checkpoint"
        ]["last_error"]
        == "Null sayısı azalmadı."
    )


def test_chat_rejects_session_from_another_workspace():
    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Data Quality",
            "workspace_type": "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    other_session_response = client.post(
        "/sessions"
    )

    other_session_id = (
        other_session_response.json()["session_id"]
    )

    response = client.post(
        "/chat",
        json={
            "session_id": other_session_id,
            "learner_id": "learner-001",
            "workspace_id": workspace_id,
            "message": "Merhaba",
        },
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Session bu workspace'e ait değil."
    )