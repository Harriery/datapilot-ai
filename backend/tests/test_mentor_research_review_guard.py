"""Replay actual rejected model answers without another billed model call."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.app import database
from backend.app.mentor_research_service import (
    ResearchTurn, prepare_research_context, normalize_review_references,
    validate_turn, detect_visible_language, response_language, generate_research_reply,
)
from backend.app.mentor_research_store import load_research_state


@pytest.fixture
def actual_report():
    return json.loads((Path(__file__).parent / "fixtures/research_recorded_code_review.json").read_text(encoding="utf-8"))


def research_state(report):
    state = prepare_research_context(report["notebook"], report["message"])
    state["response_language"] = "tr"
    return state


def test_actual_turkish_repair_is_accepted_without_exposing_old_code(actual_report):
    state = research_state(actual_report)
    raw = ResearchTurn.model_validate(actual_report["proposals"][1])
    cleaned, changes = normalize_review_references(raw, state)
    assert validate_turn(cleaned, state, actual_report["message"]) == []
    assert "kayıtlı hücre" in cleaned.answer
    assert 'df[' not in cleaned.answer
    assert raw.next_action.code == cleaned.next_action.code
    assert 'df[' in raw.answer  # no mutation of the recorded raw response
    assert changes == ["replaced_exact_recorded_code_reference"]


def test_actual_english_response_is_rejected_for_language_not_source_code(actual_report):
    state = research_state(actual_report)
    raw = ResearchTurn.model_validate(actual_report["proposals"][0])
    cleaned, _ = normalize_review_references(raw, state)
    assert validate_turn(cleaned, state, actual_report["message"]) == [
        "User-visible response language does not match the requested language",
    ]


@pytest.mark.parametrize("text", [
    'Yeni çözüm: df["temperature"].fillna(0)',
    'Sonuç: df["temperature"].isna().sum() + 1',
    'Sonuç: df["temperature"].isna().sum().item()',
])
def test_unseen_or_extended_expression_is_not_whitelisted(actual_report, text):
    state = research_state(actual_report)
    raw = ResearchTurn.model_validate(actual_report["proposals"][1])
    raw.answer = text
    cleaned, _ = normalize_review_references(raw, state)
    assert 'df[' in cleaned.answer
    assert any("contains code" in error for error in validate_turn(cleaned, state, actual_report["message"]))


def test_quoting_old_code_does_not_allow_repeating_that_calculation(actual_report):
    state = research_state(actual_report)
    raw = ResearchTurn.model_validate(actual_report["proposals"][1])
    raw.next_action.code = actual_report["notebook"]["latest_cell"]["code"]
    raw.next_action.columns = ["temperature"]
    cleaned, _ = normalize_review_references(raw, state)
    assert "Calculation already completed in current evidence" in validate_turn(cleaned, state, actual_report["message"])


@pytest.mark.parametrize("text,language", [
    ("Bu sonuç eksik değer sayısını gösteriyor ve mevcut veriyi açıklıyor.", "tr"),
    ("The current result shows missing values in the recorded rows.", "en"),
    ("Bekijk de ontbrekende waarden in deze rijen voor de volgende stap.", "nl"),
])
def test_supported_language_mismatches_are_detectable(text, language):
    assert detect_visible_language(text) == language


def test_ui_language_is_explicit_and_code_only_turn_preserves_prior_language():
    assert response_language({"ui_context": {"language": "nl"}}, "Bu sonuç ne?", [], {}) == "nl"
    assert response_language({}, "sensor_value", [], {"response_language": "tr"}) == "tr"


def test_live_recorded_failure_and_repair_replay_through_production_service(actual_report, tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "replay.db")
    database.init_db()
    context = {"workspace_id": "recorded-regression", "artifacts": {"selected_notebook": actual_report["notebook"]},
               "dataset_profile_summary": {"columns": actual_report["notebook"]["available_columns"]}}
    from backend.app.mentor_research_service import GroundedResearchPlan
    old = ResearchTurn.model_validate(actual_report["proposals"][-1])
    ctx_state = prepare_research_context(actual_report["notebook"],actual_report["message"])
    # Legacy free prose is rejected, then a typed evidence selection is accepted.
    responses = [SimpleNamespace(output_parsed=old), SimpleNamespace(output_parsed=GroundedResearchPlan(next_action=old.next_action,evidence_ids=ctx_state["current_evidence_ids"][:1]))]
    with patch("backend.app.mentor_research_service.get_ai_runtime", return_value=SimpleNamespace(client=None, provider="groq", model="test")), \
         patch("backend.app.mentor_research_service.guarded_responses_parse", side_effect=responses) as model:
        reply = generate_research_reply(context, actual_report["message"], [])
    assert model.call_count == 2
    assert 'df[' not in reply
    assert "Sonraki tek adım" in reply
    assert "**5000**" in reply
    saved = load_research_state("recorded-regression", "n1")["last_validation"]
    assert saved["accepted"] is True
    assert "GroundedResearchPlan" in saved["model_attempts"][0]["errors"][0]
    assert saved["model_factual_prose_published"] is False
