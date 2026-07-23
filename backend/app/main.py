from fastapi import FastAPI

from backend.app.session_routes import router as session_router
from backend.app.chat_routes import router as chat_router

app = FastAPI() # bir uygulama oluşturur.

app.include_router(session_router) 
app.include_router(chat_router)

@app.get("/")
def home():
    return {
        "message": "DataPilot AI is running",
    }

