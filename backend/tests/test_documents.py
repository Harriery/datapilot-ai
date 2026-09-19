from fastapi.testclient import TestClient

from backend.app.main import app
from unittest.mock import patch
import pytest
import backend.app.database as database

client = TestClient(app)

@pytest.fixture(autouse=True)
def ensure_demo_learner():

    learner = (
        database.get_learner_profile_by_id(
            "demo-learner"
        )
    )

    if learner is None:
        database.insert_learner_profile(
            learner_id="demo-learner",
            answer_length="concise",
            learning_style="guided",
            code_support="medium",
            preferred_language="auto",
        )

PERSONAL_PUBLIC_UPLOAD_DATA = {
    "learner_id": "demo-learner",
    "usage_context": "personal",
    "data_sensitivity": "public",
}

#----- TXT dosya yukleme testi-----

def test_upload_txt_document():

    with patch(
        "backend.app.document_routes.create_embeddings"
    ) as mock_create_embeddings:

        mock_create_embeddings.return_value = [
            [1.0, 0.0]
        ]

        response = client.post(
            "/documents/upload",
            data=PERSONAL_PUBLIC_UPLOAD_DATA,
            files={
                "file": (
                    "test.txt",
                    b"Data engineering test metni.",
                    "text/plain",
                )
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert "document_id" in body
    assert body["chunk_count"] >= 1

    assert body["usage_context"] == "personal"
    assert body["data_sensitivity"] == "public"

    assert body["external_ai_allowed"] is True
    assert body["content_ingested"] is True

    mock_create_embeddings.assert_called_once()

#-----Gecersiz dosya turu testi-----

def test_upload_invalid_file_type():
    response = client.post(
        "/documents/upload",
        data=PERSONAL_PUBLIC_UPLOAD_DATA,
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

    with patch(
        "backend.app.document_routes.create_embeddings"
    ) as mock_create_embeddings:

        mock_create_embeddings.return_value = [
            [1.0, 0.0]
        ]

        upload_response = client.post(
            "/documents/upload",
            data=PERSONAL_PUBLIC_UPLOAD_DATA,
            files={
                "file": (
                    "test.txt",
                    b"Data engineering test metni",
                    "text/plain",
                )
            },
        )

    assert upload_response.status_code == 200

    document_id = (
        upload_response.json()[
            "document_id"
        ]
    )

    get_response = client.get(
        f"/documents/{document_id}",
        params={
            "learner_id": "demo-learner",
            "usage_context": "personal",
        },
    )

    get_body = get_response.json()

    assert get_response.status_code == 200

    assert get_body["filename"] == "test.txt"

    assert len(
        get_body["chunks"]
    ) >= 1


def test_get_nonexistent_document():
    response = client.get(
        "/documents/999999",
        params={
            "learner_id": "demo-learner",
            "usage_context": "personal",
        },
    )

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
            data=PERSONAL_PUBLIC_UPLOAD_DATA,
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
                "learner_id": "demo-learner",
                "usage_context": "personal",
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


def test_ask_uploaded_document():
    with patch(
        "backend.app.document_routes.create_embeddings"
    ) as mock_create_embeddings:

        mock_create_embeddings.return_value = [
            [1.0, 0.0]
        ]

        upload_response = client.post(
            "/documents/upload",
            data=PERSONAL_PUBLIC_UPLOAD_DATA,
            files={
                "file": (
                    "ask_test.txt",
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

        session_response = client.post("/sessions")
        session_id = session_response.json()["session_id"]

         # Arama sırasında sorunun embedding'ini sahte değerle değiştirir.
        with patch(
            "backend.app.document_routes.create_embedding"
        ) as mock_create_embedding:
            # Soru embedding'i, chunk embedding'iyle aynı olsun.
            mock_create_embedding.return_value = [1.0, 0.0]

            with patch(
                "backend.app.document_routes.generate_answer"
            ) as mock_generate_answer:

                mock_generate_answer.return_value = (
                    "Python listeleri sıralı verileri saklar."
                )

                ask_response = client.post(
                    f"/documents/{document_id}/ask",
                    json={
                        "learner_id": "demo-learner",
                        "usage_context": "personal",
                        "question": "Python listeleri nedir?",
                        "top_k": 1,
                        "session_id": session_id,
                    },
                )

            called_history = mock_generate_answer.call_args.kwargs["history"]
            assert called_history == []
            # Arama isteğinin başarılı olduğunu kontrol eder.
            assert ask_response.status_code == 200

            # JSON cevabını Python sözlüğüne dönüştürür.
            ask_body = ask_response.json()

            assert ask_body["answer"] == (
                "Python listeleri sıralı verileri saklar."
            )       




def test_ask_document_without_chunks():
    with patch(
    "backend.app.document_routes.get_document_by_id"
    ) as mock_get_document:

        mock_get_document.return_value = {
            "id": 99,
            "learner_id": "demo-learner",
            "filename": "empty.txt",
            "usage_context": "personal",
            "organization_id": None,
            "ai_processing_status": "allowed",
        }

        session_response = client.post("/sessions")
        session_id = session_response.json()["session_id"]

        with patch(
        "backend.app.document_routes.get_chunks_by_document"
        ) as mock_get_chunks:

            mock_get_chunks.return_value = []
            response = client.post(
            "/documents/99/ask",
            json={
                "learner_id": "demo-learner",
                "usage_context": "personal",
                "question": "Bu belgede ne anlatılıyor?",
                "top_k": 1,
                "session_id": session_id,
            },

        )
            assert response.status_code == 400

            body = response.json()
            assert body["detail"] == "Belgede aranabilir içerik bulunamadı."

def test_ask_document_ai_error():
    with patch(
        "backend.app.document_routes.get_document_by_id"
    ) as mock_get_document:

        mock_get_document.return_value = {
            "id": 99,
            "learner_id": "demo-learner",
            "filename": "ai_error_test.txt",
            "usage_context": "personal",
            "organization_id": None,
            "ai_processing_status": "allowed",
        }

        session_response = client.post("/sessions")
        session_id = session_response.json()["session_id"]

        with patch(
            "backend.app.document_routes.get_chunks_by_document"
        ) as mock_get_chunks:

            mock_get_chunks.return_value = [
                {
                    "chunk_index": 0,
                    "content": "Python listeleri sıralı veri saklar.",
                    "embedding": [1.0, 0.0],
                }
            ]

            with patch(
                "backend.app.document_routes.create_embedding"
            ) as mock_create_embedding:

                mock_create_embedding.return_value = [1.0, 0.0]

                with patch(
                    "backend.app.document_routes.generate_answer"
                ) as mock_generate_answer:

                    mock_generate_answer.side_effect = Exception(
                        "OpenAI bağlantı hatası"
                    )

                    response = client.post(
                        "/documents/99/ask",
                        json={
                            "learner_id": "demo-learner",
                            "usage_context": "personal",
                            "question": "Python listeleri nedir?",
                            "top_k": 1,
                            "session_id": session_id,
                        },
                    )

                    assert response.status_code == 502
                    body = response.json()

                    assert body["detail"] == (
                        "AI servisine şu anda ulaşılamıyor."
                    )

def test_confidential_document_never_calls_embeddings():

    with patch(
        "backend.app.document_routes."
        "create_embeddings"
    ) as mock_embeddings:

        response = client.post(
            "/documents/upload",

            data={
                "learner_id":
                    "demo-learner",

                "usage_context":
                    "work",

                "data_sensitivity":
                    "confidential",

                "organization_id":
                    "company-001",
            },

            files={
                "file": (
                    "confidential.txt",
                    b"Sensitive company data",
                    "text/plain",
                )
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert (
        body["external_ai_allowed"]
        is False
    )

    assert (
        body["ai_processing_status"]
        == "blocked"
    )

    assert (
        body["content_ingested"]
        is False
    )

    assert body["chunk_count"] == 0

    mock_embeddings.assert_not_called()

def test_personal_context_cannot_access_work_document():

    with patch(
        "backend.app.document_routes."
        "create_embeddings"
    ) as mock_embeddings:

        mock_embeddings.return_value = [
            [1.0, 0.0]
        ]

        upload_response = client.post(
            "/documents/upload",

            data={
                "learner_id":
                    "demo-learner",

                "usage_context":
                    "work",

                "data_sensitivity":
                    "public",

                "organization_id":
                    "company-001",
            },

            files={
                "file": (
                    "work.txt",
                    b"Public work document",
                    "text/plain",
                )
            },
        )

    document_id = (
        upload_response.json()[
            "document_id"
        ]
    )

    response = client.get(
        f"/documents/{document_id}",
        params={
            "learner_id":
                "demo-learner",

            "usage_context":
                "personal",
        },
    )

    assert response.status_code == 403


def test_blocked_document_search_never_calls_ai():

    upload_response = client.post(
        "/documents/upload",

        data={
            "learner_id":
                "demo-learner",

            "usage_context":
                "work",

            "data_sensitivity":
                "confidential",

            "organization_id":
                "company-001",
        },

        files={
            "file": (
                "secret.txt",
                b"Sensitive company data",
                "text/plain",
            )
        },
    )

    document_id = (
        upload_response.json()[
            "document_id"
        ]
    )

    with patch(
        "backend.app.document_routes."
        "create_embedding"
    ) as mock_embedding:

        response = client.post(
            f"/documents/{document_id}/search",

            json={
                "learner_id":
                    "demo-learner",

                "usage_context":
                    "work",

                "organization_id":
                    "company-001",

                "question":
                    "What is inside?",

                "top_k": 1,
            },
        )

    assert response.status_code == 403

    mock_embedding.assert_not_called()

def test_personal_context_cannot_access_work_document():

    with patch(
        "backend.app.document_routes.create_embeddings"
    ) as mock_embeddings:

        mock_embeddings.return_value = [
            [1.0, 0.0]
        ]

        upload_response = client.post(
            "/documents/upload",
            data={
                "learner_id": "demo-learner",
                "usage_context": "work",
                "data_sensitivity": "public",
                "organization_id": "company-001",
            },
            files={
                "file": (
                    "work.txt",
                    b"Public work document",
                    "text/plain",
                )
            },
        )

    assert upload_response.status_code == 200

    document_id = (
        upload_response.json()["document_id"]
    )

    response = client.get(
        f"/documents/{document_id}",
        params={
            "learner_id": "demo-learner",
            "usage_context": "personal",
        },
    )

    assert response.status_code == 403

def test_blocked_document_search_never_calls_ai():

    upload_response = client.post(
        "/documents/upload",
        data={
            "learner_id": "demo-learner",
            "usage_context": "work",
            "data_sensitivity": "confidential",
            "organization_id": "company-001",
        },
        files={
            "file": (
                "secret.txt",
                b"Sensitive company data",
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 200

    document_id = (
        upload_response.json()["document_id"]
    )

    with patch(
        "backend.app.document_routes.create_embedding"
    ) as mock_embedding:

        response = client.post(
            f"/documents/{document_id}/search",
            json={
                "learner_id": "demo-learner",
                "usage_context": "work",
                "organization_id": "company-001",
                "question": "What is inside?",
                "top_k": 1,
            },
        )

    assert response.status_code == 403

    mock_embedding.assert_not_called()

def test_other_learner_cannot_access_document():

    with patch(
        "backend.app.document_routes.create_embeddings"
    ) as mock_embeddings:

        mock_embeddings.return_value = [
            [1.0, 0.0]
        ]

        upload_response = client.post(
            "/documents/upload",
            data={
                "learner_id": "demo-learner",
                "usage_context": "personal",
                "data_sensitivity": "public",
            },
            files={
                "file": (
                    "personal.txt",
                    b"Personal document",
                    "text/plain",
                )
            },
        )

    assert upload_response.status_code == 200

    document_id = (
        upload_response.json()["document_id"]
    )

    response = client.get(
        f"/documents/{document_id}",
        params={
            "learner_id": "another-learner",
            "usage_context": "personal",
        },
    )

    assert response.status_code == 403

def test_other_organization_cannot_access_work_document():

    with patch(
        "backend.app.document_routes.create_embeddings"
    ) as mock_embeddings:

        mock_embeddings.return_value = [
            [1.0, 0.0]
        ]

        upload_response = client.post(
            "/documents/upload",
            data={
                "learner_id": "demo-learner",
                "usage_context": "work",
                "data_sensitivity": "public",
                "organization_id": "company-001",
            },
            files={
                "file": (
                    "company.txt",
                    b"Company document",
                    "text/plain",
                )
            },
        )

    assert upload_response.status_code == 200

    document_id = (
        upload_response.json()["document_id"]
    )

    response = client.get(
        f"/documents/{document_id}",
        params={
            "learner_id": "demo-learner",
            "usage_context": "work",
            "organization_id": "company-002",
        },
    )

    assert response.status_code == 403