# Notebook mentor conversation: version 3

27 October 2026. Experimental teaching behavior; neither local tests nor delivery
success establishes mentoring quality or independent project completion.

## Why simplify

The previous live six-turn probe delivered no teaching answers. The model could
identify the syntax error and interpret the recorded proportions, but answers
failed the application's code/numeric/metadata contract. It also ignored no-code
requests and produced a wrong evidence identifier. Those are different failures;
counting them all as provider unavailability concealed the problem.

The earlier strict compiler did not certify truth: correct digit-bearing prose
could be rejected while unsupported claims written in words could pass. Version 3
removes that apparent guarantee rather than presenting a relaxed regex as a more
capable factual validator. It also does not claim that the model is now a good tutor.

## Conversation versus authority

The provider returns one bounded `TeachingAnswer.answer` string. No task identifier,
evidence identifier, conversation classification, action/reason pair or result
placeholder is required. The existing task and evidence ledger stay local. The
learning view contains goal, level, current question, permitted recent dialogue,
selected rows/columns, recorded work, latest code attempt and the pending step.
Internal analysis contracts are not teaching material.

Generated explanations and code suggestions are conversation only. They cannot
install an action, change data, execute code, create an observation, advance a
step or prove understanding. The existing workflow still requires a new matching,
current, supported execution receipt for completion. The research planner's
separate evidence/decision contract is unchanged.

A learner may explicitly request code. A model code suggestion is then labeled in
diagnostics `model_suggestion_not_executed`, never a validated pipeline artifact.
If no model code is included, the route can still display the existing pending
read-only expression after explicit code consent. With the provider disabled,
this existing local code-help path remains available. Model prose is never run.

## What is retained and retired

Retained:

- Existing data-sharing/organization policies, bounded input/output and free-only
  usage guards. One provider attempt; no classifier or automatic repair cascade.
- Current successful observations separated from partial/failed attempts.
- Task/scope identity, completion receipts, unavailable-definition memory and
  typed summaries already parsed by the backend.
- A presentation check that withholds detected executable code when code was not
  requested. Its failure is reported as `code_not_requested`, not provider outage.

Retired:

- Provider-generated task/evidence IDs and mandatory conversation classifications.
- Exact copied fact sentences, `[[result:ID]]` placeholders and their renderer.
- The blanket digit ban, blanket punctuation/backtick ban, source-AST quotation
  rewriting and field-specific action/reason compiler.
- Exact repetition as a delivery-blocking condition. Repetition is now a quality
  signal, not grounds to hide the whole answer.

The retired existing-code/compiler test module was removed. Tests for obsolete
formatting policies were replaced with current privacy, presentation, diagnostic
and authority checks; test counts before/after are not comparable quality scores.
No parallel runtime mentor or dataset-specific answer exception was added.

## Quality is explicitly unverified

Natural numbers, percentages and ordinary identifier markup can be delivered.
This is NOT an implementation of factual verification for natural language.
`numeric_prose_requires_review` marks digit-bearing text without claiming it is
wrong or right. Deliberately wrong numbers can pass schema/presentation checks;
a regression explicitly verifies that they never acquire factual or workflow
authority. The same is true of a bad recommendation written in words.

`content_accepted` / `teaching_accepted` mean an answer was delivered.
`provider_contract_accepted` means the bounded answer contract and presentation
check passed. `model_factual_prose_published` is true when conversation is delivered;
`factual_claims_verified` and `semantic_quality_verified` remain false.
`workflow_valid` describes retained state only. None certifies a helpful next step,
correct interpretation, source attribution, successful learning or project readiness.

The code detector is a presentation heuristic, not a sandbox, complete Python
recognizer or security boundary. Links and repetition are also review signals,
not automatic truth decisions. There is no hidden numeric-value-matching judge.
The prototype requires human review before novice/product acceptance.

## Data and history boundary

The last bounded code attempt remains available for explanation even if it is not
in the evidence grammar. Other literals/comments are redacted; ambiguous strings,
f-strings and truncated source may be withheld. The syntax diagnostic is computed
from sanitized source and labeled `local_parser`. Only built-in recorded exception
types are extracted; raw tracebacks, paths, exception messages and arbitrary row
outputs are excluded. This is not a general source-code secret detector.

Generic mode excludes real messages, code, labels, results and project metadata;
it uses anonymous fields and fixed intent flags. Question/code mode permits scoped
messages/code without output values. Explicit question/code/summaries consent adds
only typed current missing counts and complete parsed normalized distributions,
with row selection and recorded input scope. Input rows are not necessarily df's
size after preceding transformations; the full source is never implied verified.
Protected data and unapproved work policies still block this provider path.
Other application AI paths keep their own policies; this is no enterprise-wide
privacy claim.

Provider history includes only delivered version-3 lessons from the same task/scope
and sharing mode. Old dialogue with retired protocol markers is not replayed.
Revoking summary consent also excludes earlier summary-mode prose. The local
journal and old project evidence remain stored; they are not silently rewritten.
Rejected candidates are diagnostic records, never later prompt history.

## Verification and acceptance

Controlled invented-data tests verify one-field requests, no metadata/action
injection, unrequested-code failures, explicitly requested code suggestions,
numeric delivery without truth certification, failed/partial source context,
redaction, summary consent/revocation, generic isolation, provider failures and
unchanged task ownership. The paired probe still preserves usage accounting,
free-only policy, raw versus displayed text and partial failures.

The frozen six-turn API probe remains available:

```powershell
& ".\venv\Scripts\python.exe" -m backend.benchmarks.run_mentor_teaching_probe --live --dialogue-suite --case orders
```

At most six attempts, no retries; supplied execution receipts are scripted inputs,
not evidence that a novice followed the mentor. `result_context_available` means
parsed results were in the request, NOT that the answer used them correctly.
Human review evaluates whether the answer addressed the question, respected the
code preference, explained the actual attempt/result, retained exceptions and
supported a useful small next step. Reports identify context version 3.

The existing paired experiment can prepare all nine checkpoints offline, with zero
provider calls, or compare the current and simple bundles under the same configured
free Groq model. Context/rules/schema differ together; no automatic winner or
learning-quality conclusion is assigned. Local project state is isolated and the
normal usage ledger is retained. Safe provider error handling and request caps
remain. Historical reports from versions 1/2 are not new model-generation results.

No live Groq key is available in the implementation environment. A local replay
can establish changed presentation behavior only. Before further production claims,
freeze this implementation and evaluate actual model replies on the same scenarios,
then previously unseen questions/data. Repeated semantic or preference failures
should inform a model/scope decision, not another per-answer formatting exception.
The final acceptance remains a novice completing a new project with the mentor.
