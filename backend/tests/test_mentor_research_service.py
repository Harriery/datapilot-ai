from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.app import database
from backend.app.mentor_research_service import (
    ResearchTurn, GroundedResearchPlan, ResearchAction, ResearchClaim, prepare_research_context,
    validate_turn, render_turn, generate_research_reply, code_signature,
)
from backend.app.mentor_research_store import save_research_state, load_research_state


@pytest.fixture(autouse=True)
def memory_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "research.db")
    database.init_db()


def cell(field="sensor_value", code=None, rows=10000, success=True, section=None):
    return {"cell_id": field, "section_title": section or field,
            "code": code or f'df["{field}"].isna().sum()',
            "last_execution": {"success": success, "output": "np.int64(8047)",
                               "input_row_count": rows, "input_total_row_count": 20000,
                               "dataset_kind": "working", "executed_at": "2026-10-18"}}


def notebook(latest=None):
    return {"notebook_id": "n1", "dataset_kind": "working", "configured_development_rows": 10000,
            "latest_cell": latest or cell(), "recent_cells": [], "quality_checks": [],
            "available_columns": ["sensor_value", "helper", "arrival_metric"]}


def state():
    return prepare_research_context(notebook(), "sensor_value neden boş?")


def proposal(s, code='df.loc[df["sensor_value"].isna(), "arrival_metric"].max()'):
    return ResearchTurn(
        answer="Mevcut sayım eksikleri gösteriyor; nedenlerini henüz açıklamıyor.", claims=[],
        next_action=ResearchAction(
            instruction="Bu gruptaki en yüksek varış ölçümünü bul.",
            why="Boşluğun ölçüm düzeyiyle ilişkisini araştıracağız.",
            focus_column="sensor_value", columns=["sensor_value", "arrival_metric"],
            kind="inspect", code=code, evidence_ids=s["current_evidence_ids"][:1],
        ),
    )


def grounded_proposal(s, action=None):
    return GroundedResearchPlan(next_action=action or proposal(s).next_action,
                                evidence_ids=s["current_evidence_ids"][:1])


@pytest.mark.parametrize("focus", ["AIR_SYSTEM_DELAY", "blood_pressure", "invoice_total"])
def test_helper_check_never_automatically_changes_research_focus(focus):
    n = notebook(cell(focus))
    s = prepare_research_context(n, f"{focus} boşluklarını inceleyelim")
    n["latest_cell"] = cell("other", code='df[df["flag"] == 1]["reason"].isna().sum()', section=focus)
    n["recent_cells"] = [cell(focus)]
    updated = prepare_research_context(n, "sonucunu gördün mü?", s)
    assert updated["focus_column"] == focus
    assert len(updated["observations"]) == 2


def test_explicit_learner_topic_switch_changes_focus():
    n = notebook()
    s = prepare_research_context(n, "sensor_value")
    updated = prepare_research_context(n, "helper sütununa geçelim", s)
    assert updated["focus_column"] == "helper"
    assert updated["proposals"] == []


def test_valid_focus_related_action_is_accepted():
    s = state()
    assert validate_turn(proposal(s), s, "Sırada ne var?") == []


def test_helper_only_action_is_rejected_even_if_declared_focus_is_correct():
    s = state()
    p = proposal(s, 'df["helper"].isna().sum()')
    p.next_action.columns = ["helper"]
    assert "Inspection code omits the active target" in validate_turn(p, s, "Devam")


def test_focus_cannot_be_changed_by_model():
    s = state(); p = proposal(s); p.next_action.focus_column = "helper"
    assert "Proposed task changes the active research focus" in validate_turn(p, s, "Devam")


@pytest.mark.parametrize("code", ['df["sensor_value"].isna().sum()', "df['sensor_value'].isnull().sum()"])
def test_repeated_successful_check_is_rejected(code):
    s = state(); p = proposal(s, code); p.next_action.columns = ["sensor_value"]
    assert "Calculation already completed in current evidence" in validate_turn(p, s, "Devam")


def test_failed_calculation_may_be_retried():
    s = prepare_research_context(notebook(cell(success=False)), "sensor_value")
    p = proposal(s, 'df["sensor_value"].isna().sum()'); p.next_action.columns = ["sensor_value"]
    assert not validate_turn(p, s, "Düzeltmeye yardım et")


@pytest.mark.parametrize("kind", ["observation", "hypothesis"])
def test_notebook_cannot_support_full_source_coverage(kind):
    s = state(); p = proposal(s)
    p.claims = [ResearchClaim(text="Tam kaynakta eksikler var.", kind=kind,
        evidence_ids=s["current_evidence_ids"], coverage="full_source")]
    assert "Notebook evidence cannot establish a full-source claim" in validate_turn(p, s, "Devam")


def test_invented_evidence_id_is_rejected():
    s = state(); p = proposal(s)
    p.claims = [ResearchClaim(text="Bir gözlem.", kind="observation", evidence_ids=["invented"], coverage="shown_output")]
    assert "Unknown evidence reference" in validate_turn(p, s, "Devam")


@pytest.mark.parametrize("rows", [5000, None])
def test_old_or_unknown_scope_cannot_be_claimed_as_current_input(rows):
    s = prepare_research_context(notebook(cell(rows=rows)), "sensor_value")
    p = proposal(s); p.next_action = None
    p.claims = [ResearchClaim(text="Mevcut örneklemde sonuç.", kind="observation",
        evidence_ids=s["current_evidence_ids"], coverage="loaded_input")]
    assert "Unknown or stale scope cannot support a current-input claim" in validate_turn(p, s, "Sonuç?")


def test_self_review_does_not_assign_new_action():
    s = state()
    assert "Self review must not assign a new task" in validate_turn(proposal(s), s, "önceki cevabını yeniden değerlendir")


@pytest.mark.parametrize("code", ['df["sensor_value"] = 0', 'import os', 'df["sensor_value"].dropna(inplace=True)'])
def test_mutations_are_not_inspections(code):
    s = state(); p = proposal(s, code); p.next_action.columns = ["sensor_value"]
    assert validate_turn(p, s, "Devam")


def test_recorded_checks_do_not_become_passed_or_complete():
    n = notebook(); n["quality_checks"] = [{"status": "recorded"}]
    s = prepare_research_context(n, "sensor_value")
    assert "completed" not in s
    assert s["open_questions"]


def test_hypothesis_and_scope_are_visibly_qualified():
    s = state(); p = proposal(s); p.next_action = None
    p.claims = [ResearchClaim(text="Eksiklik koşula bağlı olabilir.", kind="hypothesis", evidence_ids=[], coverage="shown_output")]
    text = render_turn(p, s, "Neden?")
    assert "doğrulanmadı" in text
    assert "10,000" in text
    assert "Tam kaynak doğrulanmış sayılmaz" in text


def test_memory_is_isolated_and_survives_new_load():
    save_research_state("w1", "n1", state())
    assert load_research_state("w1", "n1")["focus_column"] == "sensor_value"
    assert load_research_state("w2", "n1") == {}
    assert load_research_state("w1", "n2") == {}


def test_same_observation_is_not_appended_repeatedly():
    s = state(); second = prepare_research_context(notebook(), "Devam", s)
    assert len(second["observations"]) == 1


def context():
    return {"workspace_id": "w1", "artifacts": {"selected_notebook": notebook()},
            "dataset_profile_summary": {"columns": notebook()["available_columns"]}}


def test_rejected_model_plan_gets_one_repair_and_is_not_shown():
    s = state(); bad = grounded_proposal(s); bad.next_action.focus_column = "helper"
    with patch("backend.app.mentor_research_service.get_ai_runtime", return_value=SimpleNamespace(client=None, provider="groq", model="test")), \
         patch("backend.app.mentor_research_service.guarded_responses_parse", return_value=SimpleNamespace(output_parsed=bad)) as call:
        result = generate_research_reply(context(), "sensor_value", [])
    assert call.call_count == 2
    assert "denetiminden geçmedi" in result
    assert bad.next_action.instruction not in result
    assert load_research_state("w1", "n1")["last_validation"]["accepted"] is False


def test_accepted_plan_uses_production_path_and_persists():
    s = state(); good = grounded_proposal(s)
    with patch("backend.app.mentor_research_service.get_ai_runtime", return_value=SimpleNamespace(client=None, provider="groq", model="test")), \
         patch("backend.app.mentor_research_service.guarded_responses_parse", return_value=SimpleNamespace(output_parsed=good)) as call:
        result = generate_research_reply(context(), "sensor_value", [])
    assert call.call_count == 1
    assert "en yüksek değeri bul" in result
    assert "**8047**" in result
    assert good.next_action.instruction not in result
    assert "```" not in result
    saved = load_research_state("w1", "n1")
    assert saved["last_validation"]["accepted"]
    assert saved["focus_column"] == "sensor_value"


def test_source_replacement_invalidates_same_size_notebook_observation():
    n = notebook(); n["current_input_version"] = "new-version"
    n["latest_cell"]["last_execution"]["input_data_version"] = "old-version"
    s = prepare_research_context(n, "sensor_value")
    assert s["observations"][0]["stale_scope"] is True


def test_cell_from_other_notebook_does_not_change_persisted_goal():
    s = state(); new = prepare_research_context(notebook(cell("helper")), "sonuç ne?", s)
    assert new["focus_column"] == "sensor_value"


def test_unexecuted_notebook_can_ask_one_clarifying_question():
    n = notebook(); n["latest_cell"] = None
    s = prepare_research_context(n, "Nasıl başlayacağım?")
    p = ResearchTurn(answer="Önce hedefi belirleyelim.", claims=[], next_action=ResearchAction(
        instruction="Bu veriyle hangi soruyu yanıtlamak istiyorsun?", why="İncelemeyi amaca göre seçeceğiz.",
        focus_column="", columns=[], kind="clarify", code=None, evidence_ids=[],
    ))
    assert not validate_turn(p, s, "Nasıl başlayacağım?")


def test_condition_values_are_not_mistaken_for_column_names():
    from backend.app.mentor_research_service import fields_in_code
    assert set(fields_in_code('df.loc[df["flag"] == "A", "reason"]')) == {"flag", "reason"}


def test_context_budget_preserves_latest_evidence_without_mutating_memory():
    from backend.app.mentor_research_service import build_research_request
    import json
    n = notebook()
    n["recent_cells"] = [cell(str(i), code='df["sensor_value"].isna().sum()') for i in range(7)]
    for c in [n["latest_cell"], *n["recent_cells"]]:
        c["last_execution"]["preview_rows"] = [{"blob": "z" * 100000}]
        c["last_execution"]["output"] = "x" * 900
    s = prepare_research_context(n, "sensor_value")
    original = deepcopy(s)
    request = build_research_request(context(), s, "sensor_value", [{"role": "assistant", "content": "x" * 5000}] * 10)
    assert len(json.dumps(request, ensure_ascii=False)) <= 10000
    assert request["current_observations"][0]["id"] == s["current_evidence_ids"][0]
    assert s == original


def test_offline_acceptance_runs_three_distinct_schemas():
    from backend.benchmarks.run_mentor_research_acceptance import CASES, offline_case
    assert len(CASES) == 3
    assert all(offline_case(case)["passed"] for case in CASES)


def test_notebook_chat_uses_the_validated_planner_instead_of_legacy_classifier(monkeypatch):
    monkeypatch.setenv("AI_NOTEBOOK_RESEARCH_ENABLED", "true")
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from backend.app.models import WorkspaceNotebook, WorkspaceNotebookCell
    client = TestClient(app)
    database.insert_learner_profile(learner_id="research-route", answer_length="concise", learning_style="guided", code_support="medium")
    created = client.post("/workspaces", json={"learner_id": "research-route", "title": "Research route", "workspace_type": "data_engineering"}).json()
    workspace = database.get_workspace(workspace_id=created["workspace_id"], learner_id="research-route")
    workspace.notebooks = [WorkspaceNotebook(notebook_id="n1", name="Analysis", dataset_kind="working", created_at="2026-10-18", updated_at="2026-10-18", cells=[WorkspaceNotebookCell(cell_id="c1", code='df["sensor_value"].isna().sum()', section_title="sensor_value", last_execution={"success": True, "output": "4", "input_row_count": 10000, "dataset_kind": "working"})])]
    workspace.development_sample_size = 10000
    database.save_workspace(workspace=workspace)
    # Capture the actual current execution ID from the production context.
    # The provider stub selects that ID from the request, as the model would.
    def parsed_response(*args, **kwargs):
        import json
        request = json.loads(kwargs["input"])
        return SimpleNamespace(output_parsed=GroundedResearchPlan(next_action=None, evidence_ids=[request["current_observations"][0]["id"]]))
    with patch("backend.app.mentor_research_service.get_ai_runtime", return_value=SimpleNamespace(client=None, provider="groq", model="test")), \
         patch("backend.app.mentor_research_service.guarded_responses_parse", side_effect=parsed_response) as provider, \
         patch("backend.app.chat_routes.get_mentor_response_from_message") as legacy:
        response = client.post("/chat", json={"learner_id": "research-route", "workspace_id": workspace.workspace_id, "session_id": workspace.mentor_session_id, "message": "sensor_value sonucum ne demek?", "ui_context": {"selected_notebook_id": "n1", "workbench_view": "notebook"}})
    assert response.status_code == 200, response.text
    assert "Araştırma hedefi: sensor_value" in response.json()["reply"]
    provider.assert_called_once()
    legacy.assert_not_called()
    assert load_research_state(workspace.workspace_id, "n1")["last_validation"]["accepted"]
