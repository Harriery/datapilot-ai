from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)    #FastAPI uygulamamıza test amaçlı sahte bir kullanıcı oluşturuyoruz.
                           # Bu client ile gerçek tarayıcı açmadan şunu yapabiliyoruz:
                            #client.post("/chat")
                            #client.get("/sessions/...")

#Session oluşturuldu mu?
#Cevapta session_id geldi mi?
def test_create_session():
    response = client.post("/sessions")

    assert response.status_code == 200
    assert "session_id" in response.json()      # assert ->  Bu şart doğru olmak zorunda.


# Session oluşturur
# → ID’yi alır
# → O session’ı getirir
# → ID doğru mu ve geçmiş boş mu kontrol eder
def test_get_created_session():
    create_response = client.post("/sessions")
    session_id = create_response.json()["session_id"]

    response = client.get(f"/sessions/{session_id}")

    assert response.status_code == 200
    assert response.json()["session_id"] == session_id
    assert response.json()["history"] == []



# Olmayan bir session ID gönder
# ↓
# API 404 döndürmeli
# ↓
# Hata mesajı doğru olmalı
def test_get_nonexistent_session():
    response = client.get("/sessions/olmayan-session")

    assert response.status_code == 404
    assert response.json()["detail"] == "Session bulunamadı."



# Session oluştur
# ↓
# Session’ı sil
# ↓
# Silme işlemi 200 döndü mü?
# ↓
# Aynı session tekrar istendiğinde 404 dönüyor mu?
def test_delete_session():
    create_response = client.post("/sessions")
    session_id = create_response.json()["session_id"]

    delete_response = client.delete(f"/sessions/{session_id}")

    assert delete_response.status_code == 200

    get_response = client.get(f"/sessions/{session_id}")

    assert get_response.status_code == 404