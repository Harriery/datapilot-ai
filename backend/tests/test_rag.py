from unittest.mock import MagicMock, patch

from backend.app.rag_service import (
    build_context,
    generate_answer,
)

def test_build_context_combines_chunk_contents():
    # Retrieval sonucunda gelmiş gibi iki sahte chunk oluşturur.
    relevant_chunks = [
        {
            "chunk_index": 0,
            "content": "Birinci ilgili metin.",
            "similarity": 0.90,
        },
        {
            "chunk_index": 2,
            "content": "İkinci ilgili metin.",
            "similarity": 0.75,
        },
    ]

    # Chunk metinlerini tek bir context içinde birleştirir.
    context = build_context(relevant_chunks)

    expected_context = (
        "Birinci ilgili metin.\n\n"
        "İkinci ilgili metin."
    )

    assert context == expected_context


def test_generate_answer_returns_output_text():
    # Gerçek OpenAI çağrısını test sırasında sahte çağrıyla değiştirir.
    with patch(
        "backend.app.rag_service.client.responses.create"
    ) as mock_create:
        fake_response = MagicMock()

        fake_response.output_text = "Belgeye dayalı test cevabı."

        mock_create.return_value = fake_response

        question = "Belgede ne anlatılıyor?"

        context = "Belgede veri temizleme işlemleri anlatılıyor."

        answer = generate_answer(question, context)

        assert answer ==  fake_response.output_text

        mock_create.assert_called_once()