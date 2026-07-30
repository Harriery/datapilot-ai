from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


#----- TXT dosya yukleme testi-----

def test_upload_txt_document():
    response = client.post(
        "/documents/upload",
        files={
            "file": (                           # Testte gerçek bir dosya seçemediğimiz için, dosyayı kod içinde taklit ediyoruz:
                "test.txt",
                b"Data engineering test metni.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 200          # → Dosya başarıyla yüklendi mi?
    assert "document_id" in response.json()     #  Belge veritabanına kaydedilip ID aldı mı?
    assert response.json()["chunk_count"] >= 1  # → Metin en az bir chunk’a bölündü mü?



#-----Gecersiz dosya turu testi-----

def test_upload_invalid_file_type():
    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "test.jpg",
                b"sahte resim verisi",
                "image/jpeg",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == ("Yalnızca PDF veya TXT dosyası yükleyebilirsiniz.")

def test_get_uploaded_document():
     # Önce bir TXT belgesi yükler.
    upload_response = client.post(
        "/documents/upload",    # bu endpointe post istegi gonderiyruz. 

        files={                 # Python dictionary ve tuple oluşturuyoruz
            "file": (           # bu bizim test amacli olusturdugumuz txt dosyasi adi, icerigi
                "test.txt",
                b"Data engineering test metni",
                "text/plain",
            )
        },

    )

    # POST cevabındaki JSON'u Python sözlüğüne çevirir.
    upload_body = upload_response.json()

    # Sözlük içindeki document_id değerini alır.
    document_id = upload_body["document_id"]

    # Oluşan belgeyi ID ile tekrar ister.
    # upload_response, HTTP Response nesnesidir.
    # .json()  Python dict hâline getirir.
    get_response = client.get(f"/documents/{document_id}")  

    # GET cevabındaki JSON'u sözlüğe çevirir.
    get_body = get_response.json()

    assert get_response.status_code == 200
    assert get_body["filename"] == "test.txt"
    assert len(get_body["chunks"]) >= 1



def test_get_nonexistent_document():
    response = client.get("/documents/999999")

    # JSON cevabını Python sözlüğüne çevir.
    body = response.json()

    # HTTP kodu 404 mü?
    assert response.status_code == 404      # HTTP cevap kodu

    # JSON içindeki detail mesajı doğru mu?
    assert body["detail"] == "Belge bulunamadı."