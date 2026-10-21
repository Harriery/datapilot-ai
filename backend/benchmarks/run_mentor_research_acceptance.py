"""Replay isolated multi-turn cases through the production Notebook planner.

This is NOT an autonomous beginner or an end-to-end browser/usability test.
Offline mode checks adversarial guards. Live mode uses configured AI credentials
and writes actual replies for human technical/pedagogical review. Structural
acceptance never claims semantic correctness. No Flight workspace is touched.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from dotenv import load_dotenv
import pandas as pd

from backend.app import database
from backend.app.mentor_research_service import (
    ResearchAction, ResearchTurn, GroundedResearchPlan, build_research_request, generate_research_reply,
    prepare_research_context, validate_turn, safe_provider_failure,
    normalize_review_references, response_language,
)
from backend.app.mentor_grounded_reply import compile_reply
from backend.app.mentor_research_service import render_turn
from copy import deepcopy
from backend.app.mentor_research_store import load_research_state

CASES = {
    "sensors": ("temperature", "offline", "latency", "status_reason"),
    "retail": ("delivery_days", "returned", "order_value", "return_reason"),
    "service": ("response_seconds", "closed", "queue_minutes", "closure_reason"),
}


def snapshots(case):
    target, flag, measure, reason = CASES[case]
    frame = pd.DataFrame({target: [None if i % 2 == 0 else i for i in range(10000)],
                          flag: [i % 3 == 0 for i in range(10000)],
                          measure: [i % 41 - 20 for i in range(10000)],
                          reason: ["A" if i % 3 == 0 else None for i in range(10000)]})
    missing = frame[target].isna()
    code_and_output = [
        (f'df["{target}"].isna().sum()', str(missing.sum())),
        (f'df.loc[df["{target}"].isna(), "{measure}"].value_counts()', str(frame.loc[missing, measure].value_counts())),
        (f'df.loc[df["{flag}"] == 1, "{reason}"].isna().sum()', str(frame.loc[frame[flag] == 1, reason].isna().sum())),
    ]
    cells = [{"cell_id": f"c{i}", "section_title": target, "code": code,
              "last_execution": {"success": True, "output": output,
                                 "input_row_count": len(frame), "input_total_row_count": len(frame),
                                 "input_data_version": "isolated-fixture-v1", "dataset_kind": "working",
                                 "executed_at": f"2026-10-18T10:0{i}:00"}}
             for i, (code, output) in enumerate(code_and_output)]
    messages = [f"{target} sütunundaki boşlukları araştırıyoruz. Sayımımı açıkla ve kod vermeden tek sonraki adımı söyle.",
                "Son dağılım çıktısını açıkla. Ana araştırmayı koruyarak tek sonraki adımı söyle.",
                "Yardımcı kontrolü yaptım. Bu neyi kanıtlıyor, neyi kanıtlamıyor? Ana araştırmada nerede kaldık?",
                "Önceki cevabını teknik olarak yeniden değerlendir. Yeni görev verme."]
    for i, message in enumerate(messages):
        active = cells[:min(i+1, 3)]
        notebook = {"notebook_id": "n1", "dataset_kind": "working", "configured_development_rows": 10000,
                    "current_input_version": "isolated-fixture-v1", "latest_cell": active[-1],
                    "recent_cells": list(reversed(active)), "quality_checks": [], "available_columns": list(frame.columns)}
        yield {"workspace_id": f"acceptance-{case}", "task_brief": f"Investigate missing {target}; no domain rule supplied.",
               "dataset_profile_summary": {"columns": list(frame.columns)},
               "mentor_setup": {"approach": "guided", "experience_level": "beginner"},
               "artifacts": {"selected_notebook": notebook}}, message


def offline_case(case):
    context, message = next(snapshots(case))
    n = context["artifacts"]["selected_notebook"]
    state = prepare_research_context(n, message)
    focus = state["focus_column"]
    helper = CASES[case][1]
    ref = state["current_evidence_ids"][:1]
    bad = ResearchTurn(answer="Kayıtlı sonucu değerlendirelim.", claims=[], next_action=ResearchAction(
        instruction="Yardımcı sütunun eksiklerini say.", why="Yeni bir kontrol.",
        focus_column=focus, columns=[helper], kind="inspect", code=f'df["{helper}"].isna().sum()', evidence_ids=ref,
    ))
    drift_errors = validate_turn(bad, state, message)
    bad.next_action.columns = [focus]
    bad.next_action.code = f'df["{focus}"].isna().sum()'
    repeat_errors = validate_turn(bad, state, message)
    helper_ctx, helper_message = list(snapshots(case))[2]
    helper_state = prepare_research_context(helper_ctx["artifacts"]["selected_notebook"], helper_message, state)
    helper_state["response_language"] = "tr"
    selected = helper_state["current_evidence_ids"][:1]
    grounded, contract_errors = compile_reply(GroundedResearchPlan(next_action=None, evidence_ids=selected), helper_state, helper_message)
    latest = next(item for item in helper_state["observations"] if item["id"] == selected[0])
    contract = latest["analysis_contract"]
    population_preserved = contract.get("row_predicate") == {"op":"eq","column":helper,"value":1} and contract.get("measured_columns") == [CASES[case][3]] and contract.get("result") == 0
    passed = bool(drift_errors and any("already completed" in e for e in repeat_errors)
                  and population_preserved and not contract_errors and not validate_turn(grounded,helper_state,helper_message))
    return {"case": case, "mode": "offline_guards", "passed": passed,
            "drift_rejection": drift_errors, "repeat_rejection": repeat_errors,
            "observation_contract_tested": True, "result_group_is_preserved": population_preserved,
            "observation_contract": contract, "grounded_reply": render_turn(grounded,helper_state,helper_message) if grounded else None,
            "model_guidance_quality_tested": False, "semantic_quality_tested": False}


def reusable_prefix(case, previous, max_turns):
    """Reuse only unchanged fixtures whose cached proposals pass current checks."""
    prefix, history, state = [], [], {}
    for (context, message), cached in zip(list(snapshots(case))[:max_turns], previous):
        if not cached.get("accepted") or cached.get("message") != message:
            break
        notebook = context["artifacts"]["selected_notebook"]
        if cached.get("evidence_snapshot") != notebook:
            raise ValueError("Resume refused: scenario evidence changed")
        state = prepare_research_context(notebook, message, state)
        state["response_language"] = response_language(context, message, history, state)
        attempts = (cached.get("validation") or {}).get("model_attempts") or []
        if not attempts or not attempts[-1].get("proposal"):
            break
        try:
            proposal = ResearchTurn.model_validate(attempts[-1]["proposal"])
        except ValueError:
            break
        # Old accepted prose is not evidence of semantic correctness. Rebuild
        # every cached display from actual code/output; retain its raw trace.
        refs = [state["current_evidence_ids"][0]]
        for claim in proposal.claims:
            refs.extend(ref for ref in claim.evidence_ids if ref in state["current_evidence_ids"])
        plan = GroundedResearchPlan(next_action=proposal.next_action, evidence_ids=list(dict.fromkeys(refs))[:3])
        normalized, errors = compile_reply(plan, state, message)
        if errors or validate_turn(normalized, state, message):
            break
        rebuilt = deepcopy(cached)
        rebuilt["reply"] = render_turn(normalized, state, message)
        rebuilt["validation"]["rendering_contract"] = "grounded-v1"
        rebuilt["validation"]["cached_display_recompiled"] = True
        rebuilt["validation"]["model_factual_prose_published"] = False
        trace = rebuilt["validation"]["model_attempts"][-1]
        if "original_cached_proposal" not in trace:
            trace["original_cached_proposal"] = deepcopy(trace["proposal"])
        trace["cached_recompile_plan"] = plan.model_dump()
        trace["proposal"] = normalized.model_dump()
        prefix.append(rebuilt)
        history.extend([{"role": "user", "content": message}, {"role": "assistant", "content": rebuilt["reply"]}])
    return prefix, history


def run_live_case(case, report_path, delay, max_turns=4, previous=None):
    turns, history = reusable_prefix(case, previous or [], max_turns)
    reused = len(turns)
    if reused:
        print(f"{case}: reusing {reused} locally revalidated turns", flush=True)
    last_request = [None]
    def pace_request():
        if last_request[0] is not None:
            deadline = last_request[0] + delay
            while time.monotonic() < deadline:
                time.sleep(max(0, min(5, deadline - time.monotonic())))
        last_request[0] = time.monotonic()
    for context, message in list(snapshots(case))[reused:max_turns]:
        # Synthetic fixture evidence is included so reports can be reviewed
        # without guessing what the model actually observed.
        evidence_snapshot = context["artifacts"]["selected_notebook"]
        try:
            # Pace every actual request, including a model correction within
            # a turn, rather than only the outer replay turns.
            if delay > 0:
                reply = generate_research_reply(context, message, history, request_pacer=pace_request)
            else:
                reply = generate_research_reply(context, message, history)
        except Exception as exc:
            saved = load_research_state(context["workspace_id"], "n1")
            failure = safe_provider_failure(exc)
            # Preserve learner message; provider diagnostics also contain a
            # message field and must never overwrite the test input.
            if "message" in failure:
                failure["provider_message"] = failure.pop("message")
            turns.append({"message": message, "status": "provider_or_configuration_failure",
                          **failure, "accepted": False,
                          "validation": saved.get("last_validation"), "evidence_snapshot": evidence_snapshot})
            report_path.write_text(json.dumps({"case": case, "turns": turns, "human_review_required": True}, ensure_ascii=False, indent=2), encoding="utf-8")
            # Stop on provider/limit failure; do not burn quota repeating it.
            break
        state = load_research_state(context["workspace_id"], "n1")
        accepted = state.get("last_validation", {}).get("accepted") is True
        turns.append({"message": message, "reply": reply, "accepted": accepted,
                      "validation": state.get("last_validation"), "focus": state.get("focus_column"),
                      "evidence_snapshot": evidence_snapshot})
        history.extend([{"role": "user", "content": message}, {"role": "assistant", "content": reply}])
        report_path.write_text(json.dumps({"case": case, "turns": turns, "human_review_required": True}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{case}: turn {len(turns)}/{max_turns}, structural acceptance={accepted}", flush=True)
        if not accepted:
            # Later replay steps assume earlier guidance succeeded. Stop here
            # rather than consume quota after the first rejected turn.
            break
    return {"case": case, "mode": "live_production_planner", "turns": turns,
            "all_structurally_accepted": len(turns) == max_turns and all(t.get("accepted") for t in turns),
            "planned_turns": max_turns, "reused_turns": reused, "full_scenario_exercised": max_turns == 4 and len(turns) == 4,
            "human_review_required": True,
            "review_rubric": ["Does each answer address the actual question?",
                              "Does the helper check preserve the original research objective?",
                              "Are sample, preview and domain claims distinguished?",
                              "Is the proposed next step useful, justified and beginner-friendly?",
                              "Does self-review correct actual claims without a new task?"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume-latest", action="store_true", help="Resume the latest compatible live report using its isolated database.")
    parser.add_argument("--live", action="store_true", help="Use existing local AI settings (consumes provider quota).")
    parser.add_argument("--case", choices=["all", *CASES], default="all")
    parser.add_argument("--max-turns", type=int, choices=range(1, 5), default=4,
                        help="Use 1 for a cheap live protocol smoke test before the full suite.")
    parser.add_argument("--delay", type=float, default=65, help="Seconds between live turns; conservative for free-tier TPM.")
    parser.add_argument("--output-dir", type=Path, default=Path("backend/benchmarks/results/research-acceptance"))
    args = parser.parse_args(argv)
    load_dotenv()
    cases = list(CASES) if args.case == "all" else [args.case]
    previous_results = {}
    if args.resume_latest:
        if not args.live:
            parser.error("--resume-latest requires --live")
        candidates = sorted(args.output_dir.glob("*/report.json"), reverse=True)
        selected = None
        for candidate in candidates:
            saved = json.loads(candidate.read_text(encoding="utf-8"))
            if saved.get("mode") != "live" or not saved.get("results"):
                continue
            if any(r.get("planned_turns") != args.max_turns for r in saved["results"]):
                continue
            if not (candidate.parent / "isolated-research.sqlite").is_file():
                continue
            selected = (candidate, saved)
            break
        if selected is None:
            parser.error("No compatible live report and isolated database found; no calls were made")
        path, saved = selected
        folder = path.parent
        # Keep the failed report intact as diagnostic history before writeback.
        archive = folder / ("report-before-resume-" + datetime.now(timezone.utc).strftime("%H%M%S-%f") + ".json")
        archive.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        previous_results = {r["case"]: r.get("turns", []) for r in saved["results"]}
    else:
        folder = args.output_dir / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        folder.mkdir(parents=True, exist_ok=False)
    # A separate database means real project state, progress and chat remain untouched.
    database.DATABASE_PATH = folder / "isolated-research.sqlite"
    database.init_db()
    if args.resume_latest:
        for case in cases:
            if previous_results.get(case) and not load_research_state(f"acceptance-{case}", "n1"):
                parser.error("Resume database has no research state; no calls were made")
    results = []
    for index, case in enumerate(cases):
        if args.live and index and args.delay > 0:
            deadline = time.monotonic() + args.delay
            while time.monotonic() < deadline:
                time.sleep(max(0, min(5, deadline - time.monotonic())))
        result = run_live_case(case, folder / f"{case}.json", max(0, args.delay), args.max_turns,
                               previous_results.get(case)) if args.live else offline_case(case)
        results.append(result)
        if args.live and not result["all_structurally_accepted"]:
            break
    report = {"mode": "live" if args.live else "offline", "results": results,
              "human_review_required": args.live, "end_to_end_beginner_completion_proven": False,
              "flight_workspace_touched": False}
    path = folder / "report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"REPORT: {path.resolve()}", flush=True)
    passed = len(results) == len(cases) and all(r.get("all_structurally_accepted", r.get("passed", False)) for r in results)
    if passed and args.live and args.max_turns < 4:
        print("Protocol smoke passed; full scenarios and mentor quality remain unverified.")
    else:
        print("Guard checks passed; semantic quality remains unverified." if passed else "Evaluation incomplete or rejected; inspect report.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
