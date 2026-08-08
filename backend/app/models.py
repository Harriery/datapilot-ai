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
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):      #/chat endpoint’inin başarılı cevabında
                                    #reply isimli string alan bulunacak.
    reply: str


class DocumentSearchRequest(BaseModel):
    question: str
    top_k: int =Field(default=3, ge=1, le=10)   
# Field(...)
# │
# ├── default=3  → top_k gönderilmezse 3
# ├── ge=1       → greater than or equal → en az 1
# └── le=10      → less than or equal → en fazla 10