"""
Bu dosya belge yükleme endpoint'lerini içerir.

Bu dosya RAG sisteminin belge hazırlama aşamasını yönetir.

Belge hazırlama akışı:
- PDF veya TXT dosyasını alır.
- Dosyadan metni çıkarır.
- Metni chunk'lara böler.
- Belgeyi ve chunk'ları SQLite'a kaydeder.
- Kaydedilen belge ve chunk'ları geri getirir.

Şu an RAG'in belge hazırlama (document ingestion) aşamasındayız.
Embedding, retrieval ve belgeye dayalı cevap üretme daha sonra eklenecek.
"""

from fastapi import APIRouter, HTTPException, UploadFile
from pypdf import PdfReader
from backend.app.database import insert_chunks, insert_document, get_document_by_id, get_chunks_by_document

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

    # Belge bilgilerini documents tablosuna kaydeder.
    document_id = insert_document(
        filename=file.filename,
        content_type=file.content_type,
    )

    # Chunk'ları aynı document_id ile chunks tablosuna kaydeder.
    insert_chunks(
        document_id=document_id,
        chunks=chunks,
    )

    return {                    # Endpoint Python sözlüğü döndürüyor
        "document_id": document_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "character_count": len(text),
        "preview": text[:200],
        "chunk_count": len(chunks),
        "first_chunk_preview": chunks[0][:200],
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
            }
            for chunk in chunks     # tek bir chunk değil, birden fazla chunk’tan oluşan liste döndürür
        ],
    }