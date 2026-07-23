"""
Bu dosya session ile ilgili API endpoint'lerini içerir.

- Yeni session oluşturur.
- Session geçmişini getirir.
- Session'ı siler.
"""

import uuid

from fastapi import APIRouter, HTTPException

from backend.app.session_store import conversation_history


router = APIRouter() ## Session endpoint'lerini gruplar.


@router.post("/sessions")   #Yeni session oluştur.
def create_session():
    session_id = str(uuid.uuid4())

    conversation_history[session_id] = []   # Yeni session icin yeni bir id ile conversation_history olusuyor.

    return {
        "session_id": session_id,
    }


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    history = conversation_history.get(session_id)

    if history is None:
        raise HTTPException(
            status_code=404,
            detail="Session bulunamadı.",
        )

    return {
        "session_id": session_id,
        "history": history,
    }


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    if session_id not in conversation_history:
        raise HTTPException(
            status_code=404,
            detail="Session bulunamadı.",
        )

    del conversation_history[session_id]

    return {
        "message": "Session başarıyla silindi.",
        "session_id": session_id,
    }