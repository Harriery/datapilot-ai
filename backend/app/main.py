from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.chat_routes import router as chat_router
from backend.app.database import init_db
from backend.app.session_routes import router as session_router
from backend.app.document_routes import router as document_router
from backend.app.data_routes import router as data_router
from backend.app.mentor_routes import router as mentor_router
from backend.app.workspace_routes import (
    router as workspace_router,
)



# Server başlar
# ↓
# init_db()
# ↓
# Veritabanı ve tablolar hazır mı kontrol edilir
# ↓
# FastAPI çalışmaya başlar


# FastAPI uygulamasının başlangıç ve kapanış işlemlerini yönetir.
# Uygulama başlarken veritabanını hazırlar,
# kapanış işlemlerini de yönetebilir.
# FastAPI'nin yaşam döngüsü sistemi async context manager beklediği için async kullanılır.
@asynccontextmanager
async def lifespan(app: FastAPI):
     # yield'dan önceki bölüm, server başlarken bir kez çalışır.
    init_db()
    # Başlangıç işlemleri tamamlandı.
    # Kontrolü FastAPI'ye verir ve uygulama istek almaya başlar.
    yield
     # Buraya kod yazarsak server kapanırken çalışır.

# FastAPI uygulamasını oluşturur ve lifespan fonksiyonunu bağlar.
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session_router)
app.include_router(chat_router)
app.include_router(document_router)
app.include_router(data_router)
app.include_router(mentor_router)
app.include_router(workspace_router)

@app.get("/")
def home():
    return {"message": "DataPilot AI çalışıyor"}
