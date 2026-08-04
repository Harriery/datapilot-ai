import os

from dotenv import load_dotenv
from openai import OpenAI

# .env dosyasındaki değişkenleri uygulamaya yükler.
load_dotenv()

# OpenAI API anahtarını ortam değişkeninden alır.
api_key = os.getenv("OPENAI_API_KEY")

# OpenAI ile iletişim kuracak istemciyi oluşturur.
client = OpenAI(api_key=api_key)


# En ilgili chunk metinlerini tek bir bağlam metninde birleştirir.
def build_context(
    relevant_chunks: list[dict],  # Retrieval sonucunda seçilen chunk'lar
) -> str:

    # Chunk metinlerini burada toplayacağız.
    context_parts = []

    # Her ilgili chunk'ın yalnızca metin kısmını alır.
    for chunk in relevant_chunks:
        content = chunk["content"]

        # Metni context_parts listesine ekler.
        context_parts.append(content)

    # Chunk metinlerini aralarında boş satır olacak şekilde birleştirir.
    context = "\n\n".join(context_parts)

    # Oluşturulan bağlam metnini geri döndürür.
    return context

# Kullanıcının sorusuna, verilen belge bağlamına dayanarak cevap üretir.
def generate_answer(
    question: str,  # Kullanıcının sorusu
    context: str,   # İlgili chunk metinlerinin birleşmiş hâli
) -> str:

    # Belge bağlamı ile kullanıcı sorusunu OpenAI'ye gönderilecek
    # tek bir metin içinde birleştirir.
    input_text = f"""
        Belge bağlamı:
        {context}

        Kullanıcının sorusu:
        {question}
    """

    # Hazırlanan bağlamı ve soruyu OpenAI'ye gönderir.
    response = client.responses.create(
        model="gpt-5-mini",

        # Modelin yalnızca belge bağlamına dayanmasını ister.
        instructions=(
            "Yalnızca verilen belge bağlamına dayanarak cevap ver. "
            "Cevap bağlamda yoksa bunu açıkça belirt."
        ),

        # Bir önceki adımda hazırladığımız context + question metni.
        input=input_text,
    )

    return response.output_text