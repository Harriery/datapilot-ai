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

    # Mesaj belirli bir workspace içinden geliyorsa
    # frontend workspace_id'yi de gönderir.
    workspace_id: str | None = None



class ChatResponse(BaseModel):      #/chat endpoint’inin başarılı cevabında
                                    #reply isimli string alan bulunacak.
    reply: str

# ==================================================
# DOCUMENT SECURITY
# ==================================================

class DocumentMetadata(BaseModel):
    document_id: int

    # Eski / migrate edilmemiş document kayıtlarında
    # owner henüz bilinmeyebilir.
    learner_id: str | None = None

    filename: str
    content_type: str

    # "unknown" eski veya henüz sınıflandırılmamış
    # document'lar için güvenli ara durumdur.
    usage_context: Literal[
        "personal",
        "work",
        "unknown",
    ] = "unknown"

    # Work document'larında kullanılacak.
    organization_id: str | None = None
    workspace_id: str | None = None

    data_sensitivity: Literal[
        "public",
        "internal",
        "confidential",
        "restricted",
        "unknown",
    ] = "unknown"

    # Default deny:
    # Security policy açıkça izin vermedikçe
    # external AI processing kapalı kalır.
    ai_processing_status: Literal[
        "allowed",
        "blocked",
        "pending",
    ] = "blocked"

    created_at: str | None = None

class DocumentSecurityDecision(BaseModel):

    ai_processing_status: Literal[
        "allowed",
        "blocked",
        "pending",
    ]

    external_ai_allowed: bool

    reason_code: Literal[
        "allowed_public",
        "allowed_personal_internal",
        "allowed_organization_internal",
        "unknown_context",
        "unknown_sensitivity",
        "organization_required",
        "organization_policy_required",
        "organization_policy_blocked",
        "sensitive_data_blocked",
    ]

    reason: str

class DocumentAccessDecision(BaseModel):

    allowed: bool

    reason_code: Literal[
        "allowed",
        "unknown_owner",
        "owner_mismatch",
        "unknown_context",
        "context_mismatch",
        "organization_required",
        "organization_mismatch",
    ]

    reason: str
class DocumentAskRequest(BaseModel):
    learner_id: str

    usage_context: Literal[
        "personal",
        "work",
    ]

    organization_id: str | None = None

    question: str

    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
    )

    session_id: str


class DocumentSearchRequest(BaseModel):
    learner_id: str

    usage_context: Literal[
        "personal",
        "work",
    ]

    organization_id: str | None = None

    question: str

    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
    )

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


class WorkspacePlanStepDraft(BaseModel):
    # AI hangi finding üzerinde çalışılacağını
    # index ile belirtir.
    finding_index: int = Field(ge=0)

    # Junior'ın göreceği kısa çalışma adımı.
    title: str = Field(
        min_length=1,
        max_length=120,
    )


class WorkspacePlanDraft(BaseModel):
    # AI'nın önerdiği genel plan başlığı.
    title: str = Field(
        min_length=1,
        max_length=120,
    )

    # Sıralanmış çalışma adımları.
    steps: list[WorkspacePlanStepDraft]


class WorkspaceExecutionPlanRequest(BaseModel):
    # Dataset'in güvenli profiling sonucu.
    # sample_rows backend tarafında AI'ya
    # gönderilmeden önce tekrar filtrelenecek.
    profile: dict

    # Profil analizinden gelen doğrulanmış findings.
    findings: list[DataQualityFinding]


class WorkspaceExecutionPlanResponse(BaseModel):
    # Oluşturulup DB'ye kaydedilmiş gerçek task.
    task: DataEngineeringTask

class WorkspaceFindingMentorResponse(BaseModel):
    finding_index: int

    finding: DataQualityFinding

    skill_name: str

    skill_status: Literal[
        "new",
        "learning",
        "practicing",
        "comfortable",
    ]

    assistance_level: Literal[
        "NONE",
        "NUDGE",
        "GUIDE",
    ]

    mentor_response: str

    source: Literal[
        "local",
    ] = "local"

class WorkspaceFindingAttemptRequest(BaseModel):
    attempt: str = Field(
        min_length=1,
        max_length=4000,
    )


class WorkspaceFindingAttemptResponse(BaseModel):
    finding_index: int

    skill_name: str

    skill_status: Literal[
        "new",
        "learning",
        "practicing",
        "comfortable",
    ]

    mentor_response: str

    evidence: LearningEvidenceDecision

    source: Literal[
        "local",
        "external_ai",
    ]

class WorkspaceWorkingDataResponse(
    BaseModel
):
    columns: list[str]
    row_count: int
    rows: list[dict]

class WorkspaceTransformationRequest(BaseModel):
    after_rows: list[dict]

class WorkspaceVersionSummary(BaseModel):
    version_number: int
    label: str
    created_at: str
    row_count: int

class WorkspaceValidationCheck(BaseModel):
    name: str

    status: Literal[
        "passed",
        "failed",
        "warning",
    ]

    message: str

    code: Literal[
        "dataset_integrity",
        "schema_preserved",
        "duplicate_rows",
        "missing_values",
    ] | None = None

    params: dict = Field(
        default_factory=dict
    )


class WorkspaceValidationResponse(BaseModel):
    passed: bool

    source_row_count: int
    working_row_count: int

    checks: list[
        WorkspaceValidationCheck
    ]

class WorkspaceReviewResponse(BaseModel):
    completed: bool
    message: str
    working_row_count: int

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
# WORKSPACE
# ==================================================
#
# Workspace:
# Junior'ın belirli bir iş / proje bağlamını temsil eder.
#
# Amaç:
# Farklı çalışmaların birbirine karışmasını önlemek.
#
# Global learner progress workspace'ler arasında ortak olabilir.
# Ancak:
#
# - task
# - kaldığı yer
# - hata
# - sonraki adımlar
# - mentor konuşması
#
# workspace'e özel kalır.


class WorkspaceCheckpoint(BaseModel):
    # Junior'ın bu workspace içinde tamamladığı
    # önemli adımlar.
    completed_items: list[str] = Field(
        default_factory=list
    )

    # Junior şu anda tam olarak ne üzerinde çalışıyor?
    current_focus: str | None = None

    # İlerlemeyi engelleyen bir problem varsa.
    blocked_reason: str | None = None

    # Son teknik hata.
    last_error: str | None = None

    # Junior geri geldiğinde önerilecek
    # sıradaki küçük adımlar.
    next_actions: list[str] = Field(
        default_factory=list
    )


class Workspace(BaseModel):
    workspace_id: str
    learner_id: str

    title: str

    # Workspace gerçek şirket işi için mi,
    # yoksa kullanıcının bireysel çalışması için mi?
    usage_context: Literal[
        "work",
        "personal",
    ] = "work"

    # Work workspace'in hangi organization'a
    # ait olduğunu belirtir.
    #
    # Personal workspace için None kalır.
    organization_id: str | None = None

    # Sadece work workspace'lerde anlamlıdır.
    # Şimdilik metadata olarak saklanır.
    # Gerçek security enforcement daha sonra eklenecek.
    data_sensitivity: Literal[
        "public",
        "internal",
        "confidential",
        "restricted",
        "unknown",
    ] | None = None

    # Junior'a şirket / ekip tarafından verilen
    # iş tanımı.
    task_brief: str | None = None

    # İş tamamlandığında beklenen sonuç.
    desired_outcome: str | None = None

    # Çalışmanın genel veri mühendisliği akışı.
    # "auto" ise ileride mentor task brief'e göre
    # uygun workflow'u seçecek.
    workflow_type: Literal[
        "auto",
        "etl",
        "elt",
        "data_quality",
        "analysis",
        "pipeline",
    ] = "auto"

    dataset_filename: str | None = None

    dataset_profile: dict | None = None

    dataset_analysis: DataQualityAnalysis | None = None

    dataset_ai_processing_status: Literal[
        "allowed",
        "blocked",
        "pending",
    ] | None = None

    dataset_analysis_source: Literal[
        "local",
        "local_and_ai",
        "local_ai_fallback",
    ] | None = None

    validation_result: WorkspaceValidationResponse | None = None

    workspace_type: Literal[
        "data_engineering",
        "practice",
        "general",
    ]

    status: Literal[
        "active",
        "paused",
        "completed",
    ] = "active"

    # Workspace bir Data Engineering task'ına
    # bağlıysa task id burada tutulabilir.
    current_task_id: str | None = None

    # Bu workspace'e ait mentor konuşmasının
    # session id'si.
    #
    # Böylece başka workspace'in sohbetiyle
    # karışmaz.
    mentor_session_id: str | None = None

    checkpoint: WorkspaceCheckpoint = Field(
        default_factory=WorkspaceCheckpoint
    )

class TaskSummaryItem(BaseModel):
    workspace_id: str
    workspace_title: str

    task_id: str | None = None
    task_title: str

    status: Literal[
        "todo",
        "active",
        "blocked",
        "completed",
    ]

    current_step: str | None = None
    next_action: str | None = None

    validation_passed: bool = False
    review_completed: bool = False
    handoff_completed: bool = False

    usage_context: Literal[
        "work",
        "personal",
    ]


class TaskSummaryResponse(BaseModel):
    learner_id: str
    tasks: list[TaskSummaryItem]


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


class MentorDependencyPoint(BaseModel):
    attempt_number: int
    skill_name: str

    assistance_level: Literal[
        "NONE",
        "NUDGE",
        "GUIDE",
        "TEACH",
        "DEMONSTRATE",
    ]

    independence_percent: int

    created_at: str | None = None


class OverallReadiness(BaseModel):
    level: Literal[
        "GUIDE",
        "NUDGE",
        "INDEPENDENT",
    ]

    score: int

    knowledge_score: int
    independence_score: int
    skill_coverage: int

    covered_skills: int
    total_skills: int
    total_attempts: int


# LearnerProgressResponse:
#
# Bir junior'ın bütün takip edilen skill'lerdeki
# gelişim özetini API'ye döndürmek için kullanılır.
class LearnerProgressResponse(BaseModel):
    learner_id: str
    skills: list[LearnerSkillProgress]

    mentor_dependency_history: list[
        MentorDependencyPoint
    ] = Field(default_factory=list)

    overall_readiness: OverallReadiness | None = None


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
        "multiple_choice",
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

    # Junior'ın değiştirmemesi gereken
    # soru bağlamı / örnek kod / verilen veri.
    context_code: str | None = None

    # Çoktan seçmeli challenge için seçenekler.
    options: list[str] | None = None

    starter_code: str | None = None
    # Transformation challenge'larında junior'a
    # verilecek başlangıç datası.
    input_rows: list[dict] | None = None

# ==================================================
# PRACTICE VALIDATION SPEC
# ==================================================
#
# Backend'in challenge sonucunu nasıl kontrol edeceğini
# makine tarafından anlaşılır şekilde tanımlar.
#
# Örnek:
#
# validation_type = "exact_output"
# expected_output = "2"
class PracticeValidationSpec(BaseModel):
    validation_type: Literal[
        "exact_output",
        "exact_answer",
        "null_count_reduction",
        "duplicate_count_reduction",
    ]

    expected_output: str | None = None
    expected_answer: str | None = None
    column: str | None = None

class PracticeSupportSpec(BaseModel):
    # Küçükten büyüğe ilerleyen hazır ipuçları.
    # Frontend'e challenge oluşturulurken gönderilmez.
    hints: list[str] = Field(default_factory=list)

    # Junior yeterince denedikten sonra
    # gösterilebilecek örnek tam çözüm.
    solution: str | None = None

class PracticeHintRequest(BaseModel):
    learner_id: str
    challenge_id: str


class PracticeHintResponse(BaseModel):
    challenge_id: str

    hint: str | None

    hint_number: int

    total_hints: int

    assistance_level: Literal[
        "NUDGE",
        "GUIDE",
        "TEACH",
    ] | None = None

    solution_available: bool = False


# PracticeChallengeRecord:
#
# Public challenge + backend'e özel validation bilgisi.
#
# validation_spec:
# Yeni structured validation sistemi.
#
# expected_outcome:
# Eski kayıtlarla uyumluluk için şimdilik tutuluyor.
# Birazdan tamamen kaldıracağız.
class PracticeChallengeRecord(BaseModel):
    challenge: PracticeChallenge

    validation_spec: PracticeValidationSpec | None = None

    # Backend'e özel yardım bilgileri.
    # Public PracticeChallenge içinde bulunmaz.
    support_spec: PracticeSupportSpec | None = None

    expected_outcome: str | None = None


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

    # Transformation challenge sonucunda junior'ın
    # ürettiği yeni dataset.
    result_rows: list[dict] | None = None


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


# ==================================================
# PRACTICE MENTOR SUPPORT
# ==================================================
#
# Junior'a gösterilecek mentor mesajını ve
# varsa küçük kontrol sorusunu tutar.
#
# PracticeAttemptRecord'dan ÖNCE tanımlanır,
# çünkü attempt record içinde de kullanılacak.
class PracticeMentorSupport(BaseModel):
    message: str
    micro_check: str | None = None


class PracticeAttemptRecord(BaseModel):
    # DB'deki benzersiz attempt kimliği.
    attempt_id: str

    # Aynı challenge için kaçıncı deneme?
    attempt_number: int

    # Junior'ın gönderdiği cevap/kod.
    attempt: PracticeAttemptRequest

    # Deterministic validation sonucu.
    validation: PracticeAttemptValidation

    # Attempt başarısızsa internal AI diagnosis.
    diagnosis: PracticeDiagnosis | None = None

    # Backend'in seçtiği mentor yardım kararı.
    mentor_decision: PracticeMentorDecision | None = None

    # Junior'a gerçekten gösterilen mentor mesajı.
    #
    # Bunu saklamamızın nedeni:
    # Daha sonra junior micro-check cevabı gönderdiğinde
    # hangi soruya cevap verdiğini backend'in bilmesi.
    mentor_support: PracticeMentorSupport | None = None


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

# ==================================================
# PRACTICE MICRO-CHECK
# ==================================================
#
# Mentor TEACH / DEMONSTRATE desteğinden sonra
# junior'a küçük bir kontrol sorusu sorabilir.
#
# Junior'ın bu soruya verdiği cevap
# ayrı olarak değerlendirilir.


class PracticeMicroCheckRequest(BaseModel):
    learner_id: str

    # Micro-check hangi practice attempt'ten geldi?
    attempt_id: str

    # Junior'ın micro-check'e verdiği cevap.
    answer: str


class PracticeMicroCheckValidation(BaseModel):
    success: bool
    feedback: str


class PracticeMicroCheckSupport(BaseModel):
    message: str


class PracticeMicroCheckResponse(BaseModel):
    learner_id: str
    attempt_id: str

    validation: PracticeMicroCheckValidation

    next_action: Literal[
        "return_to_challenge",
        "more_support",
    ]

    # Sadece yanlış micro-check cevabında gelir.
    # Doğru cevapta None olur.
    additional_support: PracticeMicroCheckSupport | None = None

# ==================================================
# PRACTICE MICRO-CHECK ATTEMPT RECORD
# ==================================================
#
# Junior'ın bir micro-check sorusuna verdiği
# tek bir cevabın DB kaydını temsil eder.
#
# Aynı micro-check birden fazla kez cevaplanabilir.
class PracticeMicroCheckAttemptRecord(BaseModel):
    micro_check_attempt_id: str

    learner_id: str
    attempt_id: str

    micro_check_attempt_number: int

    answer: str

    validation: PracticeMicroCheckValidation

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


class WorkspaceCreateRequest(BaseModel):
    learner_id: str
    title: str

    usage_context: Literal[
        "work",
        "personal",
    ] = "work"

    organization_id: str | None = None
    
    data_sensitivity: Literal[
        "public",
        "internal",
        "confidential",
        "restricted",
        "unknown",
    ] | None = None

    task_brief: str | None = None
    desired_outcome: str | None = None

    workflow_type: Literal[
        "auto",
        "etl",
        "elt",
        "data_quality",
        "analysis",
        "pipeline",
    ] = "auto"

    workspace_type: Literal[
        "data_engineering",
        "practice",
        "general",
    ] = "data_engineering"

    current_task_id: str | None = None

class WorkspaceCheckpointUpdateRequest(BaseModel):
    checkpoint: WorkspaceCheckpoint

class WorkspaceStatusUpdateRequest(BaseModel):
    status: Literal[
        "active",
        "paused",
        "completed",
    ]

class WorkspaceResumeResponse(BaseModel):
    workspace_id: str
    title: str

    status: Literal[
        "active",
        "paused",
        "completed",
    ]

    checkpoint: WorkspaceCheckpoint

    # Frontend'in "Şimdi ne yapmalıyım?"
    # alanında doğrudan gösterebilmesi için.
    next_action: str | None = None

class PracticeSolutionRequest(BaseModel):
    learner_id: str
    challenge_id: str


class PracticeSolutionResponse(BaseModel):
    challenge_id: str
    solution: str

    assistance_level: Literal[
        "DEMONSTRATE",
    ] = "DEMONSTRATE"
