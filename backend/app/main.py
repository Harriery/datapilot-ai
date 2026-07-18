import uuid
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from openai import (
    OpenAI,
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
)
from backend.app.prompts import SYSTEM_PROMPT
from backend.app.models import ChatRequest, ChatResponse

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

MAX_HISTORY_MESSAGES = 10

#  # BU FONK ISTEKLERIN VE CEVAPLARIN SON 10unu TUTMAK ICIN KULLANILIR
#  EGER YENI BIR ISTEK OLDUGUNDA YANI 11 OLDUGUNDA EN ESKI MESAJI SILER
#  History sınırı aşılırsa en eski mesajları siler.
def trim_history(history):                    
    while len(history) > MAX_HISTORY_MESSAGES:   #if kullansaydik sadece 1 kez silerdi.
        history.pop(0)



@app.get("/")
def home():
    return {"message": "DataPilot AI is running"}

@app.post("/sessions")      #yeni konuşma oluşturuyor.
def create_sessions():
    # Yeni ve neredeyse benzersiz bir konuşma kimliği üretir.
    session_id=str(uuid.uuid4())

     # Bu session için boş bir konuşma geçmişi oluşturur.
    conversation_history[session_id] = []

    # Frontend'in sonraki mesajlarda kullanması için session_id'yi döndürür.
    return{"session_id": session_id}


#konuşma geçmişini getiriyor.
@app.get("/sessions/{session_id}")  #Buradaki süslü parantez, URL’nin bu kısmının değişken olduğunu söyler. session_id == "yasin-1" Buna path parameter denir.
def get_session(session_id: str):
    # URL içinden gelen session_id ile ilgili konuşma geçmişini arar.
    history = conversation_history.get(session_id)

    # Session bulunamazsa 404 hatası döndürür.
    if history is None:
        raise HTTPException(
            status_code=404,
            detail="Session bulunamadı.",
        )

    # Session varsa ID ve mesaj geçmişini kullanıcıya döndürür.
    return {
        "session_id": session_id,
        "history": history,
    }

#Kullanıcı konuşmayı tamamen silmek istediğinde asagidakini kullanir.
@app.delete("/sessions/{session_id}")       #Bu endpoint, artık kullanılmayan konuşmayı bellekten kaldıracak.
def delete_session(session_id: str):
    # Session mevcut değilse 404 hatası döndürür.
    if session_id not in conversation_history:
        raise HTTPException(
            status_code=404,
            detail="Session bulunamadı.",
        )

    # Session ID'yi ve ona ait bütün mesaj geçmişini sözlükten siler.
    del conversation_history[session_id]

    # Silme işleminin başarılı olduğunu bildirir.
    return {
        "message": "Session başarıyla silindi.",
        "session_id": session_id,
    }


@app.post("/chat", response_model=ChatResponse)          #konuşmaya mesaj ekliyor.
def chat(request: ChatRequest):
    # Kullanıcının mesajını alır ve başındaki/sonundaki boşlukları temizler.
    message = request.message.strip()

    if message == "":
        return {"reply": "Bu mesaj boş olamaz"}


    # Bu session_id varsa ona ait konuşma geçmişini getirir.
    # Yoksa None döndürür.
    history = conversation_history.get(         #id sozlukte varsa onu getirir, yoksa None verir.
        request.session_id)
    
    if history is None:
        raise HTTPException(
            status_code=404,
            detail="Session bulunamadı. Önce yeni bir session oluşturun.",
    )
    
    # Kullanıcının yeni mesajını o session'ın geçmişine ekler.
    history.append(
        {
            "role": "user",
            "content": message,
        }
    )

    trim_history(history) 

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
        print(conversation_history)
        
        trim_history(history)
        return {"reply": response.output_text}
    # Hata oluşursa son eklenen user mesajı cevapsız kalır.
    # Bu nedenle HTTP hatasını göndermeden önce history'den kaldırılır.
    except AuthenticationError:
        history.pop()               ## OpenAI cevap veremezse son eklenen, cevapsız user mesajını geçmişten kaldırır.
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