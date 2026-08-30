import json
from openai import OpenAI
from backend.app.models import (
    MentorDecision,
    SkillDetection,
    LearningEvidenceDecision,
)
import backend.app.database as database
import os

from dotenv import load_dotenv
# MentorDecision bizim models.py dosyasında oluşturduğumuz Pydantic modelidir.
# AI'dan gelecek mentor kararının hangi alanlara sahip olması gerektiğini tanımlar.

load_dotenv()

# OpenAI API anahtarını ortam değişkeninden alır.
api_key = os.getenv("OPENAI_API_KEY")

# OpenAI ile iletişim kuracak istemciyi oluşturur.
client = OpenAI(api_key=api_key)


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

    # Engineering Workflow
    "testing",
    "git_workflow",
    "development_environment",
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
    
    prompt = build_mentor_decision_prompt(learner_profile, skill_state,learning_evidence, current_message)

    instructions = """
            You are an adaptive Data Engineering mentor.

            Choose the minimum assistance level needed for the learner's next correct step.

            Assistance levels:
            - NONE: learner can continue independently
            - NUDGE: learner only needs a small hint
            - GUIDE: learner needs step-by-step direction
            - TEACH: learner needs the concept explained
            - DEMONSTRATE: learner needs a concrete example

            Base your decision on the learner profile, skill state,
            learning evidence, and current message.
            """



# parse():
# AI cevabını düz metin olarak almak yerine,
# verdiğimiz Pydantic modeline göre yapılandırılmış şekilde almamızı sağlar.
#
# text_format=MentorDecision:
# "AI cevabı bizim MentorDecision modelimizin yapısına uygun olsun" demektir.
    response = client.responses.parse(  # parse cevabi (basemodeldeki) sablona gore olusturdemek.
    model="gpt-5-mini",
    input=prompt,               # → AI NEYE BAKARAK karar versin?
    instructions=instructions,  # → AI NASIL karar versin?
    text_format=MentorDecision, # AI KARARI HANGİ ŞEKİLDE versin? model.py deki olusturdugumuz model
)
    return response.output_parsed   # MentorDecision modeline dönüştürülmüş asıl sonuç


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


def detect_relevant_skill(current_message:str):


    skills_text = ", ".join(SKILL_CATALOG)# skill katologiunu metne cevirdik ai in okumasi icin.

    instructions = f"""
        Kullanıcının mesajına en uygun skill'i seç.

        Sadece aşağıdaki skill'lerden birini seç:
        {skills_text}

        Eğer listedeki hiçbir skill mesajla gerçekten ilgili değilse:
        skill_name = null döndür.

        Yeni bir skill adı üretme.
        Neden bu kararı verdiğini kısa şekilde açıkla.
    """
    response = client.responses.parse(  # OpenAI cevabı için modeli kullanmasını parse() ile biz söyleriz.
        model="gpt-5-mini",
        input= current_message,
        instructions= instructions,            
        text_format=SkillDetection,
    )

    detection = response.output_parsed# modele gore olusturulmus sonuc (SkillDetection)
    if detection.skill_name is not None and detection.skill_name not in SKILL_CATALOG:
        raise ValueError("Geçersiz skill tespit edildi.")
    
    return detection

def get_mentor_decision_from_message(
    learner_id: str,
    current_message: str,
    ):

    # Burada SkillDetection nesnesini aldık.
    # skill_name değerine skill_detection.skill_name ile ulaşırız.
    skill_detection = detect_relevant_skill(current_message)
    if skill_detection.skill_name is None:
        return None
    decision = get_mentor_decision_for_learner(
        learner_id,
        skill_detection.skill_name,
        current_message,
        )
    return decision

ASSISTANCE_GUIDELINES = {
    "NONE": "Junior görevi büyük ölçüde bağımsız yapabiliyor. Gereksiz öğretme yok; kısa cevap/review yeterli.",
    "NUDGE": "Çok küçük bir ipucu ver. Çözümü veya kodu söyleme. Junior'ın sonraki adımı kendisinin bulmasını sağla.",
    "GUIDE":" Problemi küçük adımlara böl. Sorular ve yönlendirmelerle ilerlet.Tam çözümü hemen verme.",
    "TEACH": "Kavramı önce açıkla.Neden kullanıldığını ve küçük bir örneği göster.Sonra junior'ın uygulamasını iste.",
    "DEMONSTRATE":"Junior ciddi şekilde takılmışsa çalışan bir örnek göster. Ama örneğin ne yaptığını da açıkla.Sonrasında benzer kısmı junior'ın yapmasını sağla."
}

def generate_mentor_response(
    learner_profile: dict,
    mentor_decision: MentorDecision,  # AI'nin MentorDecision modeline göre ürettiği karar
    current_message: str,
):
    # mentor_decision bir Pydantic modelidir.
    # .assistance_level ile örn. "GUIDE" değerini alıyoruz.
    #
    # ASSISTANCE_GUIDELINES ise bir dict'tir.
    # Bu "GUIDE" değerini dict içinde key olarak kullanıp
    # o seviyeye ait mentor davranış kuralını alıyoruz.
    guideline = ASSISTANCE_GUIDELINES[
        mentor_decision.assistance_level
       
    ]
    # learner_profile bir dict.
    # AI prompt'una ekleyebilmek için JSON metnine çeviriyoruz.
    learner_profile_text = json.dumps(
        learner_profile,
        ensure_ascii=False,
        indent=2,
    )   

    #BU MESAJDA hangi yardım seviyesinde davranacağıni belirliyoruz.
    prompt = f"""
         Learner Profile:
            {learner_profile_text}
    
            Mentor Guideline:
            {guideline}

            Current Message:
            {current_message}
    """
    instructions = """
    Sen junior Data Engineer'lar için adaptif bir mentorsun.

    Verilen Mentor Guideline'a kesinlikle uy.
    Junior'ın mevcut bilgi seviyesini ve öğrenme tercihlerini dikkate al.
    Gereğinden fazla yardım etme; bir sonraki doğru adımı atmasına yetecek minimum desteği ver.
    Mümkün olduğunda junior'ın kendisinin düşünmesini ve kodu kendisinin yazmasını sağla.
    Tam çözümü yalnızca yardım seviyesi bunu gerektiriyorsa göster.
    Cevabını açık, kısa ve öğretici tut.
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
    response = client.responses.create(
     model="gpt-5-mini",
     input=prompt,              
     instructions=instructions, 
    )

    # Junior'a gösterilecek normal metin cevabı.
    return response.output_text


def get_mentor_response_from_message(
    learner_id: str,
    current_message: str,
    session_id: str | None = None,
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
    )

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
    )

    # Junior'ın mevcut mesajı gerçek evidence içeriyorsa kaydet.
    # Sonraki mesajda mentor artık güncellenmiş state'i görecek.
    process_learning_evidence(
        learner_id=learner_id,
        mentor_decision=mentor_decision,
        current_message=current_message,
        session_id=session_id,
    )

    return mentor_response





def classify_learning_evidence(
    skill_name: str,
    current_message: str,
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

    Learning evidence sayılabilecek durumlar:
    - application: junior bir çözüm veya kod deniyor
    - explanation: junior bir kavramı kendi cümleleriyle açıklıyor
    - debugging: junior bir hatayı analiz edip çözmeye çalışıyor
    - validation: junior sonucunu kontrol ediyor veya doğruluyor

    Sadece soru sormak, yardım istemek, proje navigasyonu,
    hatırlatma istemek veya genel konuşma learning evidence değildir.

    Evidence değilse:
    is_evidence=false
    evidence_type=null
    success=null

    Evidence ise:
    evidence_type belirle
    success değerini belirle
    note alanında kısa neden yaz.
    """

    response = client.responses.parse(
        model="gpt-5-mini",
        input=current_message,
        instructions=instructions,
        text_format=LearningEvidenceDecision,
    )

    evidence = response.output_parsed

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
) -> LearningEvidenceDecision:

    evidence = classify_learning_evidence(
        skill_name=mentor_decision.skill_name,
        current_message=current_message,
    )

    # Mesaj genuine learning evidence değilse
    # attempts veya skill state'e dokunmuyoruz.
    if not evidence.is_evidence:
        return evidence

    database.record_learning_evidence(
        learner_id=learner_id,
        skill_name=mentor_decision.skill_name,
        assistance_level=mentor_decision.assistance_level,
        success=evidence.success,
        evidence_type=evidence.evidence_type,
        note=evidence.note,
        session_id=session_id,
    )

    # record_learning_evidence attempts sayılarını güncelledi.
    # Şimdi bu yeni değerlere göre status'u güncelliyoruz.
    refresh_skill_status(
        learner_id,
        mentor_decision.skill_name,
    )

    return evidence