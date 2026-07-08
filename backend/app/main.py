from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
class ChatRequest(BaseModel):
    mesaj: str

@app.get("/")
def home():
    return {"message": "DataPilot AI is running"}


@app.post("/chat")
def chat(request: ChatRequest):
    return {"reply": f"You said: {request.mesaj}"}