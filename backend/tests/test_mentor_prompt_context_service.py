import json
from unittest.mock import patch

import pytest
import backend.app.database as database

import httpx
from fastapi.testclient import TestClient
from openai import APIStatusError

from backend.app.main import app
from backend.app.mentor_prompt_context_service import (
    compact_mentor_workspace_context,
    compact_mentor_history,
    compact_mentor_review_history,
    mentor_provider_overload_reply,
)


@pytest.fixture(autouse=True)
def setup_test_database(tmp_path):
    database.DATABASE_PATH = tmp_path / "test.db"
    database.init_db()


def _create_learner(learner_id: str):
    database.insert_learner_profile(
        learner_id=learner_id,
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
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
    _create_learner("mentor-context-regression")
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
    _create_learner("mentor-overload-regression")
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


def test_prior_notebook_findings_remain_visible_after_latest_cell():
    source = {
        "artifacts": {
            "selected_notebook": {
                "notebook_id": "flight-1",
                "name": "01_Data_Cleaning",
                "latest_cell": {
                    "cell_id": "now",
                    "code": 'df.loc[923, "DIVERTED"]',
                    "last_execution": {"success": True, "output": "np.int64(0)"},
                },
                "recent_cells": [
                    {
                        "code": 'df.loc[923, "DIVERTED"]',
                        "last_execution": {"output": "np.int64(0)", "success": True},
                    },
                    {
                        "code": 'df.loc[923, "CANCELLED"]',
                        "last_execution": {"output": "np.int64(1)", "success": True},
                    },
                ],
                "quality_checks": [
                    {
                        "title": "Cancelled Flight — Recorded Takeoff Investigation",
                        "note": "Satır 923: CANCELLED=1, DIVERTED=0. Acil iniş doğrulanmadı.",
                        "result_summary": "WHEELS_OFF = 1613",
                        "status": "needs_review",
                        "sample_row_count": 5000,
                    },
                ],
            },
        },
    }
    result = compact_mentor_workspace_context(source)
    notebook = result["artifacts"]["selected_notebook"]
    assert notebook["latest_cell"]["last_execution"]["output"] == "np.int64(0)"
    assert "CANCELLED" in json.dumps(notebook["recent_cells"])
    assert "CANCELLED=1" in json.dumps(notebook["quality_checks"])
    assert len(json.dumps(result, ensure_ascii=False)) < 6500


def test_secondary_evidence_413_does_not_discard_generated_mentor_reply():
    _create_learner("mentor-overload-regression")
    from types import SimpleNamespace
    from unittest.mock import patch
    from backend.app.mentor_service import get_mentor_response_from_message

    request = httpx.Request("POST", "https://api.groq.com/openai/v1/responses")
    error = APIStatusError(
        "TPM exceeded",
        response=httpx.Response(413, request=request),
        body={"error": {"type": "tokens"}},
    )
    decision = SimpleNamespace(skill_name="null_analysis", assistance_level="GUIDE")
    with patch(
        "backend.app.mentor_service.get_mentor_decision_from_message",
        return_value=decision,
    ), patch(
        "backend.app.mentor_service.generate_mentor_response",
        return_value="CANCELLED=1 kaydı iptal edilmiş uçuşu gösterir.",
    ), patch(
        "backend.app.mentor_service.process_learning_evidence",
        side_effect=error,
    ) as secondary:
        result = get_mentor_response_from_message(
            learner_id="mentor-overload-regression",
            current_message="Önceki Notebook bulgularını açıkla.",
            workspace_context={"workspace_id": "flight"},
        )
    assert "CANCELLED=1" in result
    secondary.assert_called_once()


@pytest.mark.parametrize("status_code", [400, 413, 422, 429, 500])
def test_secondary_provider_failure_keeps_mentor_reply(status_code):
    _create_learner("secondary-provider-regression")
    from types import SimpleNamespace
    from backend.app.mentor_service import get_mentor_response_from_message

    request = httpx.Request("POST", "https://api.groq.com/openai/v1/responses")
    error = APIStatusError(
        "secondary classifier rejected",
        response=httpx.Response(status_code, request=request),
        body={"error": {"type": "invalid_request"}},
    )
    decision = SimpleNamespace(skill_name="null_analysis", assistance_level="GUIDE")
    with patch(
        "backend.app.mentor_service.get_mentor_decision_from_message",
        return_value=decision,
    ), patch(
        "backend.app.mentor_service.generate_mentor_response",
        return_value="Mentorun doğrulanmış cevabı.",
    ), patch(
        "backend.app.mentor_service.process_learning_evidence",
        side_effect=error,
    ) as classifier:
        reply = get_mentor_response_from_message(
            learner_id="secondary-provider-regression",
            current_message="Önceki cevabını yeniden değerlendir.",
            workspace_context={"workspace_id": "example"},
        )
    assert reply == "Mentorun doğrulanmış cevabı."
    classifier.assert_called_once()


def test_notebook_recall_prioritizes_older_executed_fields():
    from types import SimpleNamespace
    from backend.app.mentor_context_service import build_trusted_notebook_state

    def cell(index, code, output):
        return SimpleNamespace(
            cell_id=f"cell-{index}", code=code,
            last_execution={
                "success": True, "output": output,
                "executed_at": f"2026-10-12T10:{index:02d}:00",
            },
        )

    cells = [
        cell(1, 'df.loc[923, "CANCELLED"]', "np.int64(1)"),
        cell(2, 'df.loc[923, "DEPARTURE_TIME"]', "np.int64(1603)"),
        cell(3, 'df.loc[923, "WHEELS_OFF"]', "np.int64(1613)"),
    ] + [
        cell(i, f'df.loc[{i}, "ARRIVAL_TIME"]', "np.int64(0)")
        for i in range(4, 14)
    ] + [cell(14, 'df.loc[923, "DIVERTED"]', "np.int64(0)")]

    notebook = SimpleNamespace(
        notebook_id="n1", name="01_Data_Cleaning", dataset_kind="raw",
        processed_dataset_id=None, cells=cells, quality_checks=[],
    )
    workspace = SimpleNamespace(
        notebooks=[notebook], dataset_profile={"columns": [
            "CANCELLED", "DEPARTURE_TIME", "WHEELS_OFF", "DIVERTED",
            "ARRIVAL_TIME",
        ]},
    )
    evidence = build_trusted_notebook_state(
        workspace=workspace, ui_context={"selected_notebook_id": "n1"},
        learner_message="923 için CANCELLED, DIVERTED, DEPARTURE_TIME ve WHEELS_OFF?",
    )
    compact = compact_mentor_workspace_context({
        "artifacts": {"selected_notebook": evidence}
    })
    notebook_context = compact["artifacts"]["selected_notebook"]
    source = json.dumps(notebook_context, ensure_ascii=False)
    for column in ("CANCELLED", "DIVERTED", "DEPARTURE_TIME", "WHEELS_OFF"):
        assert column in source
    assert "np.int64(1)" in source
    assert "np.int64(1603)" in source
    assert "np.int64(1613)" in source


def test_recent_notebook_evidence_preserves_source_cell_id():
    context = {"artifacts": {"selected_notebook": {
        "notebook_id": "note-1",
        "latest_cell": {
            "cell_id": "current", "code": "df.head()",
            "last_execution": {"success": True, "output": "latest"},
        },
        "recent_cells": [{
            "cell_id": "previous",
            "code": 'df.loc[923, "CANCELLED"]',
            "last_execution": {
                "success": True, "output": "np.int64(1)",
                "executed_at": "2026-10-12T12:00:00Z",
            },
        }],
    }}}
    compact = compact_mentor_workspace_context(context)
    previous = compact["artifacts"]["selected_notebook"]["recent_cells"][0]
    assert previous["cell_id"] == "previous"
    assert "CANCELLED" in previous["code"]
    assert previous["output"] == "np.int64(1)"


def test_review_history_preserves_last_assistant_opening_claim_instead_of_old_error():
    history = [
        {"role": "assistant", "content": "OLD: CANCELLED was 0"},
        {"role": "user", "content": "Explain recorded notebook evidence."},
        {
            "role": "assistant",
            "content": "LATEST: CANCELLED = 1; DIVERTED = 0. " + ("detail " * 180),
        },
    ]
    ordinary = compact_mentor_history(history)
    assert "LATEST:" not in ordinary[-1]["content"]
    review = compact_mentor_review_history(history)
    assert len(review) == 2
    assert review[0]["role"] == "user"
    assert review[1]["role"] == "assistant"
    assert "LATEST: CANCELLED = 1; DIVERTED = 0" in review[1]["content"]
    assert "OLD: CANCELLED was 0" not in json.dumps(review)


def test_review_history_is_bounded_when_previous_reply_is_extremely_long():
    content = "ACTUAL OPENING CLAIM. " + ("x" * 6200) + " FINAL CONCLUSION."
    review = compact_mentor_review_history([
        {"role": "user", "content": "y" * 3000},
        {"role": "assistant", "content": content},
    ])
    assert len(review) == 2
    assert len(review[0]["content"]) <= 650
    assert len(review[1]["content"]) < 3400
    assert review[1]["content"].startswith("ACTUAL OPENING CLAIM.")
    assert review[1]["content"].endswith("FINAL CONCLUSION.")
    assert "[middle omitted" in review[1]["content"]


def test_primary_mentor_self_review_prompt_contains_actual_previous_answer():
    from types import SimpleNamespace
    from backend.app.mentor_service import generate_mentor_response

    latest = "PREVIOUS REAL ANSWER: CANCELLED = 1, DIVERTED = 0. " + ("more " * 190)
    history = [
        {"role": "assistant", "content": "OLD ANSWER: CANCELLED = 0."},
        {"role": "user", "content": "Review row 923."},
        {"role": "assistant", "content": latest},
    ]
    with patch(
        "backend.app.mentor_service.get_ai_runtime",
        return_value=SimpleNamespace(
            client=object(), provider="groq", model="test-model"
        ),
    ), patch(
        "backend.app.mentor_service.guarded_responses_create",
        return_value=SimpleNamespace(output_text="Previous claim corrected."),
    ) as ai:
        answer = generate_mentor_response(
            learner_profile={"answer_length": "concise"},
            mentor_decision=SimpleNamespace(assistance_level="GUIDE"),
            current_message="Önceki cevabını teknik olarak yeniden değerlendir.",
            conversation_history=history,
            workspace_context={"title": "Test"},
        )
    assert answer == "Previous claim corrected."
    prompt = ai.call_args.kwargs["input"]
    assert "PREVIOUS REAL ANSWER: CANCELLED = 1, DIVERTED = 0." in prompt
    assert "OLD ANSWER: CANCELLED = 0." not in prompt


def test_fallback_self_review_keeps_actual_last_assistant_reply():
    from types import SimpleNamespace

    _create_learner("self-review-route")
    client = TestClient(app)
    created = client.post("/workspaces", json={
        "learner_id": "self-review-route",
        "title": "Review context",
        "workspace_type": "data_engineering",
    })
    assert created.status_code == 200, created.text
    workspace = created.json()
    session_id = workspace["mentor_session_id"]

    database.insert_message(session_id, "assistant", "OLD: CANCELLED = 0.")
    database.insert_message(session_id, "user", "Analyze my Notebook evidence.")
    database.insert_message(
        session_id, "assistant",
        "LATEST: CANCELLED = 1; DIVERTED = 0. " + ("details " * 140),
    )

    with patch(
        "backend.app.chat_routes.dispatch_local_investigation",
        return_value={"status": "needs_clarification"},
    ), patch(
        "backend.app.chat_routes.get_mentor_response_from_message",
        return_value=None,
    ), patch(
        "backend.app.chat_routes.get_ai_runtime",
        return_value=SimpleNamespace(client=object(), provider="groq", model="test"),
    ), patch(
        "backend.app.chat_routes.guarded_responses_create",
        return_value=SimpleNamespace(output_text="The latest claim was correct."),
    ) as ai:
        response = client.post("/chat", json={
            "session_id": session_id,
            "learner_id": "self-review-route",
            "workspace_id": workspace["workspace_id"],
            "message": "Önceki cevabını teknik olarak yeniden değerlendir.",
        })
    assert response.status_code == 200, response.text
    history = ai.call_args.kwargs["input"]
    assert any(
        item["role"] == "assistant" and "LATEST: CANCELLED = 1" in item["content"]
        for item in history
    )
    assert not any("OLD: CANCELLED = 0" in item["content"] for item in history)
    assert history[-1]["role"] == "user"
