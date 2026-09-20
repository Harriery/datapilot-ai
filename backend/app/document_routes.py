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

from fastapi import (
    APIRouter,
    HTTPException,
    UploadFile,
    Form,
)
from pypdf import PdfReader
from backend.app.database import(
    insert_chunks,
    insert_document,
    get_document_by_id,
    get_chunks_by_document,
    get_session_by_id,
    insert_message,
    get_messages_by_session,
    get_learner_profile_by_id,
) 
from backend.app.data_security_service import (
    evaluate_external_ai_policy,
)

from backend.app.embedding_service import (
    create_embedding,
    create_embeddings,
)
from backend.app.retrieval_service import find_relevant_chunks
from backend.app.models import DocumentSearchRequest, DocumentAskRequest
from backend.app.rag_service import build_context, generate_answer
from backend.app.document_access_service import (
    evaluate_document_access,
)

router = APIRouter()  # Belge endpoint'lerini gruplar.


# ==================================================
# AYARLAR
# ==================================================
# Kabul edilen dosya türlerini tutar.
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
}

def require_document_access(
    document_id: int,
    learner_id: str,
    usage_context: str,
    organization_id: str | None = None,
):

    document = get_document_by_id(
        document_id
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Belge bulunamadı.",
        )

    decision = evaluate_document_access(
        document=document,
        requester_learner_id=(
            learner_id
        ),
        usage_context=usage_context,
        organization_id=(
            organization_id
        ),
    )

    if not decision.allowed:
        raise HTTPException(
            status_code=403,
            detail=(
                "Bu belgeye erişim izniniz yok."
            ),
        )

    return document

def require_external_ai_access(
    document,
):

    if (
        document["ai_processing_status"]
        != "allowed"
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Bu belge için external AI "
                "processing izinli değil."
            ),
        )

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
def upload_document(
    file: UploadFile,

    learner_id: str = Form(...),

    usage_context: str = Form(...),

    data_sensitivity: str = Form(...),

    organization_id: str | None = Form(
        default=None
    ),

    workspace_id: str | None = Form(
        default=None
    ),
):

    # ==================================================
    # FILE TYPE
    # ==================================================

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                "Yalnızca PDF veya TXT "
                "dosyası yükleyebilirsiniz."
            ),
        )

    # ==================================================
    # LEARNER
    # ==================================================

    learner = get_learner_profile_by_id(
        learner_id
    )

    if learner is None:
        raise HTTPException(
            status_code=404,
            detail="Learner bulunamadı.",
        )

    # ==================================================
    # SECURITY METADATA VALIDATION
    # ==================================================

    if usage_context not in {
        "personal",
        "work",
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "usage_context yalnızca "
                "personal veya work olabilir."
            ),
        )

    if data_sensitivity not in {
        "public",
        "internal",
        "confidential",
        "restricted",
        "unknown",
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "Geçersiz document "
                "sensitivity değeri."
            ),
        )

    # ==================================================
    # SECURITY POLICY
    # ==================================================
    #
    # ÖNEMLİ:
    # Bu kontrol dosya içeriğini okumadan ve
    # external AI çağrısı yapmadan önce gerçekleşir.
    #
    # Work + internal için organization policy
    # henüz implement edilmediği için policy=None.
    # Sonuç PENDING olacaktır.

    security_decision = (
        evaluate_external_ai_policy(
            usage_context=usage_context,
            data_sensitivity=(
                data_sensitivity
            ),
            organization_id=(
                organization_id
            ),
            organization_ai_allowed=None,
        )
    )

    # ==================================================
    # EXTERNAL AI BLOCKED / PENDING
    # ==================================================
    #
    # Güvenlik kararı AI işlemine izin vermiyorsa:
    #
    # - dosya içeriğini okumuyoruz
    # - chunk oluşturmuyoruz
    # - embedding üretmiyoruz
    #
    # V1'de yalnızca document metadata kaydedilir.
    #
    # Daha sonra encrypted local storage
    # eklediğimizde raw file burada güvenli şekilde
    # saklanabilecek.

    if not security_decision.external_ai_allowed:

        document_id = insert_document(
            filename=file.filename,
            content_type=file.content_type,
            learner_id=learner_id,
            usage_context=usage_context,
            organization_id=organization_id,
            workspace_id=workspace_id,
            data_sensitivity=(
                data_sensitivity
            ),
            ai_processing_status=(
                security_decision
                .ai_processing_status
            ),
        )

        return {
            "document_id": document_id,
            "filename": file.filename,

            "usage_context":
                usage_context,

            "data_sensitivity":
                data_sensitivity,

            "ai_processing_status":
                security_decision
                .ai_processing_status,

            "external_ai_allowed":
                False,

            "reason_code":
                security_decision
                .reason_code,

            "security_reason":
                security_decision.reason,

            "content_ingested":
                False,

            "chunk_count":
                0,
        }

    # ==================================================
    # CONTENT EXTRACTION
    # ==================================================
    #
    # Buraya geldiysek policy external AI
    # processing'e açıkça izin verdi.

    if file.content_type == "text/plain":

        file_bytes = file.file.read()

        text = file_bytes.decode(
            "utf-8"
        )

    else:

        text = extract_pdf_text(
            file
        )

    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail=(
                "Dosyadan metin "
                "çıkarılamadı."
            ),
        )

    # ==================================================
    # CHUNKS + EMBEDDINGS
    # ==================================================

    chunks = split_text_into_chunks(
        text
    )

    chunk_embeddings = (
        create_embeddings(
            chunks
        )
    )

    # ==================================================
    # DOCUMENT METADATA
    # ==================================================

    document_id = insert_document(
        filename=file.filename,
        content_type=file.content_type,
        learner_id=learner_id,
        usage_context=usage_context,
        organization_id=organization_id,
        workspace_id=workspace_id,
        data_sensitivity=(
            data_sensitivity
        ),
        ai_processing_status=(
            security_decision
            .ai_processing_status
        ),
    )

    insert_chunks(
        document_id=document_id,
        chunks=chunks,
        embeddings=chunk_embeddings,
    )

    return {
        "document_id": document_id,
        "filename": file.filename,
        "content_type":
            file.content_type,

        "usage_context":
            usage_context,

        "data_sensitivity":
            data_sensitivity,

        "ai_processing_status":
            security_decision
            .ai_processing_status,

        "external_ai_allowed":
            True,

        "reason_code":
            security_decision
            .reason_code,

        "security_reason":
            security_decision.reason,

        "content_ingested":
            True,

        "character_count":
            len(text),

        "preview":
            text[:200],

        "chunk_count":
            len(chunks),

        "first_chunk_preview":
            chunks[0][:200],

        "embedding_count":
            len(chunk_embeddings),

        "first_embedding_length":
            len(
                chunk_embeddings[0]
            ),

        "first_embedding_preview":
            chunk_embeddings[0][:5],
    }


@router.get("/documents/{document_id}")
def get_document(
    document_id: int,
    learner_id: str,
    usage_context: str,
    organization_id: str | None = None,
):

    document = require_document_access(
        document_id=document_id,
        learner_id=learner_id,
        usage_context=usage_context,
        organization_id=organization_id,
    )

    chunks = get_chunks_by_document(
        document_id
    )

    return {
        "document_id":
            document["id"],

        "filename":
            document["filename"],

        "content_type":
            document["content_type"],

        "usage_context":
            document["usage_context"],

        "organization_id":
            document["organization_id"],

        "workspace_id":
            document["workspace_id"],

        "data_sensitivity":
            document["data_sensitivity"],

        "ai_processing_status":
            document[
                "ai_processing_status"
            ],

        "chunks": [
            {
                "chunk_index":
                    chunk["chunk_index"],

                "content":
                    chunk["content"],

                "embedding_length":
                    len(
                        chunk["embedding"]
                    ),

                "embedding_preview":
                    chunk["embedding"][:5],
            }
            for chunk in chunks
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
    document = require_document_access(
        document_id=document_id,
        learner_id=request.learner_id,
        usage_context=request.usage_context,
        organization_id=(
            request.organization_id
        ),
    )

    require_external_ai_access(
        document
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
@router.post("/documents/{document_id}/ask")    # FastAPI gelen JSON body’yi DocumentAskRequest modeline göre doğruluyor ve bize request nesnesi olarak veriyo
def ask_document(
    document_id: int,
    request: DocumentAskRequest,     # question, top_k ve session_id alanlarını taşır
):

    
    # Session veritabanında var mı kontrol eder.
    session = get_session_by_id(request.session_id) # DocumentAskRequest ile session_id dogrulanir
                                                    # Sonra request nesnesi olusur ve request,session_id ile session_id ye ulasilir.

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session bulunamadı. Önce yeni bir session oluşturun.",
        )
    
    # URL'den gelen document_id ile belgeyi veritabanında arar.
    document = require_document_access(
        document_id=document_id,
        learner_id=request.learner_id,
        usage_context=request.usage_context,
        organization_id=(
            request.organization_id
        ),
    )
    
    require_external_ai_access(
        document
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

    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="Belgede aranabilir içerik bulunamadı.",
        )

    # Kullanıcının sorusunu sayı listesine dönüştürür.
    question_embedding = create_embedding(question)

    # Soruya en çok benzeyen chunk'ları bulur.
    relevant_chunks = find_relevant_chunks(
        question_embedding=question_embedding,
        chunks=chunks,
        top_k=request.top_k,
    )

    context = build_context(relevant_chunks= relevant_chunks)
    history = get_messages_by_session(request.session_id)
    
    #kullanicin sorusunu kaydediyoruz.
    insert_message(     
        session_id=request.session_id,
        role="user",
        content=question, #yukarda trip ile bosluklarini almistik.
    )


    # OpenAI tarafında bağlantı/API hatası olursa endpoint 500 ile patlayabilir.
    # Biz bunun yerine kullanıcıya anlaşılır bir API hatası döndüreceğiz.
    try:
        answer = generate_answer(   #rag_service icinden generate_answer fonk gore doldurduk.
            question=question,
            context=context,
            history=history,
        )

    except Exception:
        raise HTTPException(
            status_code= 502,
            detail= "AI servisine şu anda ulaşılamıyor."
        )
    
    
    insert_message(                 # o session'a ait eski mesajlari getirdik, oncesinde biz bu session ile user in sorusunu kaydetmistik
        session_id=request.session_id,
        role="assistant",
        content=answer,
        )

    return {
        "document_id": document_id,
        "question": question,
        "sources": relevant_chunks,
        "answer": answer,
    }