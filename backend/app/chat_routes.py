"""
Bu dosya AI sohbetiyle ilgili API endpoint'lerini içerir.

- Kullanıcı mesajını alır.
- İlgili session'ın konuşma geçmişini bulur.
- Mesajı OpenAI'ye gönderir.
- AI cevabını konuşma geçmişine ekler.
- OpenAI hatalarını uygun HTTP hatalarına dönüştürür.
"""
import os
import logging
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from openai import (
    OpenAI,
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
    APIStatusError,
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
from backend.app.ai_usage_guard import (
    AIUsageLimitError,
    get_ai_usage_status,
    guarded_responses_create,
)
from backend.app.ai_provider_service import (
    get_ai_runtime,
    get_ai_runtime_config,
)
from backend.app.mentor_workspace_context_service import (
    build_chat_mentor_workspace_context,
)
from backend.app.mentor_pedagogy_contract import enforce_discovery_contract
from backend.app.mentor_local_dispatcher_service import dispatch_local_investigation

import json


logger = logging.getLogger('uvicorn.error')

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
    """
    Kept as a narrow compatibility hook. Mentor V2 intentionally contains no
    dataset-specific columns, counts, or notebook code here; semantic guidance
    comes from the capability registry, workspace state and learning playbooks.
    """
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

        # Run local verification before constructing the bounded AI context.
        # Only explicit named-column investigations may dispatch; never
        # infer business rules or spend model tokens on data counting.
        from backend.app.workspace_data_service import get_workspace_data_dir
        local_result = dispatch_local_investigation(
            workspace,
            message,
            get_workspace_data_dir(workspace.workspace_id) / "working.csv",
        )
        if local_result.get("status") == "verified":
            database.save_workspace(workspace=workspace)

        workspace_context = (
            build_chat_mentor_workspace_context(
                workspace=workspace,
                learner_id=learner_id,
                ui_context=request.ui_context,
                message=message,
                current_task=current_task,
                current_step=current_step,
            )
        )
        workspace_context["local_investigation"] = local_result

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
        # Trusted local query results are rendered without a second model call.
        # This prevents the Mentor from overlooking verified counts and
        # asking the learner to repeat the same calculation.
        local_evidence = (
            (workspace_context or {}).get("local_investigation") or {}
        )
        if local_evidence.get("status") == "verified":
            evidence = local_evidence["evidence"]
            lines = [
                f"{evidence['target_column']} eksikliği, "
                f"{evidence['group_column']} sütununa göre incelendi.",
                f"Çalışma örneklemi: {evidence['total_rows']} satır; "
                f"eksik: {evidence['total_missing']} satır.",
            ]
            lines.extend(
                f"{item['value']}: {item['rows']} satır, "
                f"{item['missing_rows']} eksik, "
                f"{item['present_rows']} dolu (%{item['missing_pct']} eksik)."
                for item in evidence["groups"]
            )
            if evidence["groups_truncated"]:
                lines.append("Yalnızca en büyük gruplar gösterildi.")
            lines.append(
                "Bu sayılar doğrulanmıştır; iş kuralının nedeni henüz "
                "doğrulanmamıştır. Sence bu ilişkiyi nasıl yorumlamalıyız?"
            )
            reply = "\n".join(lines)
        else:
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

            runtime = get_ai_runtime(
                "mentor"
            )

            response = guarded_responses_create(
                runtime.client,
                provider=runtime.provider,
                purpose="chat_fallback",
                model=runtime.model,
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

    except AIUsageLimitError as exc:
        delete_last_message(request.session_id)
        raise HTTPException(
            status_code=429,
            detail=str(exc),
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

    except APIStatusError as exc:
        logger.warning(
            "Mentor AI provider rejected request (status=%d)",
            exc.status_code,
        )
        delete_last_message(request.session_id)
        if exc.status_code == 413:
            raise HTTPException(
                status_code=413,
                detail=(
                    "Mentor context exceeded the AI provider token limit. "
                    "Try a shorter question or retry after context refresh."
                ),
            ) from exc
        raise HTTPException(
            status_code=503,
            detail="Mentor AI provider request failed.",
        ) from exc

    except Exception:
        logger.exception(
            "Mentor chat request failed (workspace_attached=%s)",
            workspace_context is not None,
        )
        delete_last_message(request.session_id)
        raise HTTPException(
            status_code=500,
            detail="Beklenmeyen bir sunucu hatası oluştu.",
        )

    if workspace_context is not None:
        reply = enforce_discovery_contract(message, reply)

    # Başarılı AI cevabını SQLite veritabanına kaydeder.
    insert_message(
        session_id=request.session_id,
        role="assistant",
        content=reply,
    )

    return {
        "reply": reply,
    }

@router.get("/ai/usage")
def ai_usage_status():
    """Return local safety counters and resolved AI runtime configuration."""
    status = get_ai_usage_status()
    mentor_runtime = get_ai_runtime_config(
        "mentor"
    )
    classifier_runtime = get_ai_runtime_config(
        "classifier"
    )

    return {
        **status,
        "current_provider":
            mentor_runtime.provider,
        "current_model":
            mentor_runtime.model,
        "mentor_provider":
            mentor_runtime.provider,
        "mentor_model":
            mentor_runtime.model,
        "classifier_provider":
            classifier_runtime.provider,
        "classifier_model":
            classifier_runtime.model,
    }
