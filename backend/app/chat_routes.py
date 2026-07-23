"""
Bu dosya AI sohbetiyle ilgili API endpoint'lerini içerir.

- Kullanıcı mesajını alır.
- İlgili session'ın konuşma geçmişini bulur.
- Mesajı OpenAI'ye gönderir.
- AI cevabını konuşma geçmişine ekler.
- OpenAI hatalarını uygun HTTP hatalarına dönüştürür.
"""
import os
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from openai import (
    OpenAI,
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
)
from backend.app.models import ChatRequest, ChatResponse
from backend.app.prompts import SYSTEM_PROMPT
from backend.app.session_store import conversation_history, trim_history


router = APIRouter()

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    # Kullanıcının mesajını alır ve başındaki/sonundaki boşlukları temizler.
    message = request.message.strip()

    if message == "":
       raise HTTPException(
           status_code=400,
           detail="Mesaj boş olamaz.",
       )

    # Session ID varsa ona ait konuşma geçmişini getirir.
    # Yoksa None döndürür.
    history = conversation_history.get(request.session_id)

    if history is None:
        raise HTTPException(
            status_code=404,
            detail="Session bulunamadı. Önce yeni bir session oluşturun.",
        )

    # Kullanıcının yeni mesajını session geçmişine ekler.
    history.append(
        {
            "role": "user",
            "content": message,
        }
    )

    # Geçmiş belirlenen sınırı aşmışsa eski mesajları siler.
    trim_history(history)

    try:
        # Bu session'a ait konuşma geçmişini OpenAI'ye gönderir.
        response = client.responses.create(
            model="gpt-5-mini",
            instructions=SYSTEM_PROMPT,
            input=history,
        )

        # OpenAI cevabını aynı session'ın geçmişine ekler.
        history.append(
            {
                "role": "assistant",
                "content": response.output_text,
            }
        )

        trim_history(history)

        

        return {
            "reply": response.output_text,
        }

    # OpenAI cevap veremezse son eklenen cevapsız user mesajını kaldırır.
    except AuthenticationError:
        history.pop()
        raise HTTPException(
            status_code=401,
            detail="OpenAI API anahtarı geçersiz.",
        )

    except RateLimitError:
        history.pop()
        raise HTTPException(
            status_code=429,
            detail="AI kullanım limiti veya bakiyesi yetersiz.",
        )

    except APIConnectionError:
        history.pop()
        raise HTTPException(
            status_code=503,
            detail="AI servisine şu anda ulaşılamıyor.",
        )

    except Exception:
        history.pop()
        raise HTTPException(
            status_code=500,
            detail="Beklenmeyen bir sunucu hatası oluştu.",
        )