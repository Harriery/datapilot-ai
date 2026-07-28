"""
Bu dosya session ile ilgili API endpoint'lerini içerir.

- Yeni session oluşturur.
- Session geçmişini getirir.
- Session'ı siler.
"""

import uuid

from fastapi import APIRouter, HTTPException

from backend.app.database import (
    delete_session_by_id,
    get_messages_by_session,
    get_session_by_id,
    insert_session,
)


router = APIRouter()  # Session endpoint'lerini gruplar.


@router.post("/sessions")  # Yeni session oluşturur.
def create_session():
    # Her session için benzersiz bir ID oluşturur.
    session_id = str(uuid.uuid4())

    # Yeni session'ı SQLite veritabanındaki sessions tablosuna kaydeder.
    insert_session(session_id)

    return {
        "session_id": session_id,
    }


@router.get("/sessions/{session_id}")  # Session ve mesaj geçmişini getirir.
def get_session(session_id: str):
    # Verilen session_id veritabanında var mı kontrol eder.
    session = get_session_by_id(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session bulunamadı.",
        )

    # Session'a ait bütün mesajları veritabanından getirir.
    history = get_messages_by_session(session_id)

    return {
        "session_id": session_id,
        "history": history,
    }


@router.delete("/sessions/{session_id}")  # Session'ı siler.
def delete_session(session_id: str):
    # Session'ı veritabanından siler.
    # Sonuç 1 ise silindi, 0 ise session bulunamadı.
    deleted_count = delete_session_by_id(session_id)

    if deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Session bulunamadı.",
        )

    return {
        "message": "Session başarıyla silindi.",
        "session_id": session_id,
    }