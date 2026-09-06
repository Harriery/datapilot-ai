"""
Bu dosya, API içinde kullanılan veri modellerini içerir.

Modeller:
- API'ye hangi verilerin gönderileceğini tanımlar.
- API'den hangi verilerin döneceğini tanımlar.
- Verilerin tiplerini kontrol eder.
- Swagger dokümantasyonunun daha anlaşılır olmasını sağlar.

Örnek:
ChatRequest  -> Kullanıcıdan gelen verinin yapısı
ChatResponse -> Kullanıcıya dönen verinin yapısı
"""
from pydantic import BaseModel, Field # Pydantic = Python’da gelen/giden verinin şeklini ve tipini kontrol eden kütüphane.
from typing import Literal # Bir alanın sadece belirlediğimiz sabit değerlerden birini almasını sağlar.

class ChatRequest(BaseModel):
    session_id: str
    message: str

    # Frontend ileride kalıcı learner_id gönderebilir.
    # Gönderilmezse /chat session_id'yi learner_id olarak kullanacak.
    learner_id: str | None = None



class ChatResponse(BaseModel):      #/chat endpoint’inin başarılı cevabında
                                    #reply isimli string alan bulunacak.
    reply: str


class DocumentAskRequest(BaseModel):
    question: str
    top_k: int =Field(default=3, ge=1, le=10)
    session_id: str

class DocumentSearchRequest(BaseModel): # sadece dokuman icinde arama yapiyor.
    question: str
    top_k: int =Field(default=3, ge=1, le=10)   
# Field(...)
# │
# ├── default=3  → top_k gönderilmezse 3
# ├── ge=1       → greater than or equal → en az 1
# └── le=10      → less than or equal → en fazla 10

class MentorDecision(BaseModel):
    skill_name: str
    assistance_level: Literal[ # Sadece izin verilen yardım seviyeleri kabul edilir.
        "NONE",
        "NUDGE",
        "GUIDE",
        "TEACH",
        "DEMONSTRATE",
    ]
    reason: str
# AI’nın “bu mesaj hangi skill ile ilgili?” cevabının şeklini tanımlayacağız.
# skill_name = "python_dict"
# reason = "Kullanıcı dictionary yapısını soruyor."
class SkillDetection(BaseModel):
    skill_name: str | None = None   # → string veya NoneS
    reason: str


class LearningEvidenceDecision(BaseModel):
    # Bu mesaj gerçekten junior'ın bilgisini/uygulamasını gösteriyor mu?
    is_evidence: bool

    # Evidence varsa hangi tür?
    evidence_type: Literal[
        "application",
        "explanation",
        "debugging",
        "validation",
    ] | None = None

    # Evidence varsa başarılı mı?
    success: bool | None = None

    # AI'nın kısa açıklaması
    note: str | None = None

class DataQualityFinding(BaseModel):
    issue_type:Literal[
        "missing_values",
        "duplicate_rows",
        "suspicious_values",
        "data_type_issue",
        "schema_issue",
    ]
    column: str | None = None
    severity : Literal[
        "low",
        "medium",
        "high",
    ]
    observation: str
    suggested_action : str

# DataQualityAnalysis:
# AI'nın CSV profili üzerinden bulduğu tüm data quality problemlerini tutar.
#
# Kullanıldığı yer:
# data_ai_service.py içinde OpenAI structured output modeli olarak kullanılır.
# AI birden fazla DataQualityFinding üretir ve hepsi findings listesinde tutulur.
class DataQualityAnalysis(BaseModel):
    findings: list[DataQualityFinding]


# DataQualityMentorRequest:
# Junior'ın seçtiği bir data quality problemini mentor sistemine göndermek için kullanılır.
#
# learner_id → hangi junior için mentor cevabı üretileceğini belirtir.
# finding    → mentorun hangi DataQualityFinding üzerinde yardım edeceğini belirtir.
#
# Kullanılacağı yer:
# POST /mentor/data-quality endpoint'inde request body modeli olarak kullanılacak.
class DataQualityMentorRequest(BaseModel):
    learner_id: str
    finding: DataQualityFinding

# DataQualityAttemptRequest:
# Junior'ın bir data quality finding için yaptığı kendi denemesini
# mentor sistemine göndermek için kullanılır.
#
# learner_id → hangi junior?
# finding    → hangi veri kalitesi problemi?
# attempt    → junior'ın kendi çözümü / kodu / açıklaması
#
# Kullanılacağı yer:
# POST /mentor/data-quality/attempt
class DataQualityAttemptRequest(BaseModel):
    learner_id: str
    finding: DataQualityFinding
    attempt: str


# DataQualityAttemptResponse:
# Junior'ın attempt'i değerlendirildikten sonra API'nin döndüğü sonuç.
#
# mentor_response → junior'a gösterilecek adaptif mentor cevabı
# skill_name      → finding'in bağlı olduğu skill
# skill_status    → evidence sonrası güncel learner seviyesi
# evidence        → attempt gerçek learning evidence mı, başarılı mı?
class DataQualityAttemptResponse(BaseModel):
    mentor_response: str
    skill_name: str
    skill_status: Literal[
        "new",
        "learning",
        "practicing",
        "comfortable",
    ]
    evidence: LearningEvidenceDecision

class DataQualityAttemptFeedback(BaseModel):
    acknowledgement: str
    next_step: str

class DataQualityNextStep(BaseModel):
    next_step: str = Field(max_length=120)