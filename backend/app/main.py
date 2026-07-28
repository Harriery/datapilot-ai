from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.chat_routes import router as chat_router
from backend.app.database import init_db
from backend.app.session_routes import router as session_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(session_router)
app.include_router(chat_router)


@app.get("/")
def home():
    return {"message": "DataPilot AI çalışıyor"}
