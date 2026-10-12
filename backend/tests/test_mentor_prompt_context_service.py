import json
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from openai import APIStatusError

from backend.app.main import app
from backend.app.mentor_prompt_context_service import (
    compact_mentor_workspace_context,
    compact_mentor_history,
    mentor_provider_overload_reply,
)


def test_compact_context_retains_current_notebook_evidence_and_limits_size():
    context = {
        "title": "Aviation", "task_brief": "x" * 50000,
        "artifacts": {
            "selected_notebook": {
                "notebook_id": "n1", "name": "01_cleaning",
                "dataset_kind": "working", "cell_count": 60,
                "latest_cell": {
                    "cell_id": "c1", "code": "df['DEPARTURE_DELAY'].isna().sum()",
                    "last_execution": {
                        "success": True, "expression_kind": "scalar",
                        "output": "np.int64(67)", "executed_at": "2026-10-12",
                        "preview_rows": [{"blob": "z" * 200000}],
                    }
                },
            },
            "workbench_operations": [{"text": "x" * 40000} for _ in range(60)],
            "dataset_analysis": {"text": "y" * 30000},
        },
    }
    result = compact_mentor_workspace_context(context)
    assert len(json.dumps(result, ensure_ascii=False)) <= 6500
    latest = result["artifacts"]["selected_notebook"]["latest_cell"]
    assert "DEPARTURE_DELAY" in latest["code"]
    assert latest["last_execution"]["output"] == "np.int64(67)"
    assert "200000" not in json.dumps(result)


def test_compact_history_is_bounded():
    history = [{"role": "user", "content": "x" * 6000}] * 25
    concise = compact_mentor_history(history)
    assert len(concise) == 4
    assert all(len(item["content"]) <= 700 for item in concise)


def test_413_local_fallback_does_not_claim_full_data():
    reply = mentor_provider_overload_reply({
        "artifacts": {
            "selected_notebook": {
                "latest_cell": {
                    "code": "df['ARRIVAL_TIME'].isna().sum()",
                    "last_execution": {"success": True, "output": "np.int64(70)"},
                },
            },
        },
    })
    assert "ARRIVAL_TIME" in reply
    assert "np.int64(70)" in reply
    assert "tam kaynak veri doğrulanmadı" in reply


def test_stale_missingness_clarification_does_not_override_new_notebook_question():
    client = TestClient(app)
    created = client.post("/workspaces", json={
        "learner_id": "mentor-context-regression",
        "title": "Flight", "workspace_type": "data_engineering",
    })
    assert created.status_code == 200, created.text
    workspace = created.json()
    with patch("backend.app.chat_routes.dispatch_local_investigation", return_value={
        "status": "needs_clarification",
        "reason": "request_one_group_column",
        "target_column": "CANCELLATION_REASON",
        "informal_question": True,
    }), patch("backend.app.chat_routes.get_mentor_response_from_message",
              return_value="ARRIVAL_TIME sonucunu Notebook kapsamına göre değerlendirelim.") as mentor:
        response = client.post("/chat", json={
            "session_id": workspace["mentor_session_id"],
            "learner_id": "mentor-context-regression",
            "workspace_id": workspace["workspace_id"],
            "message": "ARRIVAL_TIME kontrolünde sıfır buldum, ne anlama geliyor?",
        })
    assert response.status_code == 200, response.text
    assert "ARRIVAL_TIME" in response.json()["reply"]
    mentor.assert_called_once()


def test_workspace_413_returns_grounded_local_reply_without_repeat_ai_call():
    client = TestClient(app)
    created = client.post("/workspaces", json={
        "learner_id": "mentor-overload-regression",
        "title": "Flight", "workspace_type": "data_engineering",
    })
    assert created.status_code == 200, created.text
    workspace = created.json()
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/responses")
    error = APIStatusError(
        "Request too large",
        response=httpx.Response(413, request=request),
        body={"error": {"type": "tokens"}},
    )
    with patch("backend.app.chat_routes.get_mentor_response_from_message", side_effect=error) as mentor:
        response = client.post("/chat", json={
            "session_id": workspace["mentor_session_id"],
            "learner_id": "mentor-overload-regression",
            "workspace_id": workspace["workspace_id"],
            "message": "Bu sonucu gördün mü?",
        })
    assert response.status_code == 200, response.text
    assert "AI sağlayıcısı" in response.json()["reply"]
    mentor.assert_called_once()
    history = client.get(f"/chat/{workspace['mentor_session_id']}/history").json()["messages"]
    assert history[-1]["role"] == "assistant"
