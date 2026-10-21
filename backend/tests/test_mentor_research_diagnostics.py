from types import SimpleNamespace
from unittest.mock import patch
import json

import httpx
from openai import BadRequestError
import pytest

from backend.app import database
from backend.app.mentor_research_service import generate_research_reply, safe_provider_failure
from backend.app.mentor_research_store import load_research_state, save_research_state
from backend.tests.test_mentor_research_service import state, proposal, grounded_proposal, context
from backend.benchmarks.run_mentor_research_acceptance import run_live_case


@pytest.fixture(autouse=True)
def memory(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "diagnostics.db")
    database.init_db()


def test_incomplete_internal_plan_is_recorded_and_repair_sees_exact_rejection():
    s = state()
    bad = grounded_proposal(s)
    bad.next_action.columns = []
    bad.next_action.code = None
    good = grounded_proposal(s)
    outputs = [SimpleNamespace(output_parsed=bad), SimpleNamespace(output_parsed=good)]
    with patch("backend.app.mentor_research_service.get_ai_runtime", return_value=SimpleNamespace(client=None, provider="groq", model="test")), \
         patch("backend.app.mentor_research_service.guarded_responses_parse", side_effect=outputs) as provider:
        reply = generate_research_reply(context(), "sensor_value için kod verme, yönlendir", [])
    saved = load_research_state("w1", "n1")["last_validation"]
    assert saved["accepted"] is True
    assert len(saved["model_attempts"]) == 2
    first = saved["model_attempts"][0]
    assert first["raw_plan"]["next_action"]["code"] is None
    assert any("Inspection cannot be explained safely" in e for e in first["errors"])
    correction = json.loads(provider.call_args_list[1].kwargs["input"])
    assert correction["rejected_proposal"]["next_action"]["columns"] == []
    assert correction["required_internal_contract"]["active_focus"] == "sensor_value"
    assert "```" not in reply
    assert good.next_action.code not in reply


def test_provider_400_captures_reason_and_keeps_prior_model_attempt():
    s = state(); bad = grounded_proposal(s); bad.next_action.code = None
    error = BadRequestError(
        "Invalid structured response",
        response=httpx.Response(400, request=httpx.Request("POST", "https://example.test/responses")),
        body={"error": {"code": "json_validate_failed", "type": "invalid_request_error", "message": "Invalid response format"}},
    )
    with patch("backend.app.mentor_research_service.get_ai_runtime", return_value=SimpleNamespace(client=None, provider="groq", model="test")), \
         patch("backend.app.mentor_research_service.guarded_responses_parse", side_effect=[SimpleNamespace(output_parsed=bad), error]) as provider:
        with pytest.raises(BadRequestError):
            generate_research_reply(context(), "sensor_value", [])
    validation = load_research_state("w1", "n1")["last_validation"]
    assert provider.call_count == 2
    assert validation["provider_failure"]["http_status"] == 400
    assert validation["provider_failure"]["code"] == "json_validate_failed"
    assert validation["model_attempts"][0]["raw_plan"]


def test_provider_diagnostics_do_not_copy_credentials_or_other_body_fields():
    exc = Exception()
    exc.body = {"error": {"message": "bad gsk_abcdef12345 Bearer secret-value", "request_headers": {"Authorization": "secret"}}, "api_key": "secret"}
    output = json.dumps(safe_provider_failure(exc))
    assert "gsk_abcdef12345" not in output
    assert "secret-value" not in output
    assert "Authorization" not in output
    assert "api_key" not in output


def test_live_replay_stops_after_first_rejected_turn(tmp_path):
    def reject(ctx, message, history):
        save_research_state(ctx["workspace_id"], "n1", {"last_validation": {"accepted": False, "model_attempts": [{"proposal": {"answer": "Actual model text"}}]}})
        return "Blocked"
    with patch("backend.benchmarks.run_mentor_research_acceptance.generate_research_reply", side_effect=reject) as generate:
        result = run_live_case("sensors", tmp_path / "case.json", 0)
    assert generate.call_count == 1
    assert result["all_structurally_accepted"] is False
    assert result["full_scenario_exercised"] is False
    assert result["turns"][0]["validation"]["model_attempts"][0]["proposal"]["answer"] == "Actual model text"


def test_single_turn_smoke_is_not_a_full_scenario_pass(tmp_path):
    def accept(ctx, message, history):
        save_research_state(ctx["workspace_id"], "n1", {"last_validation": {"accepted": True}})
        return "One accepted response"
    with patch("backend.benchmarks.run_mentor_research_acceptance.generate_research_reply", side_effect=accept) as generate:
        result = run_live_case("sensors", tmp_path / "case.json", 0, max_turns=1)
    assert generate.call_count == 1
    assert result["all_structurally_accepted"] is True
    assert result["full_scenario_exercised"] is False
    assert result["planned_turns"] == 1
