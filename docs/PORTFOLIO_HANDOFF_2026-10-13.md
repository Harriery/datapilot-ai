# DataPilot AI — Portfolio Preparation Handoff

**Date:** 2026-10-13
**Purpose:** Preserve the real technical learning and engineering checkpoint while improving the public README and preparing LinkedIn material.

> This document supplements **docs/ACTIVE_ROADMAP.md**. Do not replace the detailed issue register or treat this document as proof of successful full-data runs.

## What this documentation session changes

- The public **README.md** is being refreshed in English for portfolio and recruitment purposes.
- Melbourne and Flight are presented as honest, differently scoped case studies.
- The user intends to prepare a real-screen demo and LinkedIn announcement **after reviewing the updated README**.
- No application logic, user workspace data, datasets, or tests are changed as part of this documentation work.
- Main may not contain the latest local development commits. Compare local state first; do not force-reset, overwrite, or silently merge work.

## Project principles to retain

1. DataPilot AI = real data workspace + adaptive mentor/practice; it should teach rather than do all the thinking.
2. Generalize data operations across different datasets (dataset-agnostic), avoid special rules for Flight/Melbourne column names.
3. Keep full raw data, development/working data, and Notebook samples separate in every analytical claim.
4. Prefer verifiable local/deterministic checks before AI claims; do not trade correctness for reduced token cost.
5. User learns Python/Pandas/SQL by writing small steps personally; AI guides without revealing complete answers prematurely.
6. Before app-code changes: reproduce issue, state expected behavior, specify tests, obtain permission, change only approved scope, run targeted/full tests plus build and live UI checks, record results.
7. AI coding assistance is substantial; describe contribution transparently in portfolio, not as entirely hand-coded individual work.

## Melbourne Housing — saved state, not yet reverified in UI

- Recorded dataset: **13,580 rows, 21 columns**.
- Project record reports data preparation, validation, logical model, KPIs, analysis, and dashboard.
- Latest technical notes say **8/9 deliverables**; final documentation/review/handoff and dashboard/filter confirmation still open.
- Next portfolio review: open actual saved Melbourne project; verify model, visuals, labels, artifacts and all delivery gates. Save **real English-language screenshots** (never fabricate app screenshots).
- Do not claim a formally completed 9/9 project until the app actually confirms it.

## Flight Delays & Cancellations — resume state

- Original CSV: **5,819,079 rows, 31 columns** in the latest project notes.
- Development/working sample recorded: **10,000**; Notebook session: **5,000**. Different scopes are **not equivalent**.
- Saved Notebook: **01_Data_Cleaning**; recorded Quality Check: **CANCELLATION_REASON — Missing Values Analysis**.
- On the recorded 5,000-row Notebook sample:
  - CANCELLED=1 AND CANCELLATION_REASON IS NOT NULL => **68**.
  - CANCELLED=1 AND CANCELLATION_REASON IS NULL => **0**.
  - CANCELLED=0 AND CANCELLATION_REASON IS NOT NULL => **0**.
  - CANCELLATION_REASON null count => **4,932**.
  - A filtered Pandas head(10) produced **10 rows × 31 columns**.
- These are **sample results, not full-source statistics**. Full-data verification remains pending.
- Saved latest learning direction: inspect negative DEPARTURE_DELAY / ARRIVAL_DELAY carefully; compare SQL/Pandas on the same scope; continue only one small learning step at a time.
- Additional Oct 13 analytical question raised in discussion: **DEPARTURE_TIME=1603, WHEELS_OFF=1613, and CANCELLED=1** in a displayed record. These clock-like fields alone do **not** prove the flight departed or that the record is invalid. Clarify field semantics, data scope, and the record before drawing a conclusion. Prior overconfident explanations must not be repeated as evidence.

## Open engineering issues to preserve

Follow the evidence and acceptance criteria in **docs/ACTIVE_ROADMAP.md**:

| ID | Problem |
| --- | --- |
| FL-001 | Full / development / Notebook sample boundaries can be confused |
| FL-002 | SQL queries prefixed with comments may be rejected |
| FL-003 | Running one Notebook cell may execute earlier cells unexpectedly |
| NB-004 | Local Notebook Sections + Quality Checks integration branch is not confirmed on GitHub main |
| MT-005 | Mentor Notebook evidence visibility / token overflow / stale intent |
| UI-006 | Navigation overlap with both sidebars open |
| QC-007 | Quality Check title suggestions can copy comment text blindly |
| QC-008 | Saved Quality Check scope labels can wrongly imply full-source context |

**Git integration checkpoint from saved user work:** local \`integration/notebook-sections\` with merges \`5007ab2\` and \`2b618a8\`; saved successful user verification included **546 backend tests** and a frontend build, plus UI persistence. These are **historical local results, not tests rerun by this documentation session**.

**GitHub main inspected before README work:** \`3d9e5e6b5bb80e3b35e9e85302d6a133fea52354\` (snapshot on 2026-10-13). Verify branch ancestry and local uncommitted files before app development resumes. Do not overwrite \`backend/benchmarks/results/\` untracked results.

## Resume procedure after LinkedIn preparation

1. Read this handoff and **docs/ACTIVE_ROADMAP.md**, particularly Flight/Notebook issue table.
2. Inspect local \`git status\`, current branch, and relation to GitHub; never assume public main is identical to the user's local working tree.
3. Open actual Flight workspace and check full/10k/5k scope and the latest Notebook section/cell.
4. Continue the user's real SQL/Pandas investigation and check the currently visible outputs. Do not create invented results or switch tasks to a new code feature without permission.
5. If addressing a blocking reliability issue, use the established reproduce → expected behavior → test → approval → fix → regression/UI verification flow.
6. Preserve Melbourne for end-to-end screenshots and final review, but do not let the portfolio detour erase the Flight learning checkpoint.

## Portfolio demo / sharing gates

1. Verify actual Melbourne saved project screen and the English UI language selector.
2. Record genuine application captures of project overview, data profiling, model, dashboard, Notebook, and Mentor with only verified outputs.
3. Use a short captioned English or Dutch video; disclose prototype status and AI-assisted development.
4. Review README, links, public code, and any screen capture for secrets or user data.
5. Share only after the user has reviewed and approved the final materials.
