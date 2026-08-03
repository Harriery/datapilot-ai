from backend.app.retrieval_service import (
    cosine_similarity,
    find_relevant_chunks,
)


def test_same_direction_embeddings():
    question_embedding = [1.0, 2.0]
    chunk_embedding = [2.0, 4.0]

    similarity = cosine_similarity(
        question_embedding,
        chunk_embedding,
    )

    assert round(similarity, 5) == 1.0


def test_find_relevant_chunks_returns_most_similar_first():
    # Kullanıcının sorusunu temsil eden küçük embedding.
    question_embedding = [1.0, 0.0]

    # Veritabanından gelmiş gibi üç sahte chunk oluşturur.
    chunks = [
        {
            "chunk_index": 0,
            "content": "Python listeleri sıralı veri saklar.",
            "embedding": [1.0, 0.0],
        },
        {
            "chunk_index": 1,
            "content": "SQL tabloları satır ve kolonlardan oluşur.",
            "embedding": [0.0, 1.0],
        },
        {
            "chunk_index": 2,
            "content": "Python'da veriler listelerde tutulabilir.",
            "embedding": [1.0, 1.0],
        },
    ]

    # En benzer iki chunk'ı bulur.
    results = find_relevant_chunks(
        question_embedding,
        chunks,
        top_k=2,
    )

    # top_k=2 olduğu için iki sonuç dönmelidir.
    assert len(results) == 2

    # İlk chunk soru embedding'iyle tamamen aynı yöndedir.
    assert results[0]["chunk_index"] == 0

    # İkinci sırada kısmen benzer olan chunk bulunmalıdır.
    assert results[1]["chunk_index"] == 2

    # İlk chunk'ın benzerlik puanı 1 olmalıdır.
    assert round(results[0]["similarity"], 5) == 1.0