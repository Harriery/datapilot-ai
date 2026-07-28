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
from backend.app.database import (
    delete_last_message,
    get_messages_by_session,
    get_session_by_id,
    insert_message,
)


router = APIRouter()
MAX_HISTORY_MESSAGES = 10 

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    # Kullanıcının mesajındaki baştaki ve sondaki boşlukları temizler.
    message = request.message.strip()

    if message == "":
        raise HTTPException(
            status_code=400,
            detail="Mesaj boş olamaz.",
        )

    # Session veritabanında var mı kontrol eder.
    session = get_session_by_id(request.session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session bulunamadı. Önce yeni bir session oluşturun.",
        )

    # Kullanıcı mesajını SQLite veritabanına kaydeder.
    insert_message(
        session_id=request.session_id,
        role="user",
        content=message,
    )

    # Session'a ait mesajları veritabanından getirir.
    history = get_messages_by_session(request.session_id)

    # OpenAI'ye yalnızca son 10 mesajı gönderir.
    history = history[-MAX_HISTORY_MESSAGES:]

    try:
        response = client.responses.create(
            model="gpt-5-mini",
            instructions=SYSTEM_PROMPT,
            input=history,
        )

    # OpenAI cevap veremezse son eklenen user mesajını veritabanından siler.
    except AuthenticationError:
        delete_last_message(request.session_id)
        raise HTTPException(
            status_code=401,
            detail="OpenAI API anahtarı geçersiz.",
        )

    except RateLimitError:
        delete_last_message(request.session_id)
        raise HTTPException(
            status_code=429,
            detail="AI kullanım limiti veya bakiyesi yetersiz.",
        )

    except APIConnectionError:
        delete_last_message(request.session_id)
        raise HTTPException(
            status_code=503,
            detail="AI servisine şu anda ulaşılamıyor.",
        )

    except Exception:
        delete_last_message(request.session_id)
        raise HTTPException(
            status_code=500,
            detail="Beklenmeyen bir sunucu hatası oluştu.",
        )

    # Başarılı AI cevabını SQLite veritabanına kaydeder.
    insert_message(
        session_id=request.session_id,
        role="assistant",
        content=response.output_text,
    )

    return {
        "reply": response.output_text,
    }