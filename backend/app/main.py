import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import (
    OpenAI,
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
)
from backend.app.prompts import SYSTEM_PROMPT

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
app = FastAPI()
client = OpenAI(api_key=api_key)
conversation_history = {}               #Her session_id, kendi konuşma listesini gösterecek.
                                        #{
                                        #    "session-1": [...],
                                        #    "session-2": [...],
                                        #} seklinde gorunecek
                                        #bütün kullanıcıların konuşmalarını tutan büyük dolap: {
                                        #{
                                        #     "yasin-1": [...],
                                        #    "ayse-1": [...],
                                        #}



class ChatRequest(BaseModel):
    session_id: str
    message: str

@app.get("/")
def home():
    return {"message": "DataPilot AI is running"}


@app.post("/chat")
def chat(request: ChatRequest):
    # Kullanıcının mesajını alır ve başındaki/sonundaki boşlukları temizler.
    message = request.message.strip()

    if message == "":
        return {"reply": "Bu mesaj boş olamaz"}

    # Bu session_id daha önce varsa onun konuşma listesini getirir.
    # Yoksa yeni bir boş liste oluşturup sözlüğe ekler.
    history = conversation_history.setdefault(
        request.session_id,
        [],
    )

    # Kullanıcının yeni mesajını o session'ın geçmişine ekler.
    history.append(
        {
            "role": "user",
            "content": message,
        }
    )

    try:
        # Bu session'a ait tüm konuşma geçmişini OpenAI'ye gönderir.
        response = client.responses.create(
            model="gpt-5-mini",
            instructions=SYSTEM_PROMPT,
            input=history,
        )

        # OpenAI'nin cevabını aynı session'ın geçmişine ekler.
        history.append(
            {
                "role": "assistant",
                "content": response.output_text,
            }
        )

        return {"reply": response.output_text}

    except AuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="OpenAI API anahtarı geçersiz.",
        )

    except RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="AI kullanım limiti veya bakiyesi yetersiz.",
        )

    except APIConnectionError:
        raise HTTPException(
            status_code=503,
            detail="AI servisine şu anda ulaşılamıyor.",
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Beklenmeyen bir sunucu hatası oluştu.",
        )