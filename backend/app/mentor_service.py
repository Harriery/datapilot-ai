import json
from openai import OpenAI
from backend.app.models import MentorDecision, SkillDetection
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
   
    skill_state = database.get_skill_state(learner_id, skill_name,)
    if skill_state is None:
        raise ValueError("Skill state bulunamadı.")
    
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


    skills_text = ", ".join(SKILL_CATALOG)

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
        instructions= instructions             
        text_format=SkillDetection
    )

    if detection.skill_name is not None and detection.skill_name not in SKILL_CATALOG:
        raise ValueError("Geçersiz skill tespit edildi.")
    detection = response.output_parsed
    return detection