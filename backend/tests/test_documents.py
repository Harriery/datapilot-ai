from fastapi.testclient import TestClient

from backend.app.main import app
from unittest.mock import patch


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



def test_search_uploaded_document():
    # Belge yüklenirken gerçek OpenAI çağrısı yerine
    # sahte bir chunk embedding'i döndürür.
    with patch(
        "backend.app.document_routes.create_embeddings"
    ) as mock_create_embeddings:

        mock_create_embeddings.return_value = [
            [1.0, 0.0]
        ]

        upload_response = client.post(
            "/documents/upload",
            files={
                "file": (
                    "search_test.txt",
                    b"Python listeleri sirali veri saklar.",
                    "text/plain",
                )
            },
        )

        # Belge yükleme isteğinin başarılı olduğunu kontrol eder.
        assert upload_response.status_code == 200

        # JSON cevabını Python sözlüğüne dönüştürür.
        upload_body = upload_response.json()

        # Oluşturulan belgenin id değerini alır.
        document_id = upload_body["document_id"]

    # Arama sırasında sorunun embedding'ini sahte değerle değiştirir.
    with patch(
        "backend.app.document_routes.create_embedding"
    ) as mock_create_embedding:
        # Soru embedding'i, chunk embedding'iyle aynı olsun.
        mock_create_embedding.return_value = [1.0, 0.0]
        search_response = client.post(
            f"/documents/{document_id}/search",
            json={
                "question": "Python listeleri nedir?",
                "top_k": 1,
            },
        )
        # Arama isteğinin başarılı olduğunu kontrol eder.
        assert search_response.status_code == 200
        # JSON cevabını Python sözlüğüne dönüştürür.
        search_body = search_response.json()
        # Dönen ilgili chunk listesini alır.
        results = search_body["results"]

        # top_k=1 olduğu için yalnızca bir sonuç dönmelidir.
        assert len(results) == 1
        # İlk sonuç yüklediğimiz chunk olmalıdır.
        assert results[0]["chunk_index"] == 0
        # Soru ve chunk embedding'leri aynı olduğu için benzerlik 1 olmalıdır.
        assert round(results[0]["similarity"], 5) == 1.0