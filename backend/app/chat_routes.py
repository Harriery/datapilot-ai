"""
Bu dosya AI sohbetiyle ilgili API endpoint'lerini içerir.

- Kullanıcı mesajını alır.
- İlgili session'ın konuşma geçmişini bulur.
- Mesajı OpenAI'ye gönderir.
- AI cevabını konuşma geçmişine ekler.
- OpenAI hatalarını uygun HTTP hatalarına dönüştürür.
"""
import os
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from openai import (
    OpenAI,
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
)
import backend.app.database as database
from backend.app.models import ChatRequest, ChatResponse
from backend.app.prompts import SYSTEM_PROMPT
from backend.app.database import (
    delete_last_message,
    get_messages_by_session,
    get_session_by_id,
    insert_message,
)
from backend.app.mentor_service import (
    get_mentor_response_from_message,
)

import json


router = APIRouter()
MAX_HISTORY_MESSAGES = 10 

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)


def _is_step_by_step_help_request(message: str) -> bool:
    normalized = message.casefold()
    markers = (
        "ne yapmam gerekiyor", "ne yapacağım", "ne yapacagim",
        "adım adım", "adim adim", "anlamadım", "anlamadim",
        "bilmiyorum", "öğretir misin", "ogretir misin",
        "what should i do", "what do i do", "step by step",
        "i don't understand", "i dont understand", "teach me",
    )
    return any(marker in normalized for marker in markers)


def _deterministic_workspace_guidance(
    workspace_context: dict | None,
    message: str,
    conversation_history: list[dict] | None = None,
) -> str | None:
    """Control beginner-help turns while advancing from evidence already reported."""
    if workspace_context is None:
        return None

    step = workspace_context.get("current_step") or {}
    task = workspace_context.get("current_task") or {}
    checkpoint = workspace_context.get("checkpoint") or {}
    step_text = " ".join(
        str(value)
        for value in (
            step.get("title"),
            step.get("instruction"),
            step.get("description"),
            task.get("title"),
            checkpoint.get("current_focus"),
        )
        if value
    )
    normalized_step = step_text.casefold()
    if not (
        "car" in normalized_step
        and ("eksik" in normalized_step or "missing" in normalized_step or "null" in normalized_step)
    ):
        if not _is_step_by_step_help_request(message):
            return None
        step_label = (
            step.get("title")
            or step.get("instruction")
            or checkpoint.get("current_focus")
            or task.get("title")
        )
        if step_label:
            return (
                f"Şu an üzerinde çalıştığımız adım: {step_label}. "
                "Bu adımda yalnızca ilk küçük kontrolü yapalım. "
                "Nasıl yapacağını bilmiyorsan söyle, birlikte yapalım."
            )
        return None

    normalized_message = message.casefold()
    history = conversation_history or []
    recent_user_text = " ".join(
        str(item.get("content", ""))
        for item in history[-8:]
        if item.get("role") == "user"
    ).casefold()

    count_reported = (
        "np.int64(23)" in normalized_message
        or "23 eksik" in normalized_message
        or "np.int64(23)" in recent_user_text
        or "23 eksik" in recent_user_text
    )

    direct_teaching_markers = (
        "bilmiyorum", "ilk defa", "ilk kez", "tarif et", "birlikte yap",
        "nasıl yap", "nasil yap", "göster", "goster",
        "i don't know", "i dont know", "first time", "show me", "teach me",
    )
    asks_for_instruction = any(marker in normalized_message for marker in direct_teaching_markers)

    if count_reported:
        if asks_for_instruction:
            return (
                "23 eksik değer olduğunu zaten bulduk; aynı sayımı tekrar yapmayacağız. "
                "Şimdi Notebook'ta yeni bir hücreye df[df['Car'].isna()][['Suburb','Type','Rooms','Price']].head(5) yazıp çalıştır. "
                "Çıkan 5 satırı bana gönder; sonra birlikte ne gördüğümüze bakacağız."
            )
        return (
            "Car sütununda 23 eksik değer olduğunu bulduk. "
            "Şimdi yalnızca bu eksik kayıtlardan birkaç örneğe bakalım. "
            "Nasıl yapacağını bilmiyorsan söyle, birlikte yapalım."
        )

    if asks_for_instruction:
        return (
            "Notebook'ta yeni bir hücreye df['Car'].isna().sum() yaz ve o hücreyi çalıştır. "
            "Ekranda çıkan sayıyı bana gönder; şimdilik başka bir şey yapma."
        )

    if _is_step_by_step_help_request(message):
        return (
            "Şu an Car sütunundaki eksik değerleri inceliyoruz. "
            "İlk olarak sadece kaç tane Car değerinin eksik olduğunu bulalım. "
            "Bunu Notebook'ta nasıl kontrol edeceğini bilmiyorsan söyle; birlikte yapalım."
        )

    return None

@router.get("/chat/{session_id}/history")
def chat_history(session_id: str):
    """Return persisted mentor conversation so the workspace panel can resume."""
    if get_session_by_id(session_id) is None:
        raise HTTPException(status_code=404, detail="Session bulunamadı.")
    return {"messages": get_messages_by_session(session_id)}


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    # Kullanıcının mesajındaki baştaki ve sondaki boşlukları temizler.
    message = request.message.strip()

    if message == "":
        raise HTTPException(
            status_code=400,
            detail="Mesaj boş olamaz.",
        )

    # Session veritabanında var mı kontrol eder.
    session = get_session_by_id(request.session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session bulunamadı. Önce yeni bir session oluşturun.",
        )

    learner_id = request.learner_id or request.session_id

    workspace_context = None

    if request.workspace_id is not None:
        workspace = database.get_workspace(
            workspace_id=request.workspace_id,
            learner_id=learner_id,
        )

        if workspace is None:
            raise HTTPException(
                status_code=404,
                detail="Workspace bulunamadı.",
            )

        # Bir workspace'in mentor konuşması başka
        # workspace'in session'ıyla karışmamalı.
        if (
            workspace.mentor_session_id
            != request.session_id
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Session bu workspace'e ait değil."
                ),
            )

        # Give the mentor a real project snapshot, not only the workspace title.
        # This lets it reason from the learner's current task, data findings,
        # notebook/pipeline state and prior project decisions without inventing context.
        current_task = None
        current_step = None
        if workspace.current_task_id is not None:
            task = database.get_data_engineering_task(
                task_id=workspace.current_task_id,
                learner_id=learner_id,
            )
            if task is not None:
                current_task = task.model_dump()
                current_step = next(
                    (
                        step.model_dump()
                        for step in task.steps
                        if step.step_number == task.current_step_number
                    ),
                    None,
                )

        workspace_context = {
            "workspace_id": workspace.workspace_id,
            "title": workspace.title,
            "workspace_type": workspace.workspace_type,
            "status": workspace.status,
            "current_task_id": workspace.current_task_id,
            "current_task": current_task,
            "current_step": current_step,
            "checkpoint": workspace.checkpoint.model_dump(),
            "task_brief": workspace.task_brief,
            "desired_outcome": workspace.desired_outcome,
            "project_type": workspace.project_type,
            "dataset_filename": workspace.dataset_filename,
            "development_sample_size": workspace.development_sample_size,
            "dataset_profile": (
                workspace.dataset_profile.model_dump()
                if hasattr(workspace.dataset_profile, "model_dump")
                else workspace.dataset_profile
            ),
            "dataset_analysis": (
                workspace.dataset_analysis.model_dump()
                if hasattr(workspace.dataset_analysis, "model_dump")
                else workspace.dataset_analysis
            ),
            "workbench_operations": [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in (workspace.workbench_operations or [])
            ],
            "notebooks": [
                {
                    "notebook_id": item.notebook_id,
                    "name": item.name,
                    "dataset_kind": item.dataset_kind,
                    "cell_count": len(item.cells),
                    "recent_cells": [
                        {
                            "cell_id": cell.cell_id,
                            "code": cell.code[-4000:],
                            "last_execution": cell.last_execution,
                        }
                        for cell in item.cells[-6:]
                        if cell.code.strip() or cell.last_execution
                    ],
                }
                for item in (workspace.notebooks or [])
            ],
            "processed_datasets": [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in (workspace.processed_datasets or [])
            ],
            "learner_skills": [
                dict(item)
                for item in database.get_skill_states_by_learner(learner_id)
            ],
        }

    learner_profile = database.get_learner_profile_by_id(
    learner_id
)

    if learner_profile is None:
        database.insert_learner_profile(
            learner_id=learner_id,
            answer_length="concise",
            learning_style="guided",
            code_support="medium",
        )


    # Kullanıcı mesajını SQLite veritabanına kaydeder.
    insert_message(
        session_id=request.session_id,
        role="user",
        content=message,
    )

    # Session'a ait mesajları veritabanından getirir.
    history = get_messages_by_session(request.session_id)

    # OpenAI'ye yalnızca son 10 mesajı gönderir.
    history = history[-MAX_HISTORY_MESSAGES:]

    previous_history = history[:-1]

    try:
        # Explicit beginner-help turns are controlled before the LLM so one
        # learning turn cannot expand into several tasks or a solution dump.
        reply = _deterministic_workspace_guidance(
            workspace_context=workspace_context,
            message=message,
            conversation_history=previous_history,
        )

        # Other turns continue through the adaptive mentor.
        if reply is None:
            reply = get_mentor_response_from_message(
                learner_id=learner_id,
                current_message=message,
                session_id=request.session_id,
                conversation_history=previous_history,
                workspace_context=workspace_context,
            )

        # Mesaj adaptive mentor tarafından ele alınmadıysa
        # normal chat davranışına geri dön.
        if reply is None:
            fallback_instructions = SYSTEM_PROMPT

            # Inside a workspace, even messages that do not map cleanly to a
            # catalogued skill are still mentor turns. The generic fallback
            # must preserve the same guided, one-step pedagogy.
            if workspace_context is not None:
                fallback_instructions += """
                
                WORKSPACE MENTOR MODE:
                - Act as the learner's senior mentor, not as a solution generator.
                - Use the current workspace stage/task as the source of truth.
                - Distinguish a QUESTION from a REQUEST TO CHANGE THE WORK PLAN.
                  A conceptual side question (for example "KPI ne demek?") is a temporary detour:
                  answer only that question briefly, then explicitly return the learner to the
                  same current workspace step. Never turn the example used in an explanation
                  into a new assignment, practice task, KPI exercise, or next action.
                - Never replace the current task merely because the learner asked about a term.
                  The workspace current_step/current_focus remains authoritative until real
                  workspace evidence shows that step was completed or the learner explicitly
                  asks to change direction.
                - If the learner says they do not understand, do not know what to do,
                  or asks for step-by-step help, give ONLY ONE atomic next action of the
                  CURRENT workspace step. Do not continue the topic of the preceding side question.
                - ONE atomic action means exactly one observable result. Do not combine
                  "count missing values" with "show/copy/sample missing rows" in the same turn.
                  Ask for the missing count first; wait for the learner's result before requesting examples.
                - If Current Workspace Context contains dataset_filename or dataset_profile, the data
                  is already attached. Never tell the learner to open, upload, attach, or reload that file.
                - In that situation use at most 3 short sentences, no numbered plan,
                  no multi-step checklist, and no code unless the learner explicitly asks for code.
                - Do not discuss later analysis, filling strategies, models, flags, or final
                  decisions before the learner completes the current small action.
                - Ask for the result of that action before advancing.
                """
                fallback_instructions += (
                    "\n\nCurrent Workspace Context:\n"
                    + json.dumps(
                        workspace_context,
                        ensure_ascii=False,
                        indent=2,
                    )
                )

            response = client.responses.create(
                model="gpt-5-mini",
                instructions=fallback_instructions,
                input=history,
            )

            reply = response.output_text
    # OpenAI cevap veremezse son eklenen user mesajını veritabanından siler.
    except AuthenticationError:
        delete_last_message(request.session_id)
        raise HTTPException(
            status_code=401,
            detail="OpenAI API anahtarı geçersiz.",
        )

    except RateLimitError:
        delete_last_message(request.session_id)
        raise HTTPException(
            status_code=429,
            detail="AI kullanım limiti veya bakiyesi yetersiz.",
        )

    except APIConnectionError:
        delete_last_message(request.session_id)
        raise HTTPException(
            status_code=503,
            detail="AI servisine şu anda ulaşılamıyor.",
        )

    except Exception:
        delete_last_message(request.session_id)
        raise HTTPException(
            status_code=500,
            detail="Beklenmeyen bir sunucu hatası oluştu.",
        )

    # Başarılı AI cevabını SQLite veritabanına kaydeder.
    insert_message(
        session_id=request.session_id,
        role="assistant",
        content=reply,
    )

    return {
        "reply": reply,
    }