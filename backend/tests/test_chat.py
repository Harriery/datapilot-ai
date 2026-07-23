from fastapi.testclient import TestClient

from backend.app.main import app
from unittest.mock import patch

client = TestClient(app)    # FastAPI uygulamamıza test amaçlı sahte bir kullanıcı oluşturuyoruz.



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

    with patch(     # patch geçici olarak gerçek OpenAI çağrısının yerine sahte bir cevap koyar:
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
        "backend.app.chat_routes.client.responses.create"
    ) as mock_create:
        mock_create.side_effect = Exception("Test hatası")  # side_effect, sahte OpenAI çağrısına bilerek hata verdirtir.

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