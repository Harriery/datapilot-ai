from __future__ import annotations

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

    # Frontend'in o anda gerçekten hangi ekran/sekmede olduğunu taşır.
    # Bu state yalnızca konuşmayı bağlama oturtmak için kullanılır;
    # kullanıcının sorusunu o sekmeye zorla kilitlemez.
    ui_context: dict | None = None



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

class ExternalAIProcessingDecision(BaseModel):

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
# Backward compatibility:
# Eski document-specific kodlar kırılmasın.
DocumentSecurityDecision = ExternalAIProcessingDecision

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

    # Reusable conceptual error when one is confidently identifiable.
    misconception: str | None = None

class LearningEvidenceContext(BaseModel):
    """
    Learning Evidence V2 context.

    The core evidence fields (skill, success, assistance level, type)
    stay query-friendly in SQL. This model stores the richer project
    context needed by the adaptive mentor without hard-coding one dataset.
    """

    workspace_id: str | None = None
    stage: str | None = None

    learning_phase: Literal[
        "observe",
        "reason",
        "decide",
        "implement",
        "validate",
        "explain",
    ] | None = None

    task_type: str | None = None
    target_type: str | None = None
    target_name: str | None = None

    user_authored: bool | None = None
    deterministic_validation: bool | None = None

    misconception: str | None = None
    metadata: dict = Field(default_factory=dict)


class PrepareLearningPhaseEvaluation(BaseModel):
    is_evidence: bool
    success: bool | None = None

    evidence_type: Literal[
        "application",
        "explanation",
        "debugging",
        "validation",
    ] | None = None

    note: str | None = None
    misconception: str | None = None


class PrepareMentorReply(BaseModel):
    mentor_reply: str = Field(
        min_length=1,
        max_length=600,
    )


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

    # row_count is the number of rows actually sent to the client.
    # total_row_count keeps the server-side dataset size visible when
    # notebook/browser execution intentionally receives only a sample.
    total_row_count: int | None = None
    sampled: bool = False


class WorkspaceDataPreviewResponse(BaseModel):
    dataset: Literal[
        "source",
        "working",
    ]

    columns: list[str]
    column_types: dict[str, Literal[
        "text",
        "number",
        "datetime",
        "boolean",
    ]] = Field(default_factory=dict)

    total_row_count: int
    filtered_row_count: int

    page: int
    page_size: int
    total_pages: int

    rows: list[dict]


class WorkspaceTransformationRequest(BaseModel):
    after_rows: list[dict]

class WorkspaceVersionSummary(BaseModel):
    version_number: int
    label: str
    created_at: str
    row_count: int

    operation_id: str | None = None
    operation_title: str | None = None

    operation_type: Literal[
        "clean",
        "transform",
        "schema",
        "business_rule",
        "enrichment",
        "custom",
    ] | None = None

    transformation_code: str | None = None

    schema_changed: bool | None = None

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
        "pipeline_replay",
        "full_data_preflight",
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

class PersonalProjectColumnIntelligence(BaseModel):
    name: str
    data_type: str = "unknown"
    null_count: int = 0
    null_percentage: float = 0.0
    distinct_count: int = 0
    cardinality_ratio: float = 0.0
    examples: list[str] = Field(default_factory=list)
    minimum: float | None = None
    maximum: float | None = None
    role_candidates: list[
        Literal["key", "numeric", "dimension", "time"]
    ] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"
    reasoning: list[str] = Field(default_factory=list)


class PersonalProjectModelDiscovery(BaseModel):
    grain: str
    fact_table_candidate: str
    dimension_table_candidates: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"
    reasoning: list[str] = Field(default_factory=list)


class PersonalProjectAnalysisPlan(BaseModel):
    # Legacy name kept for downstream/backward compatibility.
    measure_candidates: list[str] = Field(default_factory=list)
    numeric_candidates: list[str] = Field(default_factory=list)
    key_candidates: list[str] = Field(default_factory=list)
    dimension_candidates: list[str] = Field(default_factory=list)
    time_candidates: list[str] = Field(default_factory=list)
    column_intelligence: list[PersonalProjectColumnIntelligence] = Field(
        default_factory=list
    )
    model_discovery: PersonalProjectModelDiscovery | None = None
    suggested_questions: list[str] = Field(default_factory=list)
    source: Literal["local"] = "local"


class PersonalProjectAnalysisResult(BaseModel):

    # Her kaydedilmiş analysis sonucunun
    # benzersiz kimliği.
    #
    # Eski workspace kayıtlarının bozulmaması
    # için şimdilik None kabul ediyoruz.
    analysis_id: str | None = None

    measure: str
    dimension: str | None = None

    # Semantic-model aware metadata. Optional fields keep
    # older saved analysis records backward compatible.
    kpi_code: str | None = None
    dimension_table: str | None = None
    aggregation: Literal[
        "count",
        "sum",
        "mean",
        "min",
        "max",
        "custom",
    ] | None = None

    overall: dict = Field(
        default_factory=dict
    )

    grouped_results: list[dict] = Field(
        default_factory=list
    )

    source: Literal[
        "local",
    ] = "local"
class PersonalProjectAnalysisRequest(BaseModel):
    # Legacy raw-column analysis input.
    measure: str | None = None

    # Semantic analysis input. When kpi_code is provided,
    # the backend resolves the saved KPI definition from
    # workspace state instead of trusting frontend metadata.
    kpi_code: str | None = None

    dimension_table: str | None = None
    dimension: str | None = None

class PersonalProjectAnalysisDeleteRequest(BaseModel):
    analysis_id: str


class PersonalProjectDashboardVisual(BaseModel):
    visual_id: str
    analysis_id: str | None = None

    kpi_code: str | None = None
    dimension_table: str | None = None
    dimension: str | None = None

    visual_type: Literal[
        "kpi",
        "bar",
        "column",
        "line",
        "area",
        "pie",
        "donut",
        "table",
    ]

    title: str
    subtitle: str | None = None
    auto_title: bool = True

    size: Literal[
        "compact",
        "small",
        "medium",
        "large",
    ] = "large"

    sort_mode: Literal[
        "top_value",
        "bottom_value",
        "alphabetical",
        "chronological",
        "highest_count",
        "lowest_count",
    ] = "top_value"

    top_n: int = Field(
        default=10,
        ge=1,
        le=50,
    )

    accent_color: str = "#2f80ed"
    background_color: str = "#ffffff"
    text_color: str = "#213854"

    x_axis_title: str | None = None
    y_axis_title: str | None = None
    show_values: bool = True
    show_legend: bool = True
    show_gridlines: bool = True
    animate: bool = True
    tooltip_template: str | None = None

    grid_column: int | None = Field(
        default=None,
        ge=1,
        le=12,
    )

    # Fine-grained dashboard canvas layout. Optional fields keep
    # previously saved grid-based dashboards backward compatible.
    canvas_x: int | None = Field(default=None, ge=0, le=10000)
    canvas_y: int | None = Field(default=None, ge=0, le=10000)
    canvas_width: int | None = Field(default=None, ge=120, le=4000)
    canvas_height: int | None = Field(default=None, ge=96, le=4000)

    title_alignment: Literal[
        "left",
        "center",
        "right",
    ] = "left"

    kpi_label: str | None = None
    kpi_label_font_size: int = Field(default=10, ge=6, le=32)
    kpi_label_bold: bool = False
    kpi_label_color: str | None = None
    kpi_show_secondary: bool = False
    kpi_value_alignment: Literal[
        "left",
        "center",
        "right",
    ] = "center"
    kpi_vertical_alignment: Literal[
        "top",
        "center",
        "bottom",
    ] = "center"

    title_font_size: int = Field(
        default=10,
        ge=7,
        le=28,
    )
    title_bold: bool = True
    title_color: str | None = None

    subtitle_font_size: int = Field(
        default=7,
        ge=6,
        le=20,
    )
    subtitle_bold: bool = False
    subtitle_color: str | None = None

    category_label_font_size: int = Field(
        default=8,
        ge=6,
        le=22,
    )
    category_label_bold: bool = False
    category_label_color: str | None = None

    value_label_font_size: int = Field(
        default=8,
        ge=6,
        le=64,
    )
    value_label_bold: bool = True
    value_label_color: str | None = None

    axis_label_font_size: int = Field(
        default=8,
        ge=6,
        le=20,
    )
    axis_label_bold: bool = False
    axis_label_color: str | None = None

    legend_label_font_size: int = Field(
        default=8,
        ge=6,
        le=20,
    )
    legend_label_bold: bool = False
    legend_label_color: str | None = None


class PersonalProjectDashboardFilter(BaseModel):
    filter_id: str

    table: str
    column: str
    label: str

    value: (
        str | int | float | bool | None
    ) = None

    values: list[
        str | int | float | bool
    ] = Field(default_factory=list)


class PersonalProjectDashboardPreviewRequest(BaseModel):
    kpi_code: str
    dimension_table: str | None = None
    dimension: str | None = None

    filters: list[
        PersonalProjectDashboardFilter
    ] = Field(default_factory=list)


class PersonalProjectDashboardFilterValuesRequest(BaseModel):
    table: str
    column: str


class PersonalProjectDashboardFilterValuesResponse(BaseModel):
    values: list[
        str | int | float | bool | None
    ] = Field(default_factory=list)


class PersonalProjectDashboardConfig(BaseModel):
    title: str = "Dashboard"
    subtitle: str | None = None

    theme: Literal[
        "ocean",
        "teal",
        "violet",
        "sunset",
        "slate",
    ] = "ocean"

    visuals: list[
        PersonalProjectDashboardVisual
    ] = Field(default_factory=list)

    filters: list[
        PersonalProjectDashboardFilter
    ] = Field(default_factory=list)


class PersonalProjectDashboardSaveRequest(BaseModel):
    title: str = "Dashboard"
    subtitle: str | None = None

    theme: Literal[
        "ocean",
        "teal",
        "violet",
        "sunset",
        "slate",
    ] = "ocean"

    visuals: list[
        PersonalProjectDashboardVisual
    ] = Field(
        min_length=1
    )

    filters: list[
        PersonalProjectDashboardFilter
    ] = Field(default_factory=list)


class PersonalProjectKPIDefinition(BaseModel):
    code: str
    title: str

    fact_table: str | None = None

    measure: str | None = None

    aggregation: Literal[
        "count",
        "sum",
        "mean",
        "min",
        "max",
    ] | None = None

    dimension_table: str | None = None
    dimension: str | None = None

    filter_value: (
        str | int | float | bool | None
    ) = None

    formula_mode: Literal[
        "safe_aggregation",
        "row_count",
        "custom",
    ] | None = None

    formula: str | None = None

    description: str

    source: Literal[
        "local",
        "user",
    ] = "local"


class PersonalProjectKPIBuilderRequest(BaseModel):
    definitions: list[
        PersonalProjectKPIDefinition
    ] = Field(
        min_length=1
    )


class PersonalProjectKPISelectionRequest(BaseModel):
    codes: list[str] = Field(
        min_length=1
    )

class PersonalProjectDataModelMeasure(BaseModel):
    code: str
    title: str

    column: str | None = None

    aggregation: Literal[
        "count",
        "sum",
        "mean",
        "min",
        "max",
    ]| None = None

    dimension: str | None = None



class ProjectDeliverable(BaseModel):
    code: str
    title: str

    status: Literal[
        "pending",
        "in_progress",
        "completed",
    ] = "pending"

    required: bool = True



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

class PersonalProjectDataModelPlan(BaseModel):
    model_type: Literal[
        "single_table",
        "star_schema_candidate",
    ]

    base_table: str

    grain: str

    dimensions: list[str] = Field(
        default_factory=list
    )

    time_dimension: str | None = None

    measures: list[
        PersonalProjectDataModelMeasure
    ] = Field(default_factory=list)

    recommended_dimension_tables: list[
        str
    ] = Field(default_factory=list)

    source: Literal[
        "local",
    ] = "local"

class PersonalProjectDataModelMappingRule(BaseModel):
    source_value: str
    display_value: str


class PersonalProjectDataModelBucketRule(BaseModel):
    min_value: str
    max_value: str
    label: str


class PersonalProjectDataModelDerivation(BaseModel):
    type: Literal[
        "date_part",
        "numeric",
        "text",
        "multi_column",
        "mapping",
        "bucketing",
    ]

    operation: str = Field(min_length=1)

    source_columns: list[str] = Field(
        min_length=1
    )

    parameters: dict[
        str,
        str | int | float | bool | None,
    ] = Field(default_factory=dict)

    mapping_rules: list[
        PersonalProjectDataModelMappingRule
    ] = Field(default_factory=list)

    bucket_rules: list[
        PersonalProjectDataModelBucketRule
    ] = Field(default_factory=list)


class PersonalProjectDataModelColumn(BaseModel):
    name: str

    source_column: str | None = None

    derivation: (
        PersonalProjectDataModelDerivation | None
    ) = None

    role: Literal[
        "key",
        "foreign_key",
        "dimension",
        "measure",
        "attribute",
        "time",
    ]

    aggregation: Literal[
        "count",
        "sum",
        "mean",
        "min",
        "max",
    ] | None = None


class PersonalProjectDataModelTable(BaseModel):
    name: str

    table_type: Literal[
        "fact",
        "dimension",
        "bridge",
    ]

    columns: list[
        PersonalProjectDataModelColumn
    ] = Field(default_factory=list)


class PersonalProjectDataModelRelationship(BaseModel):
    from_table: str
    from_column: str

    to_table: str
    to_column: str

    cardinality: Literal[
        "many_to_one",
        "one_to_many",
        "one_to_one",
    ] = "many_to_one"

    active: bool = True


class PersonalProjectDataModelNodePosition(BaseModel):
    x: float
    y: float


class PersonalProjectDataModelStudio(BaseModel):
    tables: list[
        PersonalProjectDataModelTable
    ] = Field(default_factory=list)

    relationships: list[
        PersonalProjectDataModelRelationship
    ] = Field(default_factory=list)

    node_positions: dict[
        str,
        PersonalProjectDataModelNodePosition,
    ] = Field(default_factory=dict)

    source: Literal[
        "local",
        "user",
    ] = "local"



class WorkspaceReplacementCondition(BaseModel):
    column: str
    value: str | int | float | bool | None = None


class WorkspaceValueReplacement(BaseModel):
    old_value: str | int | float | bool | None = None
    new_value: str | int | float | bool | None = None
    conditions: list[
        WorkspaceReplacementCondition
    ] = Field(default_factory=list)


class WorkspacePipelineAction(BaseModel):
    action: Literal[
        "rename",
        "remove",
        "change_type",
        "fill_missing",
        "replace_values",
        "derived",
    ]

    column: str

    new_name: str | None = None

    data_type: Literal[
        "string",
        "integer",
        "float",
        "datetime",
    ] | None = None

    fill_strategy: Literal[
        "value",
        "mean",
        "median",
        "mode",
        "zero",
        "mapping",
    ] | None = None

    fill_value: (
        str | int | float | bool | None
    ) = None

    mapping_source_column: str | None = None

    mapping_only_unambiguous: bool = True

    old_value: (
        str | int | float | bool | None
    ) = None

    new_value: (
        str | int | float | bool | None
    ) = None

    replacements: list[
        WorkspaceValueReplacement
    ] = Field(default_factory=list)

    derived_name: str | None = None

    derived_operation: Literal[
        "copy",
        "uppercase",
        "lowercase",
        "add",
        "multiply",
    ] | None = None

    derived_value: (
        str | int | float | bool | None
    ) = None


class WorkspaceWorkbenchOperationCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    goal: str = Field(min_length=1)

    operation_type: Literal[
        "clean",
        "transform",
        "schema",
        "business_rule",
        "enrichment",
        "custom",
    ]

    source_columns: list[str] = Field(
        default_factory=list
    )

    expected_columns: list[str] = Field(
        default_factory=list
    )

    pipeline_action: (
        WorkspacePipelineAction | None
    ) = None

    draft_code: str | None = Field(
        default=None,
        max_length=20000,
    )


class WorkspaceWorkbenchOperation(BaseModel):
    operation_id: str

    title: str
    goal: str

    operation_type: Literal[
        "clean",
        "transform",
        "schema",
        "business_rule",
        "enrichment",
        "custom",
    ]

    origin: Literal[
        "data_quality",
        "project_requirement",
        "user",
    ]

    status: Literal[
        "pending",
        "active",
        "completed",
    ] = "pending"

    source_columns: list[str] = Field(
        default_factory=list
    )

    expected_columns: list[str] = Field(
        default_factory=list
    )

    code: str | None = None

    pipeline_action: (
        WorkspacePipelineAction | None
    ) = None

    finding_index: int | None = None
    rollback_version_number: int | None = None
    result_version_id: str | None = None

    # A reviewed data-quality finding can be completed without mutating
    # the dataset. This is intentionally distinct from a replayable
    # transformation.
    decision: Literal[
        "accepted_as_is",
    ] | None = None
    decision_reason: str | None = None


class WorkspaceWorkbenchDecisionRequest(BaseModel):
    reason: str = Field(
        min_length=3,
        max_length=1000,
    )


class WorkspaceWorkbenchPreview(BaseModel):
    operation_id: str

    code: str

    before_row_count: int
    after_row_count: int

    before_columns: list[str] = Field(
        default_factory=list
    )

    after_columns: list[str] = Field(
        default_factory=list
    )

    sample_rows: list[dict] = Field(
        default_factory=list
    )

    source: Literal["local"] = "local"



class WorkspaceWorkbenchTransformationRequest(BaseModel):
    operation_id: str = Field(
        min_length=1
    )

    code: str = Field(
        min_length=1,
        max_length=20000,
    )

    after_rows: list[dict] = Field(
        min_length=1
    )

    pipeline_action: (
        WorkspacePipelineAction | None
    ) = None


class WorkspaceWorkbenchTransformationResponse(BaseModel):
    operation: WorkspaceWorkbenchOperation

    active_operation_id: str | None = None

    before_row_count: int
    after_row_count: int

    schema_changed: bool

    working_data: WorkspaceWorkingDataResponse


class WorkspaceDevelopmentSampleRequest(BaseModel):
    sample_size: int = Field(
        ge=1,
        le=20000,
    )

    strategy: Literal[
        "random",
        "smart",
    ] = "random"

    random_seed: int = 42


class WorkspaceDevelopmentSampleResponse(BaseModel):
    source_row_count: int
    working_row_count: int

    requested_sample_size: int

    strategy: Literal[
        "random",
        "smart",
    ]

    random_seed: int

    sampled: bool


class WorkspaceSmartSamplingRequest(BaseModel):
    candidate_sizes: list[int] = Field(
        default_factory=lambda: [
            5000,
            10000,
            20000,
        ],
        min_length=1,
        max_length=3,
    )

    random_seed: int = 42


class WorkspaceSmartSamplingResponse(BaseModel):
    source_row_count: int
    selected_size: int
    selected_strategy: str
    candidate_evaluations: list[dict] = Field(
        default_factory=list
    )
    selected_evaluation: dict | None = None
    threshold: float
    rare_coverage_threshold: float | None = None
    reason: str
    full_data_preflight_required: bool = True


class WorkspaceFullDataPreflightResponse(BaseModel):
    passed: bool
    source_row_count: int
    checks: list[dict] = Field(
        default_factory=list
    )
    engine: Literal["duckdb"] = "duckdb"


class WorkspaceFullPipelineResponse(BaseModel):
    source_row_count: int
    working_row_count: int

    applied_operation_ids: list[str] = Field(
        default_factory=list
    )

    applied_operation_count: int

    development_sample_disabled: bool = True


class WorkspaceNotebookCell(BaseModel):
    cell_id: str
    code: str = ""

    cell_type: Literal[
        "python",
    ] = "python"

    # Optional user-defined notebook section. Existing notebooks remain
    # backward compatible because ungrouped cells keep this as None.
    section_title: str | None = Field(
        default=None,
        max_length=80,
    )

    # Compact browser-execution evidence. We intentionally persist only a
    # bounded observation so the mentor can see the learner's work without
    # sending an entire dataframe back through chat.
    last_execution: dict | None = None


class WorkspaceNotebook(BaseModel):
    notebook_id: str

    name: str = Field(
        min_length=1,
        max_length=80,
    )

    dataset_kind: Literal[
        "working",
        "raw",
        "processed",
    ] = "working"

    processed_dataset_id: (
        str | None
    ) = None

    cells: list[
        WorkspaceNotebookCell
    ] = Field(default_factory=list)

    created_at: str
    updated_at: str


class WorkspaceNotebookMentorRequest(BaseModel):
    code: str = Field(
        min_length=1,
        max_length=20000,
    )


class WorkspaceNotebookMentorResponse(BaseModel):
    guidance: list[str] = Field(
        default_factory=list
    )

    source: Literal[
        "local",
    ] = "local"


class WorkspaceNotebookCreateRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=80,
    )

    dataset_kind: Literal[
        "working",
        "raw",
        "processed",
    ] = "working"

    processed_dataset_id: (
        str | None
    ) = None


class WorkspaceNotebookUpdateRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=80,
    )

    dataset_kind: Literal[
        "working",
        "raw",
        "processed",
    ] = "working"

    processed_dataset_id: (
        str | None
    ) = None

    cells: list[
        WorkspaceNotebookCell
    ] = Field(default_factory=list)


class WorkspaceProcessedDatasetCreateRequest(
    BaseModel
):
    name: str = Field(
        min_length=1,
        max_length=80,
    )


class WorkspaceProcessedDataset(BaseModel):
    dataset_id: str

    name: str

    row_count: int
    column_count: int

    created_at: str

    source: Literal[
        "working_snapshot",
    ] = "working_snapshot"


class WorkspaceLearningLoopMessage(BaseModel):
    role: Literal[
        "user",
        "assistant",
    ]
    content: str = Field(
        min_length=1,
        max_length=4000,
    )


class WorkspaceLearningLoop(BaseModel):
    loop_id: str

    language: Literal[
        "en",
        "nl",
        "tr",
    ] = "en"

    stage: Literal[
        "prepare",
    ] = "prepare"

    finding_index: int
    skill_name: str

    target_type: Literal[
        "column",
        "dataset",
    ]

    target_name: str | None = None

    current_phase: Literal[
        "observe",
        "reason",
        "decide",
        "implement",
        "validate",
        "explain",
        "completed",
    ] = "observe"

    completed_phases: list[
        Literal[
            "observe",
            "reason",
            "decide",
            "implement",
            "validate",
            "explain",
        ]
    ] = Field(default_factory=list)

    status: Literal[
        "active",
        "completed",
    ] = "active"

    trusted_validation: dict = Field(
        default_factory=dict
    )

    # Mentor V2 keeps the current evidence-gathering subtask stable across
    # turns. This prevents the LLM from switching comparison columns or
    # restarting an investigation when the learner asks how to continue.
    active_investigation: dict = Field(
        default_factory=dict
    )

    # Mentor V3 project/issue supervisor snapshot. This stores only bounded
    # control state; raw data and large outputs remain outside the model.
    supervisor_state: dict = Field(
        default_factory=dict
    )

    # Deterministic Mentor workflow state. The learner's wording never sets
    # this value; trusted phase/execution state does.
    workflow_state: str | None = None

    # Persisted Guided Learning conversation. This remains UI/history state;
    # only a bounded recent slice may be sent to AI.
    message_history: list[
        WorkspaceLearningLoopMessage
    ] = Field(default_factory=list)


class WorkspaceLearningLoopResponse(BaseModel):
    loop: WorkspaceLearningLoop
    mentor_prompt: str


class WorkspaceLearningLoopResponseRequest(BaseModel):
    response: str = Field(
        min_length=1,
        max_length=4000,
    )

    # Guided Learning receives the same current UI state as Mentor Chat.
    # The learning-loop service allowlists the fields before AI use.
    ui_context: dict | None = None

    # Bounded recent Guided Learning turns prevent the mentor from repeating
    # an action the learner has already completed.
    learning_history: list[dict] = Field(
        default_factory=list
    )


class WorkspaceLearningLoopReviewResponse(BaseModel):
    loop: WorkspaceLearningLoop
    mentor_response: str
    evidence: LearningEvidenceDecision
    assistance_level: Literal[
        "NONE",
        "NUDGE",
        "GUIDE",
        "TEACH",
        "DEMONSTRATE",
    ]


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

    project_type: Literal[
        "data_engineering",
        "data_analysis",
        "bi_dashboard",
        "data_quality",
        "portfolio",
    ] | None = None

    project_deliverables: list[
        ProjectDeliverable
    ] = Field(default_factory=list)

    analysis_plan: (
        PersonalProjectAnalysisPlan | None
    ) = None

    analysis_result: (
        PersonalProjectAnalysisResult | None
    ) = None

    # Personal project içinde oluşturulan
    # bütün analysis sonuçlarını saklar.
    #
    # analysis_result ise backward compatibility
    # için son çalıştırılan sonucu göstermeye devam eder.
    analysis_results: list[
        PersonalProjectAnalysisResult
    ] = Field(default_factory=list)

    dashboard_config: PersonalProjectDashboardConfig = Field(
        default_factory=PersonalProjectDashboardConfig
    )

    kpi_candidates: list[
        PersonalProjectKPIDefinition
    ] = Field(default_factory=list)

    kpi_definitions: list[
        PersonalProjectKPIDefinition
    ] = Field(default_factory=list)

    data_model_plan: (
        PersonalProjectDataModelPlan | None
    ) = None

    data_model_studio: (
        PersonalProjectDataModelStudio | None
    ) = None

    workbench_operations: list[
        WorkspaceWorkbenchOperation
    ] = Field(default_factory=list)

    workbench_active_operation_id: str | None = None

    workbench_preview: (
        WorkspaceWorkbenchPreview | None
    ) = None

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

    development_sample_size: int | None = None

    development_sample_max_size: int | None = None

    development_sample_strategy: Literal[
        "random",
        "smart",
    ] | None = None

    development_sample_seed: int | None = None

    development_sample_row_count: int | None = None

    development_sample_enabled: bool = False

    # Large-data execution metadata. Raw/source remains immutable,
    # the active development sample stays bounded, and full-data
    # results are materialized separately as Silver parquet.
    dataset_storage_mode: Literal[
        "legacy_csv",
        "duckdb",
    ] = "legacy_csv"

    dataset_source_bytes: int | None = None

    full_data_profile: dict | None = None

    smart_sampling_report: dict | None = None

    full_data_preflight: dict | None = None

    silver_dataset_path: str | None = None

    processed_datasets: list[
        WorkspaceProcessedDataset
    ] = Field(default_factory=list)

    notebooks: list[
        WorkspaceNotebook
    ] = Field(default_factory=list)

    active_processed_dataset_id: (
        str | None
    ) = None

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

    learning_loops: list[
        WorkspaceLearningLoop
    ] = Field(default_factory=list)
    
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

    independence_score: int = 0

    latest_learning_phase: Literal[
        "observe",
        "reason",
        "decide",
        "implement",
        "validate",
        "explain",
    ] | None = None

    learning_phase_counts: dict[
        str,
        int,
    ] = Field(default_factory=dict)

    learning_phase_success_counts: dict[
        str,
        int,
    ] = Field(default_factory=dict)

    misconceptions: list[
        str
    ] = Field(default_factory=list)


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
# LEARNER JOURNAL / RESUME STATE
# ==================================================

class LearnerResumePayload(BaseModel):
    topic_id: str | None = None
    subtopic_id: str | None = None
    practice_mode: str | None = None
    difficulty: str | None = None
    source_id: str | None = None
    source_exercise_id: str | None = None

    workspace_id: str | None = None
    stage: str | None = None
    current_view: str | None = None

    metadata: dict = Field(
        default_factory=dict
    )


class LearnerResumeStateUpsertRequest(BaseModel):
    context_type: Literal[
        "practice",
        "workspace",
    ]
    context_key: str = Field(
        min_length=1,
        max_length=240,
    )
    state: LearnerResumePayload


class LearnerResumeState(BaseModel):
    learner_id: str
    context_type: Literal[
        "practice",
        "workspace",
    ]
    context_key: str
    state: LearnerResumePayload
    updated_at: str | None = None


class LearnerNoteCreateRequest(BaseModel):
    context_type: Literal[
        "practice",
        "workspace",
    ]
    context_key: str = Field(
        min_length=1,
        max_length=240,
    )
    title: str | None = Field(
        default=None,
        max_length=120,
    )
    body: str = Field(
        min_length=1,
        max_length=4000,
    )
    source_exercise_id: str | None = None


class LearnerNoteUpdateRequest(BaseModel):
    title: str | None = Field(
        default=None,
        max_length=120,
    )
    body: str | None = Field(
        default=None,
        min_length=1,
        max_length=4000,
    )


class LearnerNote(BaseModel):
    note_id: str
    learner_id: str
    context_type: Literal[
        "practice",
        "workspace",
    ]
    context_key: str
    title: str | None = None
    body: str
    source_exercise_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class LearnerJournalResponse(BaseModel):
    learner_id: str
    context_type: Literal[
        "practice",
        "workspace",
    ]
    context_key: str
    resume_state: LearnerResumeState | None = None
    notes: list[LearnerNote] = Field(
        default_factory=list
    )


# ==================================================
# PRACTICE SYSTEM
# ==================================================

# ==================================================
# PRACTICE V2 CATALOG
# ==================================================

class PracticeSourceDescriptor(BaseModel):
    source_id: str
    name: str
    repository: str
    license: str
    import_policy: Literal[
        "allowed_with_attribution",
        "reference_only_copyleft_review",
        "reference_only_pending_license_review",
    ]
    delivery: Literal[
        "on_demand",
        "metadata_only",
    ]
    topics: list[str] = Field(
        default_factory=list
    )


class PracticeTopicDescriptor(BaseModel):
    topic_id: str
    title: str
    description: str

    modes: list[
        Literal[
            "theory",
            "code",
            "sql",
            "transformation",
            "design",
            "project",
            "mixed",
        ]
    ]

    difficulties: list[
        Literal[
            "easy",
            "medium",
            "hard",
        ]
    ]

    subtopics: list[str] = Field(
        default_factory=list
    )

    mastery_policy: Literal[
        "evidence_based",
    ] = "evidence_based"

    mastery_signals: list[str] = Field(
        default_factory=list
    )

    mini_project_target: int = Field(
        ge=0
    )

    source_ids: list[str] = Field(
        default_factory=list
    )


class PracticeExerciseSourceItem(BaseModel):
    source_id: str
    source_exercise_id: str
    title: str
    source_difficulty: int = Field(
        ge=1
    )
    difficulty: Literal[
        "easy",
        "medium",
        "hard",
    ]
    practices: list[str] = Field(
        default_factory=list
    )
    prerequisites: list[str] = Field(
        default_factory=list
    )
    mastery_signals: list[
        Literal[
            "concept_coverage",
            "correct_application",
            "transfer_to_new_context",
        ]
    ] = Field(default_factory=list)
    attribution: str


class PracticeExerciseSourceResponse(BaseModel):
    learner_id: str
    topic_id: str
    subtopic_id: str
    practice_mode: str
    difficulty: Literal[
        "easy",
        "medium",
        "hard",
    ]
    source_id: str
    exercises: list[
        PracticeExerciseSourceItem
    ]


class PracticeExerciseProgressState(BaseModel):
    source_exercise_id: str
    attempts: int = Field(ge=0)
    client_passes: int = Field(ge=0)
    client_failures: int = Field(ge=0)
    last_client_success: bool | None = None


class PracticeNextExerciseResponse(BaseModel):
    learner_id: str
    topic_id: str
    subtopic_id: str
    practice_mode: str
    difficulty: Literal[
        "easy",
        "medium",
        "hard",
    ]
    source_id: str
    status: Literal[
        "new",
        "resume",
        "next",
        "cycle_complete",
    ]
    exercise: PracticeExerciseSourceItem | None = None
    progress: list[
        PracticeExerciseProgressState
    ] = Field(default_factory=list)
    completed_exercise_count: int = Field(ge=0)
    available_exercise_count: int = Field(ge=0)


class PracticeTheoryConceptItem(BaseModel):
    source_id: str
    concept_id: str
    title: str
    source_path: str
    attribution: str


class PracticeTheoryConceptResponse(BaseModel):
    learner_id: str
    topic_id: str
    subtopic_id: str
    source_id: str
    concepts: list[
        PracticeTheoryConceptItem
    ]


class PracticeTheoryCheckGenerated(BaseModel):
    question: str = Field(
        min_length=10,
        max_length=500,
    )
    options: list[str] = Field(
        min_length=3,
        max_length=4,
    )
    correct_index: int = Field(
        ge=0,
        le=3,
    )
    explanation: str = Field(
        min_length=1,
        max_length=500,
    )


class PracticeTheoryCheckCreateRequest(BaseModel):
    learner_id: str
    subtopic_id: str
    concept_id: str
    difficulty: Literal[
        "easy",
        "medium",
        "hard",
    ]
    language: Literal[
        "en",
        "tr",
        "nl",
    ] = "en"


class PracticeTheoryCheckResponse(BaseModel):
    learner_id: str
    topic_id: str
    subtopic_id: str
    difficulty: Literal[
        "easy",
        "medium",
        "hard",
    ]
    concept_id: str
    challenge: PracticeChallenge
    attribution: str


class PracticeTheoryAnswerRequest(BaseModel):
    learner_id: str
    challenge_id: str
    answer: str


class PracticeTheoryAnswerResponse(BaseModel):
    learner_id: str
    challenge_id: str
    concept_id: str
    success: bool
    feedback: str
    mastery: PracticeMasterySummary


class PracticeTheoryConceptContent(BaseModel):
    learner_id: str
    source_id: str
    concept_id: str
    title: str
    source_path: str
    source_text: str
    attribution: str
    content_hash: str
    cached: bool = False


class PracticeExerciseContentResponse(BaseModel):
    learner_id: str
    source_id: str
    source_exercise_id: str
    title: str
    instructions: str
    solution_filename: str | None = None
    starter_code: str | None = None
    attribution: str
    source_revision: str | None = None
    content_hash: str
    cached: bool = False


class PracticeValidationSourceFile(BaseModel):
    path: str
    content: str


class PracticeTranslationRequest(BaseModel):
    learner_id: str
    source_id: str
    source_exercise_id: str
    content_hash: str
    target_language: Literal[
        "tr",
        "nl",
    ]
    source_text: str = Field(
        min_length=1,
        max_length=30000,
    )


class PracticeTranslationResponse(BaseModel):
    learner_id: str
    source_id: str
    source_exercise_id: str
    content_hash: str
    target_language: Literal[
        "tr",
        "nl",
    ]
    translated_text: str
    provider: str
    model: str
    cached: bool = False


class PracticeExerciseValidationBundle(BaseModel):
    learner_id: str
    source_id: str
    source_exercise_id: str
    solution_filename: str
    test_files: list[
        PracticeValidationSourceFile
    ]
    attribution: str
    source_revision: str | None = None
    content_hash: str
    cached: bool = False


class ExternalPracticeValidationEventRequest(BaseModel):
    learner_id: str
    source_id: str
    source_exercise_id: str
    topic_id: str
    subtopic_id: str
    practice_mode: str
    difficulty: Literal[
        "easy",
        "medium",
        "hard",
    ]
    content_hash: str
    validation_bundle_hash: str
    client_reported_success: bool
    tests_run: int = Field(
        ge=0,
        le=500,
    )
    answer: str = Field(
        max_length=50000
    )


class ExternalPracticeValidationEvent(BaseModel):
    event_id: str
    learner_id: str
    source_id: str
    source_exercise_id: str
    topic_id: str
    subtopic_id: str
    practice_mode: str
    difficulty: Literal[
        "easy",
        "medium",
        "hard",
    ]
    content_hash: str
    validation_bundle_hash: str
    solution_hash: str
    client_reported_success: bool
    tests_run: int
    trust_level: Literal[
        "client_sandbox",
    ] = "client_sandbox"
    created_at: str | None = None


class PracticeMasterySignalState(BaseModel):
    signal: Literal[
        "concept_coverage",
        "correct_application",
        "transfer_to_new_context",
        "independent_completion",
    ]
    demonstrated: bool
    evidence_count: int = Field(
        ge=0
    )


class PracticeMasterySummary(BaseModel):
    learner_id: str
    topic_id: str
    subtopic_id: str
    practice_mode: str
    difficulty: Literal[
        "easy",
        "medium",
        "hard",
    ]
    status: Literal[
        "not_started",
        "building",
        "demonstrated",
    ]
    signals: list[
        PracticeMasterySignalState
    ]
    successful_evidence_count: int = Field(
        ge=0
    )
    independent_success_count: int = Field(
        ge=0
    )


class PracticeCatalogResponse(BaseModel):
    learner_id: str
    level_completion_rule: str
    project_unlock_rule: str
    topics: list[
        PracticeTopicDescriptor
    ]
    sources: list[
        PracticeSourceDescriptor
    ]



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

    # Practice V2 path metadata. Optional fields keep legacy
    # adaptive challenges backward compatible.
    topic_id: str | None = None
    subtopic_id: str | None = None
    practice_mode: Literal[
        "theory",
        "code",
        "sql",
        "transformation",
        "design",
        "project",
        "mixed",
    ] | None = None
    source_id: str | None = None
    source_exercise_id: str | None = None
    mastery_signals: list[
        Literal[
            "concept_coverage",
            "correct_application",
            "transfer_to_new_context",
        ]
    ] = Field(default_factory=list)

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

    project_type: Literal[
        "data_engineering",
        "data_analysis",
        "bi_dashboard",
        "data_quality",
        "portfolio",
    ] | None = None

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
