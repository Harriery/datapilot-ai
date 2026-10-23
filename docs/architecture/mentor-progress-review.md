# Mentor progress review — 23 October 2026

Status: architecture diagnosis and acceptance plan, not a shipped redesign.
Baseline: main at 1239e2c. Flight acceptance remains paused.

The product goal is a novice completing a data project through the application
mentor. Passing evidence-contract tests is necessary but does not establish
that goal. The recent local fixes addressed real failures without demonstrating
general teaching or sustained progress. This review changes the next unit of
work from another phrase-specific fix to one coherent investigation lifecycle.

## Findings from current code

| Finding | Evidence in the repository | Consequence |
| --- | --- | --- |
| Learning and notebook research have separate control paths. | `/chat` returns a research reply before the ordinary mentor path. Existing orchestration has observe/reason/decide/implement/validate/explain phases, but the research request does not carry the full learner model or stage plan. | Existing educational mechanisms do not automatically govern the notebook research reply. |
| There is no single enforced active task lifecycle across these paths. | Research stores a proposal list, clarification status, tutoring metadata and a separate refresh request. Successful proposed inspections can be appended without first resolving an equivalent pending inspection. | An unanswered next-step question can produce another copy of the same pending task. |
| Help is narrower than the supported analysis vocabulary. | `plan_pending_support` handles simple missing-row previews and single-helper distributions, not missing-value counts. Entry depends on selected language patterns. | A valid count task can lack beginner support, even when its calculation is fully supported. |
| The ordinary renderer is primarily an evidence report. | `compile_reply` supplies canonical observations and reasons; `render_turn` emits observations, limitations and scope on ordinary turns. | A short question about where to start can receive a long recap instead of a practical explanation of the current task. |
| Structured preview handling has a width cliff. | `missing_preview_rows` rejects rows with more than twelve fields. The request compressor also retains only the first twelve fields of each example. | A wide table can lose the local continuation available to a narrow synthetic table; relevant late columns may be absent from the prompt's example rows. |
| Existing synthetic chains cover important but narrow successes. | The connected benchmark uses a small schema and an unambiguous boolean helper. | Success does not establish handling of wide schemas, numeric flags, ambiguous helpers, ordinary wording, or a complete investigation. |

These are code findings. They do not establish the exact saved state of a later
Windows chat. For example, requesting a fresh missing count can be justified
when only an older unversioned count exists. A useful mentor must explain that
reason and teach the pending task; a repeated instruction alone is inadequate.

## Reproduction performed locally

An isolated SQLite workspace used invented fields, a fresh five-row preview with
15 columns, and a controlled planner response requesting a missing count. Two
ordinary conversation turns were sent without executing that count between them.
The production code produced:

| Measurement | Observed result |
| --- | --- |
| Real provider calls | 0 |
| Controlled planner calls | 2 |
| Structured preview rows usable by the local continuation | 0 |
| Pending inspect proposals afterward | 2 |
| Distinct pending inspection expressions | 1 |
| Length of the second rendered reply | 725 characters |

This is a reproducible structural failure under a controlled response, not a
live-model quality result. No uploaded diagnostic payload or real notebook
contents are included in this document.

## Next implementation boundary

Keep the evidence parser, scope/version tracking, source constraints and safe
inspection validation. Reconcile the research path with existing learning
orchestration rather than adding another independent mentor router.

1. Establish one persisted active-step identity for an investigation, with an
   explicit question, purpose, completion evidence, status and assistance level.
   Preserve previous observations as a finding ledger, including unresolved
   uncertainty and historical scope. A list of earlier code proposals alone
   must not serve as the investigation plan.
2. Classify the conversational event before selecting another task: new
   execution, help on the active step, explanation, source unavailable, explicit
   topic change, or next-step request. A bare assertion of completion is not
   execution evidence. Reworded questions must not create duplicate tasks.
3. Apply one transition policy. If a step is incomplete, explain or teach that
   step. If a saved execution meets its acceptance conditions, close it and
   choose a justified next step. Re-observation due to missing freshness must
   be explicit and tied to the particular legacy result.
4. Support the complete allowed operation vocabulary in the teaching layer,
   including missing counts. Retain checked factual values while allowing an
   appropriate conceptual explanation and a reason tied to the open question.
   Default to a short acknowledgement, one instruction and its purpose;
   detailed evidence belongs in an optional view, not every chat turn.
5. Select bounded, relevant preview columns explicitly, preserving value types
   and selection provenance. Width limits should reduce the displayed material
   deliberately or request a focused view, rather than silently discarding
   all usable context. Do not infer business semantics from a numeric flag.

This is a dataset-neutral control structure. It must allow alternate
investigation paths and an explicit unresolved outcome when evidence or source
definitions are insufficient. It must not impose filling/deleting values or
claim that an investigation succeeded merely because no further action exists.

## First acceptance target

Complete one bounded missingness investigation with a novice persona before
extending the revised lifecycle to transformations, modelling, KPIs or dashboards.
Success requires an evidence-backed finding and a documented treatment or
deferral decision, with its scope and remaining uncertainty. Technical evidence
checks, task progress and instructional quality are separate acceptance axes.

Minimum scenarios must include:

- Wide schemas and relevant columns beyond the first twelve fields.
- Multiple plausible helpers and numeric flags without documented meanings.
- Unavailable source descriptions expressed in several ordinary ways.
- A completed preview followed by an older count that genuinely needs refresh.
- A next-step question while that count is still pending: explain it without
  creating another task or inventing completion.
- Incorrect learner code, failed execution and an unsupported expression.
- Explanation-only requests, requests for hints and explicit requests for code.
- Reload/restart and scope changes during an active step.
- Finishing a finding without inventing a missingness cause or mandatory
  transformation.

Run both directions of each rule: legitimate refresh versus redundant refresh,
new evidence versus no execution, help versus explanation only. Evaluate whole
conversation trajectories and resulting application state, not just schema
acceptance or the presence of one instruction. A simulated learner must have a
limited skill profile and act on the mentor reply; it must not silently receive
the expert solution or execute the hidden proposal as if the novice understood.

Use controlled cases for state invariants, provider-backed repeated trials for
model behavior, and browser sessions for interaction. Keep provider request and
token budgets explicit. If no configured free provider is accessible, label
those results unavailable rather than substituting controlled responses and
calling them live acceptance. Learning benefit still needs human review.

## Relevant primary sources

- [Anthropic: Building effective agents](https://www.anthropic.com/research/building-effective-agents)
  recommends simple composable patterns and explicit workflow structure before
  additional agent complexity. This supports simplifying control ownership;
  it does not require adopting a framework.
- [LangGraph: Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
  separates thread-state checkpoints from durable application knowledge. The
  relevant design lesson is persisted task state; installing LangGraph alone
  would not supply the mentor's teaching or domain logic.
- [LearnLM: Improving Gemini for Learning](https://arxiv.org/abs/2412.16429)
  treats pedagogical instruction following as a training and evaluation problem.
  [Google's learning principles](https://blog.google/products-and-platforms/products/education/google-learnlm-gemini-generative-ai/)
  include managing cognitive load and adapting to the learner.
- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
  discusses multi-turn conversational evaluation using both verified end states
  and interaction quality. This motivates the acceptance target above; it is
  not evidence that DataPilot has already met it.
