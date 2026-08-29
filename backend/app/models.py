"""
Bu dosya, API içinde kullanılan veri modellerini içerir.

Modeller:
- API'ye hangi verilerin gönderileceğini tanımlar.
- API'den hangi verilerin döneceğini tanımlar.
- Verilerin tiplerini kontrol eder.
- Swagger dokümantasyonunun daha anlaşılır olmasını sağlar.

Örnek:
ChatRequest  -> Kullanıcıdan gelen verinin yapısı
ChatResponse -> Kullanıcıya dönen verinin yapısı
"""
from pydantic import BaseModel, Field # Pydantic = Python’da gelen/giden verinin şeklini ve tipini kontrol eden kütüphane.
from typing import Literal # Bir alanın sadece belirlediğimiz sabit değerlerden birini almasını sağlar.

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):      #/chat endpoint’inin başarılı cevabında
                                    #reply isimli string alan bulunacak.
    reply: str


class DocumentAskRequest(BaseModel):
    question: str
    top_k: int =Field(default=3, ge=1, le=10)
    session_id: str

class DocumentSearchRequest(BaseModel): # sadece dokuman icinde arama yapiyor.
    question: str
    top_k: int =Field(default=3, ge=1, le=10)   
# Field(...)
# │
# ├── default=3  → top_k gönderilmezse 3
# ├── ge=1       → greater than or equal → en az 1
# └── le=10      → less than or equal → en fazla 10

class MentorDecision(BaseModel):
    skill_name: str
    assistance_level: Literal[ # Sadece izin verilen yardım seviyeleri kabul edilir.
        "NUDGE",
        "GUIDE",
        "TEACH",
        "DEMONSTRATE",
    ]
    reason: str
# AI’nın “bu mesaj hangi skill ile ilgili?” cevabının şeklini tanımlayacağız.
# skill_name = "python_dict"
# reason = "Kullanıcı dictionary yapısını soruyor."
class SkillDetection(BaseModel):
    skill_name: str | None = None   # → string veya NoneS
    reason: str
