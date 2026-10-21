"""One live follow-up after a cached, accepted data-dictionary clarification.

Only synthetic notebook evidence is used. No generated code is executed.
This measures one progression criterion, not an autonomous beginner or a project.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

from dotenv import load_dotenv

from backend.app import database
from backend.app.mentor_grounded_reply import compile_reply
from backend.app.mentor_observation_contract import expression_contract
from backend.app.mentor_research_service import (
    GroundedResearchPlan, ResearchTurn, code_signature, generate_research_reply,
    prepare_research_context, render_turn, response_language, safe_provider_failure,
    validate_turn,
)
from backend.app.mentor_research_store import load_research_state, save_research_state
from backend.benchmarks.run_mentor_research_acceptance import CASES, snapshots

FOLLOWUP_MESSAGE = (
    "Bilmiyorum, veri sözlüğüm de yok. Mevcut veriye bakarak araştırmaya devam "
    "edebilir miyiz? Kod vermeden tek bir küçük adımla yönlendir."
)


def validate_source_report(path: Path, case: str):
    """Revalidate the cached first turn without accepting arbitrary saved prose."""
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("mode") != "live":
        raise ValueError("Source must be an actual live acceptance report")
    results = report.get("results")
    if not isinstance(results, list) or any(not isinstance(item, dict) for item in results):
        raise ValueError("Source results must be a list of case records")
    result = next((item for item in results if item.get("case") == case), None)
    if not result or result.get("planned_turns") != 1 or len(result.get("turns", [])) != 1:
        raise ValueError("Source must contain exactly one planned, completed first turn for the selected case")
    turn = result["turns"][0]
    if not isinstance(turn, dict) or not isinstance(turn.get("validation"), dict):
        raise ValueError("Source turn must have recorded validation")
    validation = turn["validation"]
    if turn.get("accepted") is not True or validation.get("accepted") is not True or validation.get("rendering_contract") != "grounded-v1":
        raise ValueError("Source first turn must have passed the grounded-v1 path")
    context, message = next(snapshots(case))
    notebook = context["artifacts"]["selected_notebook"]
    if turn.get("message") != message or turn.get("evidence_snapshot") != notebook:
        raise ValueError("Source evidence or initial question differs from the current synthetic fixture")
    attempts = validation.get("model_attempts") or []
    if not isinstance(attempts, list) or not attempts or not isinstance(attempts[-1], dict) or not attempts[-1].get("raw_plan"):
        raise ValueError("Source has no recorded structured model plan")
    plan = GroundedResearchPlan.model_validate(attempts[-1]["raw_plan"])
    if plan.next_action is None or plan.next_action.kind != "clarify":
        raise ValueError("Source must end with the data-dictionary clarification")
    state = prepare_research_context(notebook, message)
    state["response_language"] = response_language(context, message, [], state)
    compiled, errors = compile_reply(plan, state, message)
    if errors or validate_turn(compiled, state, message):
        raise ValueError("Source plan no longer passes the current evidence/action checks")
    # The prior user-visible reply is rebuilt; unverified file text is not
    # promoted to assistant instructions or copied into the follow-up history.
    history = [{"role": "user", "content": message},
               {"role": "assistant", "content": render_turn(compiled, state, message)}]
    state["proposals"] = [{**compiled.next_action.model_dump(), "status": "proposed"}]
    state["open_questions"] = [compiled.next_action.instruction]
    context = deepcopy(context)
    context["workspace_id"] = "clarification-followup-" + case
    return context, state, history


def latest_source_report(root: Path, case: str) -> Path:
    for path in sorted(root.glob("*/report.json"), reverse=True):
        try:
            validate_source_report(path, case)
        except (OSError, ValueError, TypeError, KeyError):
            continue
        return path
    raise ValueError("No compatible accepted one-turn clarification report found; no model request was made")


def requires_missing_target(predicate: dict, target: str) -> bool:
    """Conservative entailment of this specific inspection criterion."""
    op = predicate.get("op")
    if op == "missing":
        return predicate.get("column") == target
    if op == "not":
        child = predicate.get("arg", {})
        return child.get("op") == "present" and child.get("column") == target
    children = predicate.get("args", [])
    if op == "and":
        return bool(children) and any(requires_missing_target(x, target) for x in children)
    if op == "or":
        return bool(children) and all(requires_missing_target(x, target) for x in children)
    return False


def progression_checks(validation: dict, context: dict) -> dict[str, bool]:
    """Do not label a repeated clarification as successful research progress."""
    action = None
    attempts = validation.get("model_attempts") or []
    if validation.get("accepted") is True and attempts:
        proposal = attempts[-1].get("proposal")
        if proposal:
            try:
                action = ResearchTurn.model_validate(proposal).next_action
            except ValueError:
                pass
    notebook = context["artifacts"]["selected_notebook"]
    target = notebook["section_title"] if "section_title" in notebook else notebook["latest_cell"]["section_title"]
    contract = expression_contract(action.code) if action and action.kind == "inspect" and action.code else {}
    successful_codes = {code_signature(cell.get("code", "")) for cell in notebook.get("recent_cells", [])
                        if (cell.get("last_execution") or {}).get("success") is True}
    return {
        "structurally_accepted": validation.get("accepted") is True,
        "proposes_an_inspection": bool(action and action.kind == "inspect"),
        "keeps_research_focus": bool(action and action.focus_column == target and target in action.columns),
        "selects_rows_with_missing_target": bool(contract.get("row_predicate") and requires_missing_target(contract["row_predicate"], target)),
        "does_not_repeat_recorded_calculation": bool(action and action.code and code_signature(action.code) not in successful_codes),
    }


def run_followup(source: Path, case: str, output_root: Path, *, live: bool):
    # Validate BEFORE creating files, changing the DB path or accessing an AI.
    context, state, history = validate_source_report(source, case)
    folder = output_root / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    folder.mkdir(parents=True, exist_ok=False)
    report = {
        "mode": "live_clarification_followup" if live else "offline_source_validation",
        "case": case, "source_report": str(source.resolve()), "source_revalidated": True,
        "cached_turns_reused": 1, "initial_turn_regenerated": False,
        "followup_message": FOLLOWUP_MESSAGE,
        "evidence_snapshot": context["artifacts"]["selected_notebook"],
        "history": history, "new_model_attempt_limit": 1,
        "proposal_executed": False, "project_completion_proven": False,
        "human_review_required": True, "flight_workspace_touched": False,
    }
    if not live:
        report.update(status="source_validated_only", followup_tested=False, progress_passed=False)
    else:
        previous_db = database.DATABASE_PATH
        try:
            database.DATABASE_PATH = folder / "isolated-followup.sqlite"
            database.init_db()
            save_research_state(context["workspace_id"], "n1", state)
            print("Reused one locally revalidated clarification turn; requesting one follow-up attempt.", flush=True)
            try:
                report["reply"] = generate_research_reply(context, FOLLOWUP_MESSAGE, history, max_attempts=1)
                report["status"] = "completed"
            except KeyboardInterrupt:
                report["status"] = "interrupted"
            except Exception as exc:
                report["status"] = "provider_or_configuration_failure"
                report["provider_failure"] = safe_provider_failure(exc)
            validation = load_research_state(context["workspace_id"], "n1").get("last_validation") or {}
            report["validation"] = validation
            report["progress_checks"] = progression_checks(validation, context)
            report["followup_tested"] = report["status"] == "completed"
            report["progress_passed"] = report["followup_tested"] and all(report["progress_checks"].values())
        finally:
            database.DATABASE_PATH = previous_db
    destination = folder / "report.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report, destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source-report", type=Path)
    source.add_argument("--from-latest", action="store_true")
    parser.add_argument("--source-root", type=Path, default=Path("backend/benchmarks/results/research-acceptance"))
    parser.add_argument("--output-dir", type=Path, default=Path("backend/benchmarks/results/clarification-followup"))
    parser.add_argument("--case", choices=tuple(CASES), default="sensors")
    parser.add_argument("--live", action="store_true", help="Use configured AI for one new follow-up attempt; consumes provider quota.")
    args = parser.parse_args(argv)
    load_dotenv()
    try:
        path = latest_source_report(args.source_root, args.case) if args.from_latest else args.source_report
        report, destination = run_followup(path, args.case, args.output_dir, live=args.live)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))
    print(f"REPORT: {destination.resolve()}", flush=True)
    if not args.live:
        print("Source validated locally; no follow-up or AI call was performed.", flush=True)
        return 0
    for key, passed in report["progress_checks"].items():
        print(f"{key}: {passed}", flush=True)
    print("Progress criterion passed; human guidance review remains required." if report["progress_passed"]
          else "Progress criterion not passed; inspect the actual proposal and reply.", flush=True)
    if report["status"] == "interrupted":
        return 130
    return 0 if report["progress_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
