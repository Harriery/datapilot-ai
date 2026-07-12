import os
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
app = FastAPI()
client = OpenAI(api_key=api_key)
class ChatRequest(BaseModel):
    message: str

@app.get("/")
def home():
    return {"message": "DataPilot AI is running"}


@app.post("/chat")
def chat(request: ChatRequest):         #request, kullanıcının gönderdiği JSON verisinin
                                        #FastAPI tarafından ChatRequest modeline çevrilmiş halidir.
                                        #request değişken adını biz verdik.
                                        #ChatRequest ise verinin hangi yapıda olması gerektiğini belirtir.
    message = request.message.strip()   # request.message yazınca kullanıcının body içinde gönderdiği message değerine ulaşıyoruz.
                                        #def chat(data: ChatRequest):
                                        #message = data.message
                                        #Yani request özel bir Python kelimesi değil; anlamlı olduğu için seçtiğimiz parametre adı.
    if message == "":
        return {"reply": "Bu mesaj boş olamaz"}
                                        # response = OpenAI’den dönen cevabın tamamını tutar.
    response = client.responses.create( #OpenAI client üzerinden yeni bir cevap üretme isteği gönder.
        model="gpt-5-mini",             #hangi modelin cevap üreteceğini seçer.
        input=message,                  #kullanıcının yazdığı mesajı OpenAI’ye gönderir.
    )

    return {"reply": response.output_text}  #response.output_text == o cevabın içindeki metni alır.
                                            # response bize sadece cevap gondermiyor, id, model, create_at, usage, output,output_text 
                                            # ama bize sadece output_text lazim