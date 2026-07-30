"""
Bu dosya metin embedding işlemlerini yönetir.

Embedding:
Metnin anlamını sayılardan oluşan bir vektöre çevirir.
Bu vektörler, benzer anlamdaki metinleri bulmak için kullanılır.
Bu dosya bir endpoint degildir.
"""
# Python’un işletim sistemi ve environment variable’larla çalışmasını sağlar.
import os

from dotenv import load_dotenv
from openai import OpenAI

# .env dosyasındaki değişkenleri Python'a yükler ve python un okuyabilmesini saglar.
load_dotenv()

# .env içindeki OPENAI_API_KEY değerini alır.
api_key = os.getenv("OPENAI_API_KEY")

# OpenAI servisiyle konuşacak istemciyi/nesneyi oluşturur.
client = OpenAI(api_key=api_key)


# Tek bir metni embedding vektörüne dönüştürür.
def create_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )

    # API cevabındaki ilk ve tek embedding vektörünü döndürür.
    return response.data[0].embedding


# Birden fazla metni embedding vektörlerine dönüştürür.
def create_embeddings(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )

    # Her metne ait embedding vektörünü liste olarak döndürür.
    return [
        item.embedding
        for item in response.data
    ]                 
             
                                        