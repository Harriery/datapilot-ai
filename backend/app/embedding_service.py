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


# Bir metni embedding vektörüne dönüştürür.
def create_embeddings(text: list[str]) -> list[list[float]]:         #text: str → dışarıdan metin alır,  list[float] → ondalıklı sayılardan oluşan liste döndürür
     # Metni OpenAI embedding modeline gönderir.
    response = client.embeddings.create(            # embedding oluşturma isteği gönderir
        model="text-embedding-3-small",
        input=text,
    )
    #print(response)
    #print(response.data)
    return[
          item.embedding                # tek bir chunk’ın sayı listesi
          for item in response.data     # embedding sonuclarini bize data adinda bir nesne de dondurdugu icin biz bunu kullandik
                                        # API cevabındaki ilk embedding vektörünü alır.
    ]                       
             
                                        