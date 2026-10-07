import json
from backend.app.models import (
    MentorDecision,
    SkillDetection,
    LearningEvidenceDecision,
    LearningEvidenceContext,
    DataQualityFinding,
    DataQualityAttemptResponse,
    DataQualityNextStep,
    MissingValuesValidationResult,
    DataQualityTransformationResponse,
    DuplicateRowsValidationResult,
    DataEngineeringTask,
    DataEngineeringTaskTransformationResponse,
)
import backend.app.database as database
import pandas as pd
from backend.app.transformation_validation_service import (
    validate_transformation_for_finding,
)
from backend.app.ai_usage_guard import (
    guarded_responses_create,
    guarded_responses_parse,
)
from backend.app.ai_provider_service import (
    get_ai_runtime,
)

from backend.app.task_service import (
    get_current_task_step,
    apply_validation_result_to_task,
)
from backend.app.mentor_classifier_policy import (
    classifier_generation_kwargs,
    learning_evidence_classifier_rules,
)
from backend.app.mentor_orchestration_service import (
    determine_assistance_level,
)
from backend.app.mentor_misconception_taxonomy import (
    normalize_misconception,
)

# MentorDecision bizim models.py dosyasında oluşturduğumuz Pydantic modelidir.
# Provider/model selection is centralized in ai_provider_service.


# Mentor sisteminin MVP'de takip ettiği skill'ler.
# AI relevant skill seçerken yalnızca bu katalogdaki değerleri kullanmalıdır.
# Skill = junior'ın farklı görevlerde tekrar tekrar kullanacağı
# öğrenilebilir bir yetkinliktir.
# Tek bir soru, fonksiyon veya kütüphane için ayrı skill oluşturmayız.
SKILL_CATALOG = {
    # Python
    "python_basics",
    "python_data_structures",
    "python_functions",
    "python_error_handling",
    "debugging",

    # Code / Software Understanding
    "code_flow",
    "software_concepts",
    "api_backend_flow",

    # Data / Pandas
    "pandas_dataframe",
    "data_types",
    "data_transformation",

    # Data Quality
    "null_analysis",
    "duplicate_analysis",
    "schema_analysis",
    "numeric_analysis",
    "data_validation",

    # SQL / Database
    "sql_basics",
    "sql_joins",
    "sql_aggregation",
    "database_fundamentals",

    # Data Engineering
    "etl_elt",
    "pipeline_concepts",
    "data_modeling",
    "file_formats",
    "medallion_architecture",
    "semantic_modeling",
    "kpi_design",
    "data_analysis",
    "dashboard_design",
    "data_interpretation",
    "technical_documentation",

    # Engineering Workflow
    "testing",
    "git_workflow",
    "development_environment",
}


DATA_QUALITY_SKILL_MAP = {
    "missing_values": "null_analysis",
    "duplicate_rows": "duplicate_analysis",
    "suspicious_values": "numeric_analysis",
    "data_type_issue": "data_types",
    "schema_issue": "schema_analysis",
}


# learner_profile
# → {"answer_length": "concise", ...}
# 
# skill_state
# → {"skill_name": "python_dict", "status": "learning", ...}
# 
# learning_evidence
# → [{...}, {...}]
# 
# current_message
# → "Dictionary nasıl oluşturuyorduk?"



# Learner profile, skill state, learning evidence ve mevcut mesajı
# AI'nın okuyabileceği tek bir prompt metnine dönüştürür.
def build_mentor_decision_prompt(
    learner_profile: dict,
    skill_state: dict,
    learning_evidence: list[dict],
    current_message: str,
):
    profile_text = json.dumps(learner_profile, ensure_ascii=False, indent=2)# json.dumps() → Python dict/list'i düzenli bir string'e çevirir.
    skill_text = json.dumps(skill_state, ensure_ascii=False, indent=2)        # ensure_ascii=False → Türkçe karakterleri düzgün bırakır.
    evidence_text = json.dumps(learning_evidence, ensure_ascii=False, indent=2) # indent=2 → okunabilir şekilde girintiler.

    prompt = f"""
        Learner Profile:
        {profile_text}

        Skill State:
        {skill_text}

        Learning Evidence:
        {evidence_text}

        Current Message:
        {current_message}
        """
    return prompt


#“Elimdeki learner context'i AI'ya gönder ve bana standart bir MentorDecision geri getir.”
def generate_mentor_decision(
    learner_profile: dict,
    skill_state: dict,
    learning_evidence: list[dict],
    current_message: str,
):
    """
    Assistance level is deterministic in Mentor V2.
    Historical evidence remains available to learner/progress systems, while
    the current message can immediately increase support when the learner is
    stuck.
    """
    skill_name = str(
        skill_state.get("skill_name")
        or ""
    )
    skill_status = str(
        skill_state.get("status")
        or "new"
    )

    assistance_level = determine_assistance_level(
        skill_status=skill_status,
        learner_message=current_message,
    )

    return MentorDecision(
        skill_name=skill_name,
        assistance_level=assistance_level,
        reason=(
            "Deterministic Mentor V2 assistance policy based on "
            f"skill_status={skill_status} and the current support request."
        ),
    )


#  output_parsed Mesela prompt kabaca şöyle görünür:

# Learner Profile:
# answer_length = concise
# learning_style = guided
# 
# Skill State:
# python_dict
# status = learning
# attempts = 3
# 
# Learning Evidence:
# GUIDE ile başarılı oldu
# NUDGE ile zorlandı
# 
# Current Message:
# "Dictionary nasıl oluşturuyorduk?"

# AI da yukardaki profile bakıp asagidaki gibi karar verecek:

#assistance_level = TEACH
# veya
#assistance_level = GUIDE

#--------------------------------------------------------------------


# Learner'ın DB'deki profilini, skill durumunu ve geçmiş evidence'larını toplar.
# Bu context'i AI mentor karar servisine gönderir ve MentorDecision döndürür.
def get_mentor_decision_for_learner(
        learner_id: str,
        skill_name:str,
        current_message:str
        ):

    learner_profile = database.get_learner_profile_by_id(learner_id)
    if learner_profile is None:
        raise ValueError("Learner profile bulunamadı.")

    if skill_name not in SKILL_CATALOG:
        raise ValueError("Bu skill_name katalogda bulunmamaktadir.")
    
    skill_state = database.get_skill_state(learner_id, skill_name,)
    if skill_state is None:
        database.insert_skill_state(
            learner_id,
            skill_name,
            status = "new"
        )
        skill_state = database.get_skill_state(learner_id, skill_name)

    
    learning_evidence = database.get_learning_evidence_by_skill(learner_id, skill_name,)

    # SQLite Row verilerini AI/prompt tarafında kullanabilmek için
    # normal Python dict yapılarına dönüştürüyoruz.
    learner_profile = dict(learner_profile)
    skill_state = dict(skill_state)
    learning_evidence = [dict(row) for row in learning_evidence]    #learning_evidence listesindeki
                                                                        # her row'u al
                                                                        # ↓
                                                                        # dict(row) yap
                                                                        # ↓
                                                                        # yeni liste oluştur
    ai_decision = generate_mentor_decision(learner_profile, skill_state, learning_evidence, current_message)

    
    return ai_decision


STAGE_SKILL_FALLBACK = {
    "data_model": "data_modeling",
    "kpis": "kpi_design",
    "bi_dataset": "semantic_modeling",
    "analysis": "data_analysis",
    "dashboard": "dashboard_design",
    "insights": "data_interpretation",
    "docs": "technical_documentation",
    "prepare.workbench": "data_transformation",
    "prepare.workbench.notebook": "pandas_dataframe",
    "prepare.workbench.pipeline": "pipeline_concepts",
    "prepare.validate": "data_validation",
}


def _workspace_product_path(
    workspace_context: dict | None,
) -> str | None:
    product = (
        (workspace_context or {}).get(
            "mentor_product_context"
        )
        or {}
    )
    current = product.get("current")

    if isinstance(current, dict):
        path = current.get("path")
        if isinstance(path, str):
            return path

    return None


def _is_contextual_stage_message(
    message: str,
) -> bool:
    normalized = message.casefold()
    markers = (
        "burada",
        "burda",
        "şimdi",
        "simdi",
        "bunu",
        "bunun",
        "hangi buton",
        "hangi seçenek",
        "hangi secenek",
        "ne yap",
        "nasıl",
        "nasil",
        "doğru mu",
        "dogru mu",
        "here",
        "this",
        "what next",
        "which button",
        "which option",
        "is this correct",
    )
    return any(
        marker in normalized
        for marker in markers
    )


def detect_relevant_skill(
    current_message: str,
    workspace_context: dict | None = None,
):


    skills_text = ", ".join(SKILL_CATALOG)# skill katologiunu metne cevirdik ai in okumasi icin.
    product_path = _workspace_product_path(
        workspace_context
    )

    if (
        product_path in STAGE_SKILL_FALLBACK
        and _is_contextual_stage_message(
            current_message
        )
    ):
        return SkillDetection(
            skill_name=(
                STAGE_SKILL_FALLBACK[
                    product_path
                ]
            ),
            reason=(
                "Active DataPilot stage resolves this contextual message "
                "without an AI classification call."
            ),
        )

    instructions = f"""
        Kullanıcının mesajına en uygun skill'i seç.

        Sadece aşağıdaki skill'lerden birini seç:
        {skills_text}

        Eğer listedeki hiçbir skill mesajla gerçekten ilgili değilse:
        skill_name = null döndür.

        Yeni bir skill adı üretme.
        Current Product Path yalnız bağlamdır; sırf bir ekranda bulunmak learning
        evidence anlamına gelmez. Ancak kısa/bağlamsal mesajlarda doğru skill'i
        seçmek için bu stage bilgisini kullanabilirsin.
        Neden bu kararı verdiğini kısa şekilde açıkla.

        Current Product Path:
        {product_path}
    """
    runtime = get_ai_runtime(
        "classifier"
    )

    response = guarded_responses_parse(
        runtime.client,
        provider=runtime.provider,
        purpose="mentor_skill_detection",
        model=runtime.model,
        input=current_message,
        instructions=instructions,
        text_format=SkillDetection,
        **classifier_generation_kwargs(),
    )

    detection = response.output_parsed# modele gore olusturulmus sonuc (SkillDetection)
    if detection.skill_name is not None and detection.skill_name not in SKILL_CATALOG:
        raise ValueError("Geçersiz skill tespit edildi.")

    if (
        detection.skill_name is None
        and product_path in STAGE_SKILL_FALLBACK
    ):
        detection.skill_name = (
            STAGE_SKILL_FALLBACK[
                product_path
            ]
        )
        detection.reason = (
            "Active DataPilot stage provides the skill context."
        )

    return detection

def get_mentor_decision_from_message(
    learner_id: str,
    current_message: str,
    workspace_context: dict | None = None,
    ):

    # Burada SkillDetection nesnesini aldık.
    # skill_name değerine skill_detection.skill_name ile ulaşırız.
    skill_detection = detect_relevant_skill(
        current_message,
        workspace_context=workspace_context,
    )
    if skill_detection.skill_name is None:
        return None
    decision = get_mentor_decision_for_learner(
        learner_id,
        skill_detection.skill_name,
        current_message,
        )
    return decision

ASSISTANCE_GUIDELINES = {
    "NONE": (
        "Junior görevi bağımsız yapabiliyor. "
        "Sadece kısa doğrulama veya review ver. "
        "Yeni konu öğretme, çözüm üretme veya uzun açıklama yapma."
    ),

    "NUDGE": (
        "Sadece küçük bir ipucu ver. "
        "En fazla 1-2 kısa cümle kullan. "
        "Kod veya doğrudan çözüm verme."
    ),

    "GUIDE": (
        "Junior'a yalnızca bir sonraki küçük adımı ver. "
        "En fazla 2-3 kısa cümle kullan. "
        "Birden fazla adım, uzun kontrol listesi veya tam çözüm verme. "
        "Junior bu adımı tamamladıktan sonra sonraki adıma geç."
    ),

    "TEACH": (
        "Gerekli kavramı kısa şekilde açıkla. "
        "Neden kullanıldığını belirt ve gerekirse tek küçük örnek ver. "
        "Sonra junior'ın kendisinin uygulamasını iste. "
        "Uzun ders veya tam çözüm verme."
    ),

    "DEMONSTRATE": (
        "Junior ciddi şekilde takılmışsa tek bir çalışan örnek göster. "
        "Örneğin ne yaptığını kısa şekilde açıkla. "
        "Sonrasında benzer kısmı junior'ın kendisinin yapmasını iste. "
        "Birden fazla alternatif çözüm veya uzun açıklama verme."
    ),
}

def generate_mentor_response(
    learner_profile: dict,
    mentor_decision: MentorDecision,  # AI'nin MentorDecision modeline göre ürettiği karar
    current_message: str,
    conversation_history: list[dict] | None = None,
    workspace_context: dict | None = None,
):
    # mentor_decision bir Pydantic modelidir.
    # .assistance_level ile örn. "GUIDE" değerini alıyoruz.
    #
    # ASSISTANCE_GUIDELINES ise bir dict'tir.
    # Bu "GUIDE" değerini dict içinde key olarak kullanıp
    # o seviyeye ait mentor davranış kuralını alıyoruz.
    effective_assistance_level = mentor_decision.assistance_level

    # Turn-level confusion/help requests must shape the response even when
    # historical evidence says the learner is usually independent.
    normalized_message = current_message.casefold()
    beginner_help_markers = (
        "adım adım", "adim adim", "anlamadım", "anlamadim",
        "bilmiyorum", "ne yapmam gerekiyor", "nasıl yapacağım",
        "nasil yapacagim", "öğretir misin", "ogretir misin",
        "step by step", "i don't understand", "i dont understand",
        "i don't know", "i dont know", "teach me",
    )
    explicit_beginner_help = any(
        marker in normalized_message for marker in beginner_help_markers
    )
    if explicit_beginner_help:
        effective_assistance_level = "GUIDE"

    guideline = ASSISTANCE_GUIDELINES[
        effective_assistance_level
    ]
    # learner_profile bir dict.
    # AI prompt'una ekleyebilmek için JSON metnine çeviriyoruz.
    learner_profile_text = json.dumps(
        learner_profile,
        ensure_ascii=False,
        indent=2,
    )   

    conversation_history_text = json.dumps(
    conversation_history or [],
    ensure_ascii=False,
    indent=2,
    )

    workspace_context_text = json.dumps(
    workspace_context or {},
    ensure_ascii=False,
    indent=2,
    )

    current_step = (workspace_context or {}).get("current_step")
    checkpoint = (workspace_context or {}).get("checkpoint") or {}
    ui_context = (workspace_context or {}).get("ui_context") or {}
    artifacts = (
        (workspace_context or {}).get("artifacts")
        or {}
    )
    workspace_has_dataset = bool(
        (workspace_context or {}).get("dataset_filename")
        or artifacts.get("dataset_profile")
    )
    notebook_summaries = (
        artifacts.get("notebooks")
        or []
    )
    mentor_state = {
        "workspace_has_dataset": workspace_has_dataset,
        "dataset_filename": (workspace_context or {}).get("dataset_filename"),
        "development_sample_size": (workspace_context or {}).get("development_sample_size"),
        "notebooks": notebook_summaries,
        "current_step": current_step,
        "current_focus": checkpoint.get("current_focus"),
        "next_actions": checkpoint.get("next_actions", []),
        "active_workspace_stage": ui_context.get("active_workspace_stage"),
        "active_prepare_stage": ui_context.get("active_prepare_stage"),
        "workbench_view": ui_context.get("workbench_view"),
        "selected_notebook_id": ui_context.get("selected_notebook_id"),
        "selected_notebook_dataset_kind":
            ui_context.get(
                "selected_notebook_dataset_kind"
            ),
        "selected_workbench_column": ui_context.get("selected_workbench_column"),
        "product_context":
            (workspace_context or {}).get(
                "mentor_product_context"
            ),
        "execution_context":
            (workspace_context or {}).get(
                "mentor_execution_context"
            ),
        "has_validation_result": bool(
            artifacts.get("validation_result")
        ),
        "has_analysis_plan": bool(
            artifacts.get("analysis_plan")
        ),
        "active_processed_dataset_id":
            (workspace_context or {}).get("active_processed_dataset_id"),
    }
    mentor_state_text = json.dumps(
        mentor_state,
        ensure_ascii=False,
        indent=2,
    )

    #BU MESAJDA hangi yardım seviyesinde davranacağıni belirliyoruz.
    prompt = f"""
        Learner Profile:
        {learner_profile_text}

        Current Workspace:
        {workspace_context_text}

        Current Mentor State:
        {mentor_state_text}

        Previous Conversation:
        {conversation_history_text}

        Mentor Guideline:
        {guideline}

        Explicit Beginner Help Request:
        {explicit_beginner_help}

        Current Message:
        {current_message}
    """
    instructions = """
    Sen DataPilot'un kıdemli Data Engineering mentorusun. Oyuncak bir chatbot gibi davranma.

    Verilen Mentor Guideline'a kesinlikle uy ve yardım seviyesini aşma.
    Current Workspace bilgisini aktif çalışma bağlamı olarak kullan:
    mevcut aşama/görev, checkpoint, veri profili ve bulgular, pipeline işlemleri,
    notebooklar ve işlenmiş datasetler birbiriyle çelişmeden değerlendirilmelidir.
    Current Mentor State içindeki ACTIVE UI STATE, kullanıcının o anda ekranda gördüğü yeri anlatır.
    product_context DataPilot'ın seçilmiş capability registry bilgisidir:
    current aktif konumu, referenced ise kullanıcının mesajında açıkça sorduğu diğer
    stage'leri gösterir. UI hakkında bu kayıtlarla çelişen bir kontrol, buton,
    select seçeneği veya işlem uydurma. Her entry'nin limits alanını gerçek ürün
    sınırı kabul et. Soruyla ilgisiz stage bilgisini cevapta dökme.
    Current Workspace içindeki artifacts yalnızca bu turla ilgili backend-retrieved
    artifact'lardır; görünmeyen artifact'ları varmış gibi varsayma.
    mentor_stage_playbooks current/referenced stage için profesyonel işlem sırasını,
    evidence gate'i ve kaçınılacak hataları verir. Kullanıcıya yol çizerken bu sırayı
    koru; kanıt kapısı geçilmeden sonraki semantik karara atlama.
    execution_context seçili notebook'un güvenilir son code/output gözlemidir.
    status=error ise yeni görev vermeden önce mevcut hatayı açıkla ve yalnız o hücreyi
    düzeltmeye yardım et. status=executed olması tek başına mantıksal doğruluk kanıtı değildir.
    Bunu varsayılan bağlam olarak kullan ama kullanıcının sorusunu o sekmeye zorla kilitleme.
    Önce sorunun niyetini ayırt et:
    - mevcut ekrandaki şeyi yorumlama/review,
    - başka bir stage/sekme hakkında soru,
    - genel kavram sorusu,
    - navigasyon/sonraki adım sorusu.
    Kullanıcı başka bir stage hakkında soruyorsa ilgili workspace artifact'ını kullan ve cevapla;
    sırf aktif ekran farklı diye soruyu geri çevirme.

    current_step yalnızca aktif Workbench/data-quality öğretim akışında pedagojik sınırdır.
    Validate, Understand, Data Model, KPI, Analysis ve diğer üst aşamalarda eski current_step'e
    takılı kalma; o aşamaya ait artifacts içindeki validation/model/KPI/analysis
    kayıtlarını önceliklendir.
    workspace_has_dataset=true ise kullanıcıya veri setini yüklemesini, dosyayı açmasını veya yeniden
    eklemesini söyleme. notebooks boş değilse notebook'un zaten workspace içinde bulunduğunu bil.
    Kullanıcı "şimdi ne yapacağım?" dediğinde sadece mevcut küçük işlemi tarif et; aynı anda hem eksik
    sayısını hem örnek satırları hem de başka kontrolleri isteme. Bir tur = bir gözlem.
    Kullanıcı arayüzde nereye gideceğini bilmiyorsa mevcut notebook/workbench bağlamına göre yönlendir.
    Previous Conversation içindeki kararları ve kullanıcının açıkladığı niyeti koru.
    Ancak konuşmadaki son konu ile aktif çalışma hedefini birbirine karıştırma.
    Kullanıcının bir terimi sorması, örnek istemesi veya kısa bir kavram sorusu sorması
    çalışma planını değiştirme talebi değildir. Böyle bir yan soruyu kısa cevapla ve ardından
    aynı current_step/current_focus'a geri dön. Açıklama içinde verdiğin örneği yeni görev yapma.
    Yalnızca kullanıcı açıkça hedef/görev değiştirmek istediğini söylüyorsa veya workspace'teki
    gerçek kanıt mevcut step'in tamamlandığını gösteriyorsa çalışma yönünü değiştir.
    Kullanıcı yön değiştirirse eski planı körü körüne sürdürme.

    Bir öneri vermeden önce kullanıcının ne yaptığını ayırt et:
    inceleme/analiz kodunu transformation gibi, deneysel kodu production pipeline gibi sunma.

    Senior review davranışı:
    - Kullanıcı bir stage'i veya ekrandaki önerileri "ne oluyor?", "bunlar doğru mu?",
      "burada ne yapacağız?" diye soruyorsa sadece navigasyon verme; mevcut artifact'ları
      teknik olarak değerlendir.
    - Understand/Model Discovery aşamasında analysis_plan içindeki grain, model_discovery,
      column_intelligence, cardinality, null oranları ve role_candidates verilerini birlikte yorumla.
      Sayısal dtype gördüğün her alanı measure sanma: identifier/code, coğrafi koordinat,
      yüksek-cardinality alan, suburb/region gibi attribute veya farklı grain'de duran aggregate
      alanları semantik olarak sorgula.
    - Ayrı dimension önerirken cardinality ve analitik faydayı değerlendir; yüksek-cardinality
      descriptive alanları otomatik dimension tablosuna dönüştürme.
    - Measure önerirken gerçekten aggregation'ın anlamlı olup olmadığını sorgula.
    - Kullanıcının önüne sistemin önerisini körü körüne tekrar koyma; güçlü noktaları,
      riskli/yanlış sınıflandırmaları ve bir sonraki kararın ne olduğunu belirt.
    - Bu değerlendirmeler dataset'e özel hard-code edilmiş kolon adlarına değil,
      workspace'teki gerçek profil/analysis evidence'ına dayanmalıdır.
    Veri hakkında context'te olmayan sayı, sonuç veya bulgu uydurma.
    Belirsizlik varsa bunu açıkça söyle ve gerekiyorsa tek hedefli bir soru sor.
    Alakasız genel tavsiye verme; öneri mevcut görev ve gözlenen kanıtla doğrudan ilgili olsun.

    Junior'ın mevcut bilgi seviyesini, geçmiş learning evidence'ını ve yardım bağımlılığını dikkate al.
    Gereğinden fazla yardım etme; bir sonraki doğru adımı atmasına yetecek minimum desteği ver.
    Mümkün olduğunda junior'ın kendisinin düşünmesini, açıklamasını ve kodu kendisinin yazmasını sağla.
    Tam çözümü yalnızca yardım seviyesi bunu gerektiriyorsa göster.
    Başarısızlığı veya yardım istemeyi tek başına bilgi eksikliği kanıtı sayma.
    Skill/practice gelişimi yalnızca gerçek learning evidence üzerinden oluşmalıdır.

    Kullanıcının dili ve soru biçimi yardım ihtiyacı için güçlü sinyaldir.
    Explicit Beginner Help Request true ise bu kural diğer pedagojik tercihlerden daha önceliklidir:
    Cevapta numaralı adımlar, kontrol listesi, birden fazla işlem, nihai karar, doldurma stratejisi,
    feature engineering veya hazır kod verme. Kullanıcı açıkça kod istemedikçe kod gösterme.
    "Nasıl yapacağım?", "neye bakacağım?", "bilmiyorum" gibi temel yardım isteyen bir mesajda
    uzman seviyesinde kontrol listesi, çok adımlı çözüm veya hazır kod dökme.
    Önce bulunduğu aşamayı bir cümlede açıkla, sonra yalnızca BİR küçük sonraki adım ver.
    Gerekirse o adımın nedenini tek kısa cümleyle açıkla ve kullanıcıdan sonucu paylaşmasını iste.
    Sonuç geldikten sonra bir sonraki adıma geç. Böylece kullanıcıyla adım adım ilerle.

    GUIDE seviyesinde bile bütün çözümü tek mesajda verme:
    - en fazla bir küçük işlem veya tek bir gözlem görevi,
    - tercihen kodu doğrudan vermek yerine neyi bulacağını açıkla,
    - kullanıcı kod isterse veya gerçekten takılırsa kısa bir örnek ver.
    NUDGE ve NONE seviyelerinde giderek daha az yönlendirme yap.
    Uzun madde listeleri, aynı mesajda analiz + karar + transformation + feature engineering zinciri
    ve kullanıcı henüz inceleme aşamasındayken nihai çözüm önerileri verme.

    Explicit Beginner Help Request true ise önce Previous Conversation'daki son konunun
    yalnızca bir yan soru olup olmadığını kontrol et; yan soruysa onu yeni çalışma hedefi yapma.
    Cevap en fazla 3 kısa cümle olsun:
    (1) Current Mentor State/current_step'ten yalnızca şu anki işi sade dille söyle,
    (2) yalnızca TEK bir küçük gözlem veya kontrol görevini ver; "eksik sayısını bul VE 5 satır göster"
        gibi iki işi aynı turda birleştirme,
    (3) gerekiyorsa "bunu nasıl yapacağını bilmiyorsan söyle, birlikte yapalım" diye sor.
    Bu cevapta gelecekte yapılacak analizleri, KPI etkisini, doldurma/işaretleme kararını veya
    sonraki task step'lerini özetleme. Kullanıcı sonucu paylaşmadan ikinci adıma geçme.

    Kullanıcıya gösterilecek cevap normal durumda kısa ve odaklı olsun.
    Ancak kullanıcı mevcut stage'i yorumlamanı, teknik review yapmanı veya önerileri
    değerlendirmeni istiyorsa gerekli derinliği ver: birkaç kısa paragraf ve en fazla
    5-7 maddelik somut teknik değerlendirme kabul edilir. Gereksiz uzun ders verme.
    Cevabın profesyonel, bağlama özgü ve teknik olarak kesin olsun.
    """



# Burada parse() değil create() kullanıyoruz.
#
# parse():
# → AI'dan belirli bir Pydantic modeline uygun structured output isteriz.
# → Örn: MentorDecision(skill_name, assistance_level, reason)
# → Sonucu response.output_parsed ile alırız.
#
# create():
# → AI'dan junior'a gösterilecek normal metin cevabı isteriz.
# → Burada belirli bir Pydantic şeması yok.
# → Sonucu response.output_text ile alırız.
    runtime = get_ai_runtime(
        "mentor"
    )

    response = guarded_responses_create(
        runtime.client,
        provider=runtime.provider,
        purpose="mentor_chat_reply",
        model=runtime.model,
        input=prompt,
        instructions=instructions,
    )

    # Junior'a gösterilecek normal metin cevabı.
    return response.output_text


def get_mentor_response_from_message(
    learner_id: str,
    current_message: str,
    session_id: str | None = None,
    conversation_history: list[dict] | None = None,
    workspace_context: dict | None = None,
) -> str | None:
    """
    Adaptive mentor sisteminin ana end-to-end servis akışı.

    Message
    → skill detection
    → mentor decision
    → mentor response
    → learning evidence
    → skill state update
    """

    mentor_decision = get_mentor_decision_from_message(
        learner_id=learner_id,
        current_message=current_message,
        workspace_context=workspace_context,
    )

    # Explicit requests for beginner/step-by-step help are turn-level evidence
    # about the amount of support needed now. Historical skill success should
    # not make the mentor dump an advanced solution or under-support the learner.
    normalized_message = current_message.casefold()
    explicit_guidance_markers = (
        "adım adım", "adim adim", "anlamadım", "anlamadim",
        "bilmiyorum", "ne yapmam gerekiyor", "nasıl yapacağım",
        "nasil yapacagim", "öğretir misin", "ogretir misin",
        "step by step", "i don't understand", "i dont understand",
        "i don't know", "i dont know", "teach me",
    )
    if (
        mentor_decision is not None
        and any(marker in normalized_message for marker in explicit_guidance_markers)
        and mentor_decision.assistance_level in {"NONE", "NUDGE"}
    ):
        mentor_decision.assistance_level = "GUIDE"

    # Her mesaj learning skill ile ilgili olmak zorunda değil.
    if mentor_decision is None:
        return None

    learner_profile = database.get_learner_profile_by_id(
        learner_id
    )

    if learner_profile is None:
        raise ValueError("Learner profile bulunamadı.")

    learner_profile = dict(learner_profile)

    # Junior'a assistance level'a uygun gerçek mentor cevabını üret.
    mentor_response = generate_mentor_response(
        learner_profile=learner_profile,
        mentor_decision=mentor_decision,
        current_message=current_message,
        conversation_history=conversation_history,
        workspace_context=workspace_context,
    )

    # Junior'ın mevcut mesajı gerçek evidence içeriyorsa kaydet.
    # Sonraki mesajda mentor artık güncellenmiş state'i görecek.
    process_learning_evidence(
        learner_id=learner_id,
        mentor_decision=mentor_decision,
        current_message=current_message,
        session_id=session_id,
        conversation_history=conversation_history,
        workspace_context=workspace_context,
    )

    return mentor_response





def classify_learning_evidence(
    skill_name: str,
    current_message: str,
    conversation_history: list[dict] | None = None,
    workspace_context: dict | None = None,
) -> LearningEvidenceDecision:
    """
    Junior'ın mesajının gerçekten öğrenme evidence'ı olup olmadığını belirler.

    Önemli:
    Bir mesajın skill ile ilgili olması tek başına evidence olması anlamına gelmez.

    Örnek:
    "Dictionary nasıl yapılıyordu?"
    → soru, evidence değil

    'data = {"name": "Yasin"}'
    → gerçek uygulama denemesi, evidence olabilir
    """

    instructions = f"""
    Sen junior Data Engineer öğrenme sürecini değerlendiren bir sistemsin.

    İlgili skill:
    {skill_name}

    Kullanıcının mesajının gerçek learning evidence olup olmadığını belirle.
    Workspace context yalnızca kullanıcının önerisini/cevabını mevcut görev ve
    artifact'lara göre değerlendirmek içindir; workspace'in kendi bilgisi learner
    evidence değildir.

    - Saf yardım, navigasyon, "hangi buton?", "nereden yapacağım?" soruları
      learning evidence değildir ve misconception üretmemelidir.
    - Kullanıcı bir çözüm, kod, açıklama, karar, hipotez veya validation kriteri
      öneriyorsa bu genuine evidence olabilir; yanlışsa success=false.
    - Data Model/KPI/Analysis/Dashboard gibi stage'lerde kullanıcı yanlış bir
      semantik karar öneriyorsa uygun canonical misconception varsa onu döndür.
    - Emin olmadığın durumda misconception=null.

    Shared classifier policy:
    {learning_evidence_classifier_rules()}
    """

    conversation_history_text = json.dumps(
    conversation_history or [],
    ensure_ascii=False,
    indent=2,
    )

    workspace_evidence_context = {
        "product":
            (workspace_context or {}).get(
                "mentor_product_context"
            ),
        "stage_playbooks":
            (workspace_context or {}).get(
                "mentor_stage_playbooks"
            ),
        "execution":
            (workspace_context or {}).get(
                "mentor_execution_context"
            ),
        "artifacts":
            (workspace_context or {}).get(
                "artifacts"
            ),
    }
    workspace_evidence_text = json.dumps(
        workspace_evidence_context,
        ensure_ascii=False,
        default=str,
    )[:24000]

    evidence_input = f"""
    Previous Conversation:
    {conversation_history_text}

    Relevant Workspace Context:
    {workspace_evidence_text}

    Current Message:
    {current_message}
    """

    runtime = get_ai_runtime(
        "classifier"
    )

    response = guarded_responses_parse(
        runtime.client,
        provider=runtime.provider,
        purpose="mentor_chat_evidence",
        model=runtime.model,
        input=evidence_input,
        instructions=instructions,
        text_format=LearningEvidenceDecision,
        **classifier_generation_kwargs(),
    )

    evidence = response.output_parsed
    evidence.misconception = (
        normalize_misconception(
            success=evidence.success,
            misconception=(
                evidence.misconception
            ),
        )
    )

    # AI evidence olduğunu söylüyorsa gerekli alanların da dolu olması gerekir.
    if evidence.is_evidence:
        if evidence.evidence_type is None or evidence.success is None:
            raise ValueError("Learning evidence sonucu eksik.")

    return evidence


def refresh_skill_status(
    learner_id: str,
    skill_name: str,
) -> str:
    """
    Evidence geçmişine göre learner'ın skill status'unu günceller.

    MVP kuralları:
    0 attempt                 → new
    1-2 attempt               → learning
    3+ attempt                → practicing
    5+ attempt ve >= %80 başarı → comfortable
    """

    skill_state = database.get_skill_state(
        learner_id,
        skill_name,
    )

    if skill_state is None:
        raise ValueError("Skill state bulunamadı.")

    attempts = skill_state["attempts"]
    successful_attempts = skill_state["successful_attempts"]

    if attempts == 0:
        new_status = "new"

    elif attempts < 3:
        new_status = "learning"

    elif attempts >= 5 and successful_attempts / attempts >= 0.8:
        new_status = "comfortable"

    else:
        new_status = "practicing"

    if skill_state["status"] != new_status:
        database.update_skill_status(
            learner_id,
            skill_name,
            new_status,
        )

    return new_status


def process_learning_evidence(
    learner_id: str,
    mentor_decision: MentorDecision,
    current_message: str,
    session_id: str | None = None,
    conversation_history: list[dict] | None = None,
    workspace_context: dict | None = None,
) -> LearningEvidenceDecision:

    evidence = classify_learning_evidence(
        skill_name=mentor_decision.skill_name,
        current_message=current_message,
        conversation_history=conversation_history,
        workspace_context=workspace_context,
    )

    # Mesaj genuine learning evidence değilse
    # attempts veya skill state'e dokunmuyoruz.
    if not evidence.is_evidence:
        return evidence

    workspace_context = workspace_context or {}
    ui_context = workspace_context.get("ui_context") or {}
    checkpoint = workspace_context.get("checkpoint") or {}

    evidence_context = LearningEvidenceContext(
        workspace_id=workspace_context.get("workspace_id"),
        stage=(
            ui_context.get("active_prepare_stage")
            or ui_context.get("active_workspace_stage")
        ),
        task_type=(
            (workspace_context.get("current_step") or {}).get("step_type")
            if isinstance(workspace_context.get("current_step"), dict)
            else None
        ),
        target_type="workspace_message",
        target_name=ui_context.get("selected_workbench_column"),
        user_authored=True,
        deterministic_validation=False,
        misconception=evidence.misconception,
        metadata={
            "current_focus": checkpoint.get("current_focus"),
            "selected_notebook_id": ui_context.get("selected_notebook_id"),
            "workbench_view": ui_context.get("workbench_view"),
        },
    )

    database.record_learning_evidence(
        learner_id=learner_id,
        skill_name=mentor_decision.skill_name,
        assistance_level=mentor_decision.assistance_level,
        success=evidence.success,
        evidence_type=evidence.evidence_type,
        note=evidence.note,
        session_id=session_id,
        context=evidence_context.model_dump(
            exclude_none=True,
        ),
    )

    # record_learning_evidence attempts sayılarını güncelledi.
    # Şimdi bu yeni değerlere göre status'u güncelliyoruz.
    refresh_skill_status(
        learner_id,
        mentor_decision.skill_name,
    )

    return evidence
def get_skill_for_data_quality_issue(issue_type: str):
    return DATA_QUALITY_SKILL_MAP.get(issue_type)

def get_mentor_decision_for_data_quality_finding(# hangi skill ve hangi assitance level onu bulacak.
    learner_id: str,
    finding: DataQualityFinding,
    ):
    skill_name = get_skill_for_data_quality_issue(finding.issue_type) # mapping e bakip konunun hangi skille alakali oldugunu anlamak
    if skill_name is None:
        return None # mentor kararina devam etmesin diyoruz eger skill adi yoksa
    
    return get_mentor_decision_for_learner(
    learner_id=learner_id,
    skill_name=skill_name,
    current_message=finding.observation,
    )



# Bir DataQualityFinding'i learner'ın seviyesine uygun mentor cevabına dönüştürür.
#
# Akış:
# 1. finding.issue_type üzerinden ilgili skill bulunur.
# 2. learner'ın o skill'deki durumuna göre MentorDecision alınır.
# 3. finding içindeki observation ve suggested_action mentor mesajına eklenir.
# 4. generate_mentor_response() ile junior'a gösterilecek adaptif cevap üretilir.
#
# Eğer finding için uygun bir skill yoksa None döner.

# Bu fonksiyonun görevi finding’i alıp junior’a gösterilecek gerçek mentor cevabını üretmek olacak.
def get_mentor_response_for_data_quality_finding(
    learner_id: str,
    finding: DataQualityFinding,
    ):

    # finding - ilgili skill bulunur - learner'ın o skill seviyesi okunur - MentorDecision gelir
    mentor_decision = get_mentor_decision_for_data_quality_finding(
    learner_id=learner_id,
    finding=finding,
    )
    if mentor_decision is None:
        return None

    # gerçek mentor cevabını üretmek için learner profilini almamız gerekiyor.
    learner_profile = database.get_learner_profile_by_id(learner_id)
    learner_profile = dict(learner_profile)

    # mentora göndereceğimiz mesajı hazırlayalım. Sadece observation değil, AI’nin önerdiği aksiyonu da görsün
    finding_message = (
    f"Problem: {finding.observation}\n" # observation:  AI ne gördü? → problem ne?
    f"Suggested action: {finding.suggested_action}\n" # suggested_action: → bu problem için junior ne yapmayı değerlendirmeli?
    "Sadece bu finding içinde verilen bilgilere dayan. "
    "Veride olmayan kolon, değer veya metadata uydurma."
    )

    # finding_message artık mentorun anlayacağı metin olacak.

    return generate_mentor_response(
    learner_profile=learner_profile,
    mentor_decision=mentor_decision,
    current_message=finding_message,
    )



# Junior'ın belirli bir DataQualityFinding için yaptığı attempt'i değerlendirir.
#
# Bu fonksiyon mentor cevabı üretmez.
# Sadece şu sorulara cevap verir:
#
# - Junior gerçekten bir deneme yaptı mı?
# - Bu hangi evidence türü?
# - Deneme teknik olarak doğru / anlamlı mı?
#
# Finding yalnızca bağlamdır.
# Learning evidence olarak sadece junior'ın kendi attempt'i değerlendirilir.
def evaluate_data_quality_attempt(
    skill_name: str,
    finding: DataQualityFinding,
    attempt: str,
) -> LearningEvidenceDecision:

    finding_text = json.dumps(
        finding.model_dump(),
        ensure_ascii=False,
        indent=2,
    )

    evaluation_input = f"""
    Data Quality Finding:
    {finding_text}

    Junior Attempt:
    {attempt}
    """

    instructions = f"""
    Sen junior Data Engineer'ın belirli bir data quality problemi
    üzerindeki kendi denemesini değerlendiriyorsun.

    İlgili skill:
    {skill_name}

    ÖNEMLİ:
    Data Quality Finding ve suggested_action yalnızca bağlamdır.
    Bunları junior'ın yaptığı şey olarak değerlendirme.
    Learning evidence olarak yalnızca Junior Attempt bölümünü değerlendir.

    is_evidence=true:
    - Junior kod deniyorsa
    - Bir kontrol yöntemi öneriyorsa
    - Problemi kendi cümleleriyle analiz ediyorsa
    - Bir sonucu doğrulamaya çalışıyorsa

    is_evidence=false:
    - Sadece soru soruyorsa
    - Yardım istiyorsa
    - Hiç gerçek deneme yapmıyorsa
    - Konu dışı cevap veriyorsa

    Evidence varsa evidence_type değerini belirle:
    - application
    - explanation
    - debugging
    - validation

    success=true:
    Junior'ın attempt'i bu finding için teknik olarak doğru,
    anlamlı veya uygun bir sonraki adımsa.

    success=false:
    Attempt yanlışsa, ilgisizse veya problemi yanlış yorumluyorsa.

    Evidence değilse:
    evidence_type=null
    success=null

    note alanında kararının nedenini kısa açıkla.

    Finding içinde olmayan kolon, veri veya metadata uydurma.
    """

    runtime = get_ai_runtime(
        "classifier"
    )

    response = guarded_responses_parse(
        runtime.client,
        provider=runtime.provider,
        purpose="mentor_data_quality_evidence",
        model=runtime.model,
        input=evaluation_input,
        instructions=(
            instructions
            + "\n\nShared classifier policy:\n"
            + learning_evidence_classifier_rules()
        ),
        text_format=LearningEvidenceDecision,
        **classifier_generation_kwargs(),
    )

    evidence = response.output_parsed
    evidence.misconception = normalize_misconception(
        success=evidence.success,
        misconception=evidence.misconception,
    )

    if evidence.is_evidence:
        if evidence.evidence_type is None or evidence.success is None:
            raise ValueError("Data quality attempt evidence sonucu eksik.")

    return evidence

# Data quality mentor attempt akışının ana servis fonksiyonu.
#
# Akış:
#
# finding
# ↓
# ilgili skill bulunur
# ↓
# learner'ın assistance level'ı belirlenir
# ↓
# junior attempt'i değerlendirilir
# ↓
# gerçek evidence ise DB'ye kaydedilir
# ↓
# skill status güncellenir
# ↓
# mentor attempt'e uygun adaptif cevap üretir
#
def review_data_quality_attempt(
    learner_id: str,
    finding: DataQualityFinding,
    attempt: str,
) -> DataQualityAttemptResponse | None:

    attempt = attempt.strip()

    if attempt == "":
        raise ValueError("Attempt boş olamaz.")

    # Finding hangi öğrenme skill'i ile ilgili?
    skill_name = get_skill_for_data_quality_issue(
        finding.issue_type
    )

    if skill_name is None:
        return None

    # Learner'ın mevcut skill durumu üzerinden
    # hangi yardım seviyesinin uygun olduğunu belirle.
    mentor_decision = get_mentor_decision_for_data_quality_finding(
        learner_id=learner_id,
        finding=finding,
    )

    if mentor_decision is None:
        return None

    # Junior'ın kendi attempt'ini değerlendir.
    evidence = evaluate_data_quality_attempt(
        skill_name=skill_name,
        finding=finding,
        attempt=attempt,
    )

    # Gerçek learning evidence ise kalıcı olarak kaydet.
    if evidence.is_evidence:
        evidence_context = LearningEvidenceContext(
            stage="prepare",
            learning_phase=(
                "validate"
                if evidence.evidence_type == "validation"
                else "implement"
                if evidence.evidence_type == "application"
                else "reason"
                if evidence.evidence_type == "explanation"
                else None
            ),
            task_type=finding.issue_type,
            target_type=(
                "column"
                if finding.column
                else "dataset"
            ),
            target_name=finding.column,
            user_authored=True,
            deterministic_validation=False,
            misconception=evidence.misconception,
            metadata={
                "severity": finding.severity,
            },
        )

        database.record_learning_evidence(
            learner_id=learner_id,
            skill_name=skill_name,
            assistance_level=mentor_decision.assistance_level,
            success=evidence.success,
            evidence_type=evidence.evidence_type,
            note=evidence.note,
            session_id=None,
            context=evidence_context.model_dump(
                exclude_none=True,
            ),
        )

    # Evidence kaydedildiyse yeni attempt sayılarına göre,
    # kaydedilmediyse mevcut sayılara göre status'u belirler.
    skill_status = refresh_skill_status(
        learner_id=learner_id,
        skill_name=skill_name,
    )

    learner_profile = database.get_learner_profile_by_id(
        learner_id
    )

    if learner_profile is None:
        raise ValueError("Learner profile bulunamadı.")

    learner_profile = dict(learner_profile)

    # Mentorun junior'a vereceği cevap için gerekli context.
    review_message = (
    f"Data quality problem: {finding.observation}\n"
    f"Suggested action: {finding.suggested_action}\n"
    f"Junior attempt: {attempt}\n"
    f"Attempt success: {evidence.success}\n"
    f"Evaluation: {evidence.note}\n\n"

    "Junior'ın attempt'ine doğrudan cevap ver. "
    "Attempt success True ise ilk cümlede bunun doğru veya uygun bir adım olduğunu açıkça belirt. "
    "Attempt success False ise hatayı kısa şekilde belirt. "
    "Ardından yalnızca bir sonraki küçük adımı ver. "
    "En fazla 2 kısa cümle kullan. "
    "Birden fazla yeni kontrol, uzun liste veya tam çözüm verme. "
    "Sadece finding ve junior attempt içindeki bilgilere dayan. "
    "Veride olmayan kolon, değer veya metadata uydurma."
    )
    mentor_response = generate_data_quality_attempt_response(
    learner_profile=learner_profile,
    mentor_decision=mentor_decision,
    finding=finding,
    attempt=attempt,
    evidence=evidence,
    )

    return DataQualityAttemptResponse(
        mentor_response=mentor_response,
        skill_name=skill_name,
        skill_status=skill_status,
        evidence=evidence,
    )





def generate_data_quality_attempt_response(
    learner_profile: dict,
    mentor_decision: MentorDecision,
    finding: DataQualityFinding,
    attempt: str,
    evidence: LearningEvidenceDecision,
) -> str:

    input_data = {
        "finding": finding.model_dump(),
        "junior_attempt": attempt,
        "evaluation": evidence.model_dump(),
    }

    prompt = json.dumps(
        input_data,
        ensure_ascii=False,
        indent=2,
    )

    instructions = """
    Junior Data Engineer için yalnızca BİR sonraki küçük adımı üret.

    Kurallar:
    - Sadece verilen finding, junior_attempt ve evaluation bilgilerini kullan.
    - Junior'ın az önce yaptığı şeyi tekrar önerme.
    - Yalnızca tek bir işlem öner.
    - Kod verme.
    - Örnek kod verme.
    - Liste verme.
    - Açıklama yapma.
    - Veride olmayan bilgi uydurma.
    - Kısa, doğal bir cümle yaz.
    """

    runtime = get_ai_runtime(
        "mentor"
    )

    response = guarded_responses_parse(
        runtime.client,
        provider=runtime.provider,
        purpose="mentor_data_quality_next_step",
        model=runtime.model,
        input=prompt,
        instructions=instructions,
        text_format=DataQualityNextStep,
    )

    next_step = response.output_parsed.next_step

    # Junior'ın attempt'ine verilen ilk tepkiyi
    # AI'ya bırakmıyoruz; backend kendisi belirliyor.
    if not evidence.is_evidence:
        acknowledgement = "Bu henüz gerçek bir deneme değil."

    elif evidence.success:
        acknowledgement = "Evet, bu doğru bir adım."

    else:
        acknowledgement = "Bu adım henüz doğru değil."

    return f"{acknowledgement} {next_step}"


# Gerçek transformation validation sonucunu
# LearningEvidenceDecision formatına dönüştürür.
#
# Burada AI kullanılmaz.
# Çünkü başarı bilgisi before/after gerçek data sonucundan gelir.
def build_learning_evidence_from_validation(
    validation: (
        MissingValuesValidationResult
        | DuplicateRowsValidationResult
    ),
) -> LearningEvidenceDecision:

    # Missing-values transformation sonucu.
    if isinstance(
        validation,
        MissingValuesValidationResult,
    ):
        note = (
            f"{validation.column} kolonundaki null sayısı "
            f"{validation.before_null_count} değerinden "
            f"{validation.after_null_count} değerine değişti."
        )

    # Duplicate-rows transformation sonucu.
    elif isinstance(
        validation,
        DuplicateRowsValidationResult,
    ):
        note = (
            "Duplicate row sayısı "
            f"{validation.before_duplicate_count} değerinden "
            f"{validation.after_duplicate_count} değerine değişti."
        )

    else:
        raise ValueError(
            "Desteklenmeyen transformation validation sonucu."
        )

    return LearningEvidenceDecision(
        is_evidence=True,
        evidence_type="application",
        success=validation.success,
        note=note,
    )

# review_data_quality_transformation()
#
# Görevi:
# Junior'ın gerçek data transformation sonucunu değerlendirir.
#
# Akış:
#
# finding
# +
# before_df
# +
# after_df
# ↓
# finding'in ilgili skill'i bulunur
# ↓
# transformation gerçek data üzerinden validate edilir
# ↓
# validation sonucu LearningEvidenceDecision'a çevrilir
# ↓
# evidence DB'ye kaydedilir
# ↓
# skill status güncellenir
# ↓
# structured response döner
#
# Buradaki success kararı AI tarafından verilmez.
# Gerçek before/after data sonucundan gelir.
def review_data_quality_transformation(
    learner_id: str,
    finding: DataQualityFinding,
    before_df: pd.DataFrame,
    after_df: pd.DataFrame,
) -> DataQualityTransformationResponse | None:

    # Finding hangi skill ile ilgili?
    skill_name = get_skill_for_data_quality_issue(
        finding.issue_type
    )

    if skill_name is None:
        return None

    # Learner'ın mevcut seviyesine göre assistance level'ı alıyoruz.
    #
    # Evidence DB'ye kaydedilirken hangi assistance level altında
    # başarılı/başarısız olduğu da tutuluyor.
    mentor_decision = get_mentor_decision_for_data_quality_finding(
        learner_id=learner_id,
        finding=finding,
    )

    if mentor_decision is None:
        return None

    # Gerçek before/after DataFrame sonucunu validate et.
    validation = validate_transformation_for_finding(
        before_df=before_df,
        after_df=after_df,
        finding=finding,
    )

    # Şimdilik missing_values ve duplicate_rows
    # transformation validation destekleniyor.
    # Diğer issue type'larda validator None dönebilir.
    if validation is None:
        return None

    # Deterministic validation sonucunu learning evidence'a çevir.
    evidence = build_learning_evidence_from_validation(
        validation
    )

    # Bu artık gerçek bir uygulama sonucu olduğu için
    # learning evidence olarak DB'ye kaydediyoruz.
    evidence_context = LearningEvidenceContext(
        stage="prepare",
        learning_phase="validate",
        task_type=finding.issue_type,
        target_type=(
            "column"
            if finding.column
            else "dataset"
        ),
        target_name=finding.column,
        user_authored=True,
        deterministic_validation=True,
        metadata={
            "severity": finding.severity,
            "validation_type": type(validation).__name__,
        },
    )

    database.record_learning_evidence(
        learner_id=learner_id,
        skill_name=skill_name,
        assistance_level=mentor_decision.assistance_level,
        success=evidence.success,
        evidence_type=evidence.evidence_type,
        note=evidence.note,
        session_id=None,
        context=evidence_context.model_dump(
            exclude_none=True,
        ),
    )

    # Yeni evidence sonrası skill seviyesini tekrar hesapla.
    skill_status = refresh_skill_status(
        learner_id=learner_id,
        skill_name=skill_name,
    )

    return DataQualityTransformationResponse(
        skill_name=skill_name,
        skill_status=skill_status,
        validation=validation,
        evidence=evidence,
    )

# review_data_engineering_task_transformation()
#
# Phase 2 transformation validation + learner evidence sistemi ile
# Phase 3 multi-step task sistemini birbirine bağlar.
#
# Akış:
#
# task
# ↓
# current step
# ↓
# finding
# ↓
# transformation review
# ↓
# validation + evidence + skill update
# ↓
# success ise task sonraki step'e ilerler
def review_data_engineering_task_transformation(
    learner_id: str,
    task: DataEngineeringTask,
    before_df: pd.DataFrame,
    after_df: pd.DataFrame,
) -> DataEngineeringTaskTransformationResponse:

    # Junior'ın şu anda hangi step üzerinde olduğunu bul.
    current_step = get_current_task_step(task)

    if current_step is None:
        raise ValueError("Current task step bulunamadı.")

    # Mevcut step'in finding'i üzerinden:
    #
    # - gerçek transformation validate edilir
    # - learning evidence oluşturulur
    # - evidence DB'ye kaydedilir
    # - skill status güncellenir
    transformation_review = review_data_quality_transformation(
        learner_id=learner_id,
        finding=current_step.finding,
        before_df=before_df,
        after_df=after_df,
    )

    if transformation_review is None:
        raise ValueError(
            "Bu task step için transformation review desteklenmiyor."
        )

    # Validation başarılıysa task ilerler.
    # Başarısızsa mevcut step aktif kalır.
    updated_task = apply_validation_result_to_task(
        task=task,
        validation=transformation_review.validation,
    )
    # Task'ın güncel durumunu kalıcı olarak sakla.
    #
    # Success = True ise ilerlemiş hali,
    # Success = False ise aynı step'te kalan hali kaydedilir.
    database.save_data_engineering_task(
        learner_id=learner_id,
        task=updated_task,
    )

    return DataEngineeringTaskTransformationResponse(
        task=updated_task,
        skill_name=transformation_review.skill_name,
        skill_status=transformation_review.skill_status,
        validation=transformation_review.validation,
        evidence=transformation_review.evidence,
    )