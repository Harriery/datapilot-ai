import json

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)
# client
# = bizim OpenAI servisiyle konuşmamızı sağlayan bağlantı nesnesi


# ----*--SADECE MEYIN HAZIRLAR AI ICIN---*-
# profile_text sadece veri profilinin metin halidir.
#
# prompt ise:
# AI'ya verilen talimat
# +
# profile_text
#
# f-string içindeki {profile_text}
# yerine gerçek profiling verisi yerleştirilir.
def build_recommendation_prompt(profile: dict) -> str:
    profile_text = json.dumps(  # dumps ile metine donusuyor, ve bunu ai metin olarak gorup okuyabiliyor. 
        profile,
        ensure_ascii=False, # turkce karakterler varsa onlarin okunabilmesini sagliyor.
        indent=2,
    )

    prompt = f"""
    Sen bir Data Engineering asistanısın.

    Aşağıdaki veri profilini incele:

    {profile_text}
    """

    return prompt


def generate_data_recommendations(profile: dict) -> str:
    prompt = build_recommendation_prompt(profile)


    response = client.responses.create( # "OpenAI'ya yeni bir istek gönder ve cevap üret."
    model="gpt-5-mini",
    instructions=(
        "Sen bir Data Engineering mentorusun. "
        "Yalnızca verilen veri profilindeki bilgilere dayan. "
        "Gözlem ile öneriyi birbirinden ayır. "
        "Domain bilgisi olmadan kesin varsayımlar yapma. "
        "Şüpheli değerleri otomatik olarak hatalı kabul etme; doğrulanması gerektiğini belirt. "
        "Veriyi otomatik değiştirme, yalnızca öneri üret. "
        "En önemli en fazla 5 veri kalitesi problemini ve bunlara yönelik kısa önerileri ver. "
        "Kod örneği üretme."
        "Her problem için gözlem ve öneriyi en fazla 2-3 cümleyle açıkla. "
        "Hiçbir durumda veriye otomatik müdahale etmeyi önerdiğini söyleme; "
        "yalnızca kullanıcı tarafından değerlendirilebilecek öneriler sun."
    ),
    input=prompt,
    )   
# OpenAI cevabı sadece düz metin değildir;
# response nesnesi içinde farklı bilgiler bulunabilir.
#
# response.output_text
# → modelin ürettiği gerçek metni alır.
#
# Bu metni recommendations değişkenine koyup
# fonksiyonun dışına döndürüyoruz.
    recommendations = response.output_text

    return recommendations