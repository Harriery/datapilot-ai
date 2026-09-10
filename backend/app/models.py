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


class DataQualityNextStep(BaseModel):
    next_step: str = Field(max_length=120)



# MissingValuesValidationResult:
#
# Bir missing-values transformation sonucunu structured olarak tutar.
#
# Örnek:
# age kolonunda transformation öncesi 3 null,
# transformation sonrası 1 null varsa:
#
# column = "age"
# before_null_count = 3
# after_null_count = 1
# success = True
#
# Böylece validation sonucu sadece True/False değil,
# hangi veriye dayanarak başarılı olduğu da backend tarafından bilinir.
class MissingValuesValidationResult(BaseModel):
    column: str
    before_null_count: int
    after_null_count: int
    success: bool


# DuplicateRowsValidationResult:
#
# Duplicate row transformation sonucunu structured olarak tutar.
#
# Örnek:
#
# transformation öncesi duplicate_count = 4
# transformation sonrası duplicate_count = 1
#
# success = True
class DuplicateRowsValidationResult(BaseModel):
    before_duplicate_count: int
    after_duplicate_count: int
    success: bool



# DataQualityTransformationResponse:
#
# Junior'ın yaptığı gerçek data transformation doğrulandıktan sonra
# servis katmanının ürettiği structured sonuç.
#
# validation:
# before/after data sonucunun gerçek teknik doğrulaması.
#
# evidence:
# validation sonucundan üretilen learning evidence.
#
# skill_status:
# evidence kaydedildikten sonraki güncel learner seviyesi.
class DataQualityTransformationResponse(BaseModel):
    skill_name: str

    skill_status: Literal[
        "new",
        "learning",
        "practicing",
        "comfortable",
    ]

    validation: ( MissingValuesValidationResult | DuplicateRowsValidationResult)
    evidence: LearningEvidenceDecision

# DataQualityTransformationRequest:
#
# Junior'ın yaptığı gerçek data transformation'ın
# before/after sonucunu backend'e göndermek için kullanılır.
#
# before_rows:
# transformation öncesindeki data satırları.
#
# after_rows:
# transformation sonrasındaki data satırları.
#
# Route bu listeleri pandas DataFrame'e dönüştürecek
# ve review_data_quality_transformation() servisine gönderecek.
class DataQualityTransformationRequest(BaseModel):
    learner_id: str
    finding: DataQualityFinding
    before_rows: list[dict]
    after_rows: list[dict]

# DataEngineeringTaskStep:
#
# Multi-step bir Data Engineering görevinin
# tek bir adımını temsil eder.
#
# Örnek:
#
# Step 1
# ↓
# age kolonundaki missing values problemini çöz
#
# finding:
# Bu adımda hangi data quality problemiyle
# ilgilenildiğini söyler.
#
# status:
# Junior bu adıma henüz başlamadı mı,
# üzerinde çalışıyor mu,
# yoksa tamamladı mı?
class DataEngineeringTaskStep(BaseModel):
    step_number: int
    title: str
    finding: DataQualityFinding

    status: Literal[
        "pending",
        "active",
        "completed",
    ] = "pending"


# DataEngineeringTask:
#
# Junior'ın üzerinde çalıştığı multi-step
# Data Engineering görevinin tamamını temsil eder.
#
# Örnek:
#
# Task
# ├── Step 1 → missing values
# ├── Step 2 → duplicate rows
# └── Step 3 → başka bir data quality problemi
#
# steps:
# Göreve ait bütün adımları tutar.
#
# current_step_number:
# Junior'ın şu anda hangi adım üzerinde çalıştığını belirtir.
#
# status:
# Görev henüz başlamadı mı,
# devam ediyor mu,
# yoksa tamamen tamamlandı mı?
class DataEngineeringTask(BaseModel):
    task_id: str
    title: str
    steps: list[DataEngineeringTaskStep]

    current_step_number: int = 1

    status: Literal[
        "pending",
        "active",
        "completed",
    ] = "pending"


#"Junior ne yaptı?" , "Doğru yaptı mı?" ,"Hangi skill gelişti?", "Task şimdi hangi step'te?"
# DataEngineeringTaskTransformationResponse:
#
# Bir task step'i üzerinde yapılan gerçek transformation sonrası
# hem learner gelişimini hem de task'ın yeni durumunu birlikte döndürür.
class DataEngineeringTaskTransformationResponse(BaseModel):
    task: DataEngineeringTask

    skill_name: str

    skill_status: Literal[
        "new",
        "learning",
        "practicing",
        "comfortable",
    ]

    validation: (
        MissingValuesValidationResult
        | DuplicateRowsValidationResult
    )

    evidence: LearningEvidenceDecision


# DataEngineeringTaskTransformationRequest:
#
# Junior'ın multi-step task içindeki mevcut step için
# yaptığı gerçek transformation'ı API'ye gönderir.
#
# task:
# Junior'ın mevcut task durumu.
#
# before_rows / after_rows:
# Transformation öncesi ve sonrası gerçek data.
class DataEngineeringTaskTransformationRequest(BaseModel):
    learner_id: str
    task_id: str
    before_rows: list[dict]
    after_rows: list[dict]

# DataEngineeringTaskCreateRequest:
#
# Yeni bir multi-step task ilk kez oluşturulurken kullanılır.
#
# learner_id:
# Task hangi junior'a ait?
#
# task:
# Başlangıçtaki DataEngineeringTask yapısı.
class DataEngineeringTaskCreateRequest(BaseModel):
    learner_id: str
    task: DataEngineeringTask

# ==================================================
# LEARNER PROGRESS
# ==================================================

# LearnerSkillProgress:
#
# Junior'ın tek bir skill'deki mevcut gelişim özetini temsil eder.
#
# Örnek:
#
# null_analysis
# status = practicing
# attempts = 6
# successful_attempts = 5
# success_rate = 0.83
# last_assistance_level = NUDGE
class LearnerSkillProgress(BaseModel):
    skill_name: str

    status: Literal[
        "new",
        "learning",
        "practicing",
        "comfortable",
    ]

    attempts: int
    successful_attempts: int

    success_rate: float

    last_assistance_level: Literal[
        "NONE",
        "NUDGE",
        "GUIDE",
        "TEACH",
        "DEMONSTRATE",
    ] | None = None

    independence_trend: Literal[
        "improving",
        "stable",
        "declining",
        "insufficient_data",
    ] = "insufficient_data"

    practice_priority: Literal[
        "high",
        "medium",
        "low",
        "none",
    ] = "none"


# LearnerProgressResponse:
#
# Bir junior'ın bütün takip edilen skill'lerdeki
# gelişim özetini API'ye döndürmek için kullanılır.
class LearnerProgressResponse(BaseModel):
    learner_id: str
    skills: list[LearnerSkillProgress]


# ==================================================
# PRACTICE SYSTEM
# ==================================================

# PracticeRecommendation:
#
# Progress sisteminin sonucuna göre
# junior'ın hangi skill üzerinde practice yapmasının
# daha faydalı olduğunu temsil eder.
class PracticeRecommendation(BaseModel):
    skill_name: str

    priority: Literal[
        "high",
        "medium",
        "low",
    ]

    difficulty: Literal[
        "foundation",
        "easy",
        "medium",
        "hard",
    ]

    reason: str


# PracticeRecommendationResponse:
#
# Bir learner için önerilen sıradaki practice hedefini döndürür.
#
# recommendation = None olabilir.
# Örneğin bütün skill'ler comfortable ise
# şu anda zorunlu bir practice önerisi olmayabilir.
class PracticeRecommendationResponse(BaseModel):
    learner_id: str
    recommendation: PracticeRecommendation | None


# ==================================================
# PRACTICE CHALLENGE
# ==================================================

# PracticeChallenge:
#
# Junior'ın Practice alanında çözeceği
# tek bir challenge'ı temsil eder.
#
# Challenge henüz execution veya validation yapmaz.
# Sadece junior'ın önüne çıkacak görevin yapısını tanımlar.
class PracticeChallenge(BaseModel):
    challenge_id: str

    skill_name: str

    difficulty: Literal[
        "foundation",
        "easy",
        "medium",
        "hard",
    ]

    challenge_type: Literal[
        "code",
        "debug",
        "output_prediction",
        "sql",
        "data_investigation",
        "transformation",
        "validation",
        "explain",
    ]

    title: str

    instructions: str

    starter_code: str | None = None

# PracticeChallengeRecord:
#
# Backend'in challenge'ı validate edebilmesi için
# public challenge bilgisi ile birlikte
# kullanıcıya gösterilmeyecek validation bilgisini tutar.
class PracticeChallengeRecord(BaseModel):
    challenge: PracticeChallenge

    expected_outcome: str 


# PracticeChallengeResponse:
#
# Bir learner için oluşturulmuş challenge'ı API'ye döndürür.
class PracticeChallengeResponse(BaseModel):
    learner_id: str
    challenge: PracticeChallenge


class PracticeAttemptRequest(BaseModel):
    learner_id: str
    challenge_id: str

    # Junior'ın yazdığı cevap veya kod.
    answer: str

    # Kod frontend'de çalıştırıldıysa oluşan çıktı.
    execution_output: str | None = None

    # Kod çalışırken hata oluştuysa hata mesajı.
    execution_error: str | None = None


class PracticeAttemptValidation(BaseModel):
    success: bool

    # Backend'in deterministik olarak belirleyebildiği
    # kısa teknik sonuç.
    feedback: str


class PracticeAttemptResponse(BaseModel):
    learner_id: str
    challenge_id: str

    validation: PracticeAttemptValidation

class PracticeDiagnosis(BaseModel):

    # Junior'ın doğru kullandığı kavramların
    # backend tarafından takip edilen sabit ID'leri.
    understood_concept_ids: list[
        Literal[
            "iteration",
            "conditional_logic",
            "none_check",
            "dictionary_key_access",
            "counting_matches",
            "output_result",
        ]
    ] = []

    # Junior'ın eksik/zayıf olduğu kavramların
    # backend tarafından takip edilen sabit ID'leri.
    missing_concept_ids: list[
        Literal[
            "iteration",
            "conditional_logic",
            "none_check",
            "dictionary_key_access",
            "counting_matches",
            "output_result",
        ]
    ] = []

    # Bu attempt'te ÖNCE ele alınması gereken tek ana problem.
    primary_missing_concept_id: Literal[
        "iteration",
        "conditional_logic",
        "none_check",
        "dictionary_key_access",
        "counting_matches",
        "output_result",
    ] | None = None

    # AI'nin insan tarafından okunabilir açıklamaları.
    understands: list[str]

    missing_concepts: list[str]

    misconception: str | None = None

    needs_concept_teaching: bool = False

    confidence: Literal[
        "low",
        "medium",
        "high",
    ] = "medium"


class PracticeMentorDecision(BaseModel):
    assistance_level: Literal[
        "NONE",
        "NUDGE",
        "GUIDE",
        "TEACH",
        "DEMONSTRATE",
    ]

    support_strategy: Literal[
        "feedback",
        "recall",
        "focus",
        "concept_explanation",
        "worked_example",
    ]

    reason: str

    # Küçük bir kontrol sorusu gerekli mi?
    needs_micro_check: bool = False 

class PracticeAttemptRecord(BaseModel):
    # DB'deki benzersiz attempt kimliği.
    attempt_id: str

    # Aynı challenge için kaçıncı deneme?
    attempt_number: int

    # Junior'ın gönderdiği cevap/kod.
    attempt: PracticeAttemptRequest

    # Deterministic validation sonucu.
    validation: PracticeAttemptValidation

    # Attempt başarısızsa AI diagnosis burada tutulabilir.
    diagnosis: PracticeDiagnosis | None = None

    # Junior'a hangi seviyede destek verildi?
    mentor_decision: PracticeMentorDecision | None = None

class PracticeMentorSupport(BaseModel):
    # Junior'a gösterilecek ana mentor mesajı.
    message: str

    # TEACH / DEMONSTRATE gibi durumlarda
    # küçük bir kontrol sorusu olabilir.
    micro_check: str | None = None
class PracticeAttemptReview(BaseModel):
    learner_id: str
    challenge_id: str

    attempt_id: str
    attempt_number: int

    validation: PracticeAttemptValidation

    diagnosis: PracticeDiagnosis | None = None
    mentor_decision: PracticeMentorDecision | None = None
    mentor_support: PracticeMentorSupport | None = None

# ==================================================
# PUBLIC PRACTICE ATTEMPT RESPONSE
# ==================================================
#
# Junior'a / frontend'e sadece gerekli bilgiler gösterilir.
#
# diagnosis ve mentor_decision backend-internal kalır.
# Böylece AI diagnosis içindeki çözüm ipuçları
# public API response'a sızmaz.
class PracticeAttemptPublicResponse(BaseModel):
    learner_id: str
    challenge_id: str

    attempt_id: str
    attempt_number: int

    validation: PracticeAttemptValidation

    mentor_support: PracticeMentorSupport | None = None

class LearnerLanguageUpdateRequest(BaseModel):
    preferred_language: Literal[
        "auto",
        "tr",
        "en",
        "nl",
    ]


class LearnerLanguageResponse(BaseModel):
    learner_id: str

    preferred_language: Literal[
        "auto",
        "tr",
        "en",
        "nl",
    ]