# Mentor core audit: investigation and teaching continuity

26 October 2026. Source baseline: `4505dcb`. This is a diagnosis and redesign
contract, not an implementation or a claim that the mentor is ready.

## Findings established from the current code

| Area | Observed implementation | Consequence |
| --- | --- | --- |
| Document embeddings/RAG | `document_routes.py` calls `embedding_service`, `retrieval_service`, and `rag_service`. The notebook research/teaching path does not call this document retrieval. | Improving document vector similarity alone cannot repair this notebook conversation. |
| Product retrieval | `mentor_product_registry.retrieve_product_context` selects a registry slice using current UI state and stage aliases. The workspace context contains it, but the bounded research and teaching payloads omit this registry slice. | Having product knowledge in a workspace object does not establish that a model received it. |
| Research decision wire | `GroundedResearchDecision` exposes `next_action` and `evidence_ids`; action kinds are inspect/clarify. Instruction, rationale and factual prose are rendered by the backend. | The model cannot express a research hypothesis, alternatives, a justified treatment/defer recommendation or a teaching explanation through this wire. |
| Pending inspection | `generate_research_reply` routes a pending inspection to the teaching service before the research planner. | A task stays coherent, but all such turns share a narrow explanation path rather than an intent-sensitive investigation/teaching decision. |
| Teaching context | It includes the pending contract, current operation contracts, partial-attempt syntax signals, learner level, two accepted explanations and (with permission) the current question and verified expression. It omits observation values, project goal, learner approach/focus and product registry context. | It can explain an operation, but cannot independently reason about numeric results or the broader investigation from this payload. Excluding values can be appropriate for a concept question; treating every pending-task turn as that same kind of question is the limitation. |
| Durable workflow | The ledger retains focus, active task, scope, receipts, step history and deferred findings. Completion requires a matching supported expression/receipt. | This protects execution truth but does not constitute a general research memory of competing hypotheses, counter-evidence, learner misconceptions and decision criteria. Common partial/alias-based student code is outside the narrow observation grammar. |
| Local planning | Relationship candidates, missing previews and some continuations have deterministic planning paths. They precede the research model. | Some apparently adaptive decisions are local policy decisions; model selection alone cannot alter them. |
| Acceptance evidence | Existing controlled tests establish protocol and state behavior. One actual rejected explanation was locally replayed successfully after source-reference rendering. | Neither fact establishes a live novice conversation or end-to-end project completion. |

The earlier generic teaching mode also replaced the actual question with intent
flags. Explicit question/code sharing fixes that loss for consenting personal
projects; it does not itself supply the other missing investigation context.

## Local payload inspection

A zero-provider-call inspection using the existing invented teaching fixture
confirmed the following, without changing user data:

- Research payload contains project goal, learner setup, current observations,
  limited recent dialogue and workflow state.
- Teaching payload contains no project goal, learner approach, observation result
  values or product registry slice.
- The provider research wire has only `next_action` and `evidence_ids`.
- The active local task was a normalized distribution following a missing count.

These observations identify structural constraints, not a measure of the
Groq model's general reasoning ability. The correct actual count explanation
shows a particular capability; it cannot prove whole-project mentoring ability.

## Target core contract

Use a common bounded, intent-sensitive investigation context, with specialized
views rather than a single unlimited prompt. Reuse existing local data engines,
execution receipts, project deliverables, privacy controls and task ownership.

The shared research state should represent:

1. Project/stage goal, current research question and learning goal.
2. Source/working/notebook scopes and versions.
3. Verified observations with provenance and coverage; unknowns kept explicit.
4. Candidate explanations and what would support or contradict each.
5. Checks already attempted, their outcomes and why another check is useful.
6. Pending action and partial attempts, separately from learner understanding.
7. User preferences, recently identified misconceptions and attempted explanations.
8. A reason to conclude, defer or seek a source definition, plus the next stage.

The conversational decision should distinguish explaining a concept, interpreting
an output, proposing a new test, helping with a partial attempt/error and reaching
an investigation decision. A concept question need not replace the active task;
new counter-evidence must still be able to revise the investigation.

Keep numerical facts and mutation/execution authority grounded in deterministic
tools and receipts. Permit clearly labeled hypotheses and explanatory prose.
Generated code remains a separate, consent-controlled artifact. Style failures
should not silently become the same long generic task recap. No automatic repair
loop or unbounded provider spending is acceptable.

RAG should provide source-linked definitions, project documentation and relevant
teaching material when needed and permitted. It is not a substitute for current
execution state or research memory. The legacy document provider path must not be
silently enabled as a side effect of notebook mentoring work.

## Evaluation before model selection or readiness claims

First freeze a small conversation suite and record both the provider response
and the final displayed response. Use invented datasets with different names,
different missingness patterns and counterexamples. Cases must include:

- Starting without knowing what to inspect; asking a concept question mid-task.
- Counting versus filtering; asking for a small code example with explicit consent.
- A valid partial attempt, an execution error and a successful execution.
- A missing source definition, already-completed checks and contradictory evidence.
- An expected missingness pattern plus exceptions requiring further investigation.
- A scope/version change and a transition to a justified documented decision.

Evaluate question responsiveness, correct use of evidence, learning-level fit,
task continuity, recovery, repetition, useful progress and provider cost. Full
source and sample claims must remain distinct. A mechanically accepted response
does not automatically pass the pedagogical evaluation.

Compare the same model on the same cases with old versus redesigned context and
protocol. Only then compare models using equal context, tools and budgets. No
live paired comparison was run in this environment: no Groq key is configured.

After the investigation conversation passes, test the learner journey across
cleaning, modeling, analysis/BI and documentation. Final acceptance is a novice
completing a new project with the application's mentor and little outside help,
with unresolved issues recorded honestly. Do not infer this from unit-test count.

## Implementation boundary

This audit does not add another runtime fallback, exception or prompt patch.
The next implementation unit is a shared investigation context and conversation
decision contract evaluated on the frozen dialogue suite. Replace overlapping
owners gradually, preserving saved workspaces and notebooks; retire superseded
routes instead of adding another competing mentor path. Work stays on `main`.
