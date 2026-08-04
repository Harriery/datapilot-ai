"""
Bu dosya belge yükleme endpoint'lerini içerir.

RAG (Retrieval-Augmented Generation):
Yapay zekânın cevap vermeden önce yüklenen belgeler içinde arama yapmasını,
soruyla ilgili bilgileri bulmasını ve cevabı bu bilgilere dayandırmasını sağlar.

Bu dosya RAG sisteminin belge hazırlama aşamasını yönetir.

Belge hazırlama akışı:
- PDF veya TXT dosyasını alır.
- Dosyadan metni çıkarır.
- Metni chunk'lara böler.
- Belgeyi ve chunk'ları SQLite'a kaydeder.
- Kaydedilen belge ve chunk'ları geri getirir.

Şu anda tamamlanan aşama:
Belge hazırlama (document ingestion).

Daha sonra eklenecek aşamalar:
- Embedding oluşturma
- Soruyla ilgili chunk'ları bulma (retrieval)
- Bulunan bilgilere dayanarak AI cevabı üretme
"""

from fastapi import APIRouter, HTTPException, UploadFile
from pypdf import PdfReader
from backend.app.database import insert_chunks, insert_document, get_document_by_id, get_chunks_by_document
from backend.app.embedding_service import (
    create_embedding,
    create_embeddings,
)
from backend.app.retrieval_service import find_relevant_chunks
from backend.app.models import DocumentSearchRequest
from backend.app.rag_service import build_context, generate_answer

router = APIRouter()  # Belge endpoint'lerini gruplar.


# ==================================================
# AYARLAR
# ==================================================
# Kabul edilen dosya türlerini tutar.
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
}



# ==================================================
# BELGE HAZIRLAMA YARDIMCI FONKSİYONLARI
# ==================================================

# Uzun metni, kısmen birbiriyle örtüşen küçük parçalara böler.
def split_text_into_chunks(text: str) -> list[str]:
    words = text.split()    # Metni kelimelere ayırır: "Bugün hava güzel"   ["Bugün", "hava", "güzel"]

    chunks = []             # oluşturulan parçaları saklar.
    chunk_size = 200        # her parça en fazla 200 kelime.
    overlap = 30            # önceki parçanın son 30 kelimesi sonraki parçada tekrar eder.
    start = 0               # parçanın başlangıç konumu.

    while start < len(words):   # İşlenmemiş kelime kaldığı sürece devam eder.
        end = start + chunk_size
        chunk = " ".join(words[start:end])     # 200 kelimeyi seçip yeniden tek metin hâline getirir. 

        chunks.append(chunk)        # Oluşan parçayı listeye ekler.

        # Sonraki parça önceki parçanın son 30 kelimesini tekrar içerir.
        start += chunk_size - overlap       # Oluşan parçayı listeye ekler. 200 - 30 = 170

    return chunks



# PDF'in bütün sayfalarındaki metinleri birleştirir.
def extract_pdf_text(file: UploadFile) -> str:
    reader = PdfReader(file.file)

    page_texts = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            page_texts.append(text)

    return "\n".join(page_texts)




# ==================================================
# BELGE ENDPOINT'LERİ
# ==================================================

@router.post("/documents/upload")
def upload_document(file: UploadFile):      # stekteki file alanını al ve bir UploadFile nesnesine çevir. file.filename, file.content_type, file.file.read() erisebiliyoruz.
    # Dosya PDF veya TXT değilse isteği reddeder.
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Yalnızca PDF veya TXT dosyası yükleyebilirsiniz.",
        )

    # Dosya türüne göre metni çıkarır.
    if file.content_type == "text/plain":
        file_bytes = file.file.read()       # TXT dosyasını bytes olarak okur.
        text = file_bytes.decode("utf-8")   # Bytes verisini normal metne çevirir.
    else:
        text = extract_pdf_text(file)       # PDF içindeki metni çıkarır.

    # PDF veya TXT içinde okunabilir metin yoksa işlemi durdurur.
    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="Dosyadan metin çıkarılamadı.",
        )

    # PDF veya TXT metnini chunk'lara böler.
    chunks = split_text_into_chunks(text)

    # Bütün chunk'ların embedding vektörlerini oluşturur
    chunk_embeddings = create_embeddings(chunks)

    # Belge bilgilerini documents tablosuna kaydeder.
    document_id = insert_document(
        filename=file.filename,
        content_type=file.content_type,
    )

    # Chunk'ları aynı document_id ile chunks tablosuna kaydeder.
    insert_chunks(
        document_id=document_id,
        chunks=chunks,
        embeddings=chunk_embeddings
    )

    return {                    # Endpoint Python sözlüğü döndürüyor
        "document_id": document_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "character_count": len(text),
        "preview": text[:200],
        "chunk_count": len(chunks),
        "first_chunk_preview": chunks[0][:200],
        "embedding_count": len(chunk_embeddings),
        "first_embedding_length": len(chunk_embeddings[0]),
        "first_embedding_preview": chunk_embeddings[0][:5],
    }

@router.get("/documents/{document_id}")
def get_document(document_id: int):
    # 1. Belgeyi database.py üzerinden getir.
    document = get_document_by_id(document_id) 

    # 2. Belge yoksa 404 döndür.
    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Belge bulunamadı.",
        )

    # 3. Belgeye ait chunk'ları getir.
    chunks =  get_chunks_by_document(document_id)

    # 4. Belge bilgilerini ve chunk'ları döndür.
    return {
        # database.py icinde documents tablosundaki kolonları SQL ile id, filename ve content_type
        # olarak tanımladığımız için sonuçlara bu kolon adlarıyla erişiyoruz.
        "document_id": document["id"],
        "filename": document["filename"],
        "content_type": document["content_type"],
        "chunks": [
            {
                # database.py icinde,  SELECT sorgusunda chunk_index ve content kolonlarını aldığımız için
                # her chunk satırına bu kolon adlarıyla erişiyoruz.
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "embedding_length": len(chunk["embedding"]),
                "embedding_preview": chunk["embedding"][:5],
            }
            for chunk in chunks     # tek bir chunk değil, birden fazla chunk’tan oluşan liste döndürür
        ],
    }


# /search
# → Yalnızca ilgili chunk’ları bulur ve döndürür
@router.post("/documents/{document_id}/search")
def search_document(
    document_id: int,
    request: DocumentSearchRequest  # model.py icinde body icin gerekli question ve top-k kismi gelir. bunu body de doldurmak gerek
    ):

    # URL'den gelen document_id ile belgeyi veritabanında arar.
    document = get_document_by_id(document_id)

    # Belge bulunamazsa arama yapılamaz.
    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Belge bulunamadı.",
        )

    # Kullanıcının gönderdiği sorunun başındaki ve sonundaki boşlukları temizler.
    question = request.question.strip() #model icinde questionve top-k vardi, biz questionaldik.

    # Soru boşsa arama yapılamaz.
    if not question:
        raise HTTPException(
            status_code=400,
            detail="Soru boş olamaz.",
        )

    # Bu belgeye ait bütün chunk'ları veritabanından getirir.
    chunks = get_chunks_by_document(document_id)    # → O belgeye ait bütün chunk’ları getirir ve embeddingleride


     # Kullanıcının sorusunu sayı listesine dönüştürür.
    question_embedding = create_embedding(question)


    # Soruya en çok benzeyen chunk'ları bulur.
    relevant_chunks = find_relevant_chunks(
        question_embedding=question_embedding,
        chunks=chunks,
        top_k=request.top_k,
    )
    # Bulunan en ilgili chunk'ları JSON cevap olarak döndürür.
    return {
        "document_id": document_id,
        "question": question,
        "results": relevant_chunks,
    }


# /ask
# → İlgili chunk’ları bulur
# → context oluşturur
# → OpenAI’den cevap üretir
@router.post("/documents/{document_id}/ask")
def ask_document(
    document_id: int,
    request: DocumentSearchRequest,     # question ve top_k alanlarını taşır
):
    
    # URL'den gelen document_id ile belgeyi veritabanında arar.
    document = get_document_by_id(document_id)

    # Belge bulunamazsa arama yapılamaz.
    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Belge bulunamadı.",
        )

    # Kullanıcının gönderdiği sorunun başındaki ve sonundaki boşlukları temizler.
    question = request.question.strip() #model icinde questionve top-k vardi, biz questionaldik.

    # Soru boşsa arama yapılamaz.
    if not question:
        raise HTTPException(
            status_code=400,
            detail="Soru boş olamaz.",
        )

    # Bu belgeye ait bütün chunk'ları veritabanından getirir.
    chunks = get_chunks_by_document(document_id)

    # Kullanıcının sorusunu sayı listesine dönüştürür.
    question_embedding = create_embedding(question)

    # Soruya en çok benzeyen chunk'ları bulur.
    relevant_chunks = find_relevant_chunks(
        question_embedding=question_embedding,
        chunks=chunks,
        top_k=request.top_k,
    )

    context = build_context(relevant_chunks= relevant_chunks)

    answer = generate_answer(
    question=question,
    context=context,
    )

    return {
        "document_id": document_id,
        "question": question,
        "sources": relevant_chunks,
        "answer": answer,
    }