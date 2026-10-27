# Notebook teaching: current contract and acceptance boundary

27 October 2026. This document describes the current implementation, not a
claim of novice learning or end-to-end project completion.

## Ownership

The existing investigation workflow owns the active step, scope, validated
read-only expression and completion receipts. The teacher explains the learner's
current question. It cannot execute code, replace the step, modify data or mark
an operation complete. A failed or unsupported expression can be useful learning
context without being a successful observation. No additional state owner or
mentor route is installed.

## Context at the provider boundary

The backend retains its analysis contracts for validation. `teaching_provider_view`
projects them into selection descriptions, column names and operation purposes.
Internal `row_predicate`, `measured_columns`, options dictionaries and completion
machinery are not teaching material. Project goal, learner preferences, unknown
source definitions and inferred difficulty remain available under the existing
sharing policy. Candidate explanations are explicitly untested. The provider
rules describe conversational responsibilities instead of explaining internal
wire keys or prescribing a dataset-specific reply.

`latest_attempt` includes the last bounded code attempt, even when it failed or
is outside the evidence grammar. String literals other than known column labels,
numeric literals and comments are redacted. Ambiguous strings/f-strings and
truncated code may be withheld entirely. A syntax diagnostic is computed from
the sanitized source and labeled `local_parser`: it is not a recorded successful
execution or the runtime's full error message. Only built-in exception type names
are extracted from the recorded output. Raw tracebacks, paths, exception messages,
row previews and arbitrary cell output are not sent. This is a bounded projection,
not a general-purpose source-code secret detector; code identifiers and the
learner's explicitly shared message can still contain sensitive information.

Current, successful, version-verified observations alone populate verified checks.
A count does not establish that rows were selected. Missing summaries mean unknown,
not zero. Input row counts describe recorded notebook loading, not necessarily the
size of df after prior transformations. Full-source validation is never inferred.

## Grounded numeric delivery

Summary consent permits only typed missing counts and complete, unambiguous
normalized distributions parsed from current verified observations. Each eligible
result has a compiler-owned full statement binding its row group, measured column,
category labels, values and recorded input scope. It also states that the full
source is unverified. There is no arbitrary match against a bag of allowed numbers.

The provider may cite an evidence ID and insert its supplied `[[result:ID]]` marker
in a natural explanation, or quote the complete immutable fact verbatim. The
compiler validates the citation and substitutes the scoped statement. It never
accepts a fabricated value, swapped category or different population merely
because that number occurs somewhere else. Unbound generated measurements remain
rejected. Markers cannot appear in optional guidance or survive on screen.

Qualitative interpretation surrounds the compiled result. The conversation label
(concept/attempt/evidence/plan/decision) is descriptive; it no longer determines
whether cited results reach the user. A valid cited observation is displayed even
if the model labels the question as a concept. Already expanded results are not
printed again by the route. This prevents a label error from hiding evidence;
it does not prove the interpretation is semantically correct.

## Explanation, guidance and code

`TeachingExplanation` remains the provider schema. An explanation may answer a
concept question without assigning work: action and reason can both be null.
When needed, guidance is one small prerequisite of the existing task. Count,
filter, error diagnosis and result interpretation are different conversational
needs; repeating the full pending task does not answer all of them.

The delivery compiler validates the explanation independently. Invalid optional
action/reason is omitted as a pair, with model noncompliance recorded. Invalid
explanation, task identity or provenance blocks delivery; there is no sentence
trimming, generated-code rewriting or automatic repair call. Exact references to
the latest verified expression may be rendered as prose; new solution code is
not admitted into an explanation. Requested code is the separately rendered,
validated pending expression, subject to positive code consent. It is never run.

The old syntax-only attempt-shape helper was removed: the provider now has one
bounded attempt view rather than duplicate summaries that hide the actual source.
The nullable action, existing-code reference renderer and independent guidance
compiler remain in use. No runtime module was removed solely for being old or
having many tests.

## Privacy and memory

- Generic mode uses anonymous fields and fixed intent flags. No real question,
  attempt, error diagnostic, labels, results or arbitrary project metadata is sent.
- Question/code mode permits the scoped question, relevant code/attempt context
  and descriptions, without aggregate values or result facts.
- Question/code/summaries adds bounded typed results, their category labels,
  project goal, preferences and investigation notes, under explicit personal consent.
- Confidential/restricted data and unapproved work policies block this provider
  path. Scoped personal preferences do not reclassify data or override work policy.

The Mentor panel describes the failed-attempt projection in TR/EN/NL. Its existing
save action and ownership checks remain. This does not establish enterprise-wide
privacy or authentication for other application paths.

Only displayed lessons enter the local journal. Provider history uses the checked
unexpanded explanation template and the current sharing mode. Revoking summary
consent excludes earlier summary lessons, preventing facts in prior prose from
leaking into question/code mode. Rejected candidates stay local and are not reused
as prompt history. Scope/task keys still prevent carrying lessons across versions.

## Diagnostics and limits

One guarded request, at most 1200 output tokens and 9000 provider-input characters,
uses the existing configured mentor model and free-only/usage policies. No classifier,
paid fallback or repair cascade is added. Provider exception bodies and keys are
not logged. Safe failure metadata remains available in the comparison probe.

`workflow_valid` describes retained task state. `teaching_accepted` and
`content_accepted` mean content was delivered. `provider_contract_accepted=false`
can accompany a valid explanation with omitted guidance. None is a teaching-quality
score. `semantic_quality_verified` stays false. `rendered_result_ids` identifies
backend-compiled factual delivery, not model-generated measurement authority.

## Verification and remaining acceptance

Controlled invented-data tests cover all three benchmark domains: failed and
partial source context, redaction, truncated code, internal-schema exclusion,
scoped result rendering, wrong category/group/value/measurement rejection, stale
or failed observations, consent revocation, generic isolation, code consent and
unchanged pending-task ownership. They establish boundary behavior, not model skill.
Actual uploaded transcripts are not committed as fixtures.

The frozen six-turn probe exercises count versus filter, masks, a partial attempt,
a syntax error, result interpretation and an unavailable source definition:

```powershell
& ".\venv\Scripts\python.exe" -m backend.benchmarks.run_mentor_teaching_probe --live --dialogue-suite --case orders
```

At most six requests are made, no retries. Scripted execution receipts are test
inputs; they do not prove a novice followed guidance. Deterministic content failures
are collected without concealing later turns; provider/configuration failures stop
the run. Raw candidates, delivered replies and diagnostics require human review.
This environment has no configured Groq key, so live quality remains unverified.

## Paired comparison

The same CLI retains `--paired-comparison`, `--pairs` and one-based `--start-pair`.
The current arm uses the current production boundary and compiler; the simple arm
uses question, goal, code and recorded outputs with an answer-only schema. Same free
Groq model, output cap and guarded ledger apply, with alternating arm order and
isolated in-memory project state. No model-suggested code is executed. Context,
rules, schema and rendering differ together, so this is not a context-only ablation.
No automatic winner is assigned.

The completed pilot checkpoints exposed two concrete losses: the old current
context omitted failed code, and the old delivery gate rejected a result-aware
answer containing numbers. The simple arm answered those checkpoints more directly,
but earlier simple replies violated no-code/step constraints and confused counts
with proportions. This supports correcting the boundary, not deploying the simple
arm wholesale or claiming general model superiority. Reports from before context
version 2 are historical baselines, not results of the current implementation.

Offline preparation uses zero provider calls:

```powershell
& ".\venv\Scripts\python.exe" -m backend.benchmarks.run_mentor_teaching_probe --offline --paired-comparison
```

An explicit HTTP 400/json_validate_failed rejection counts as an arm failure and
permits remaining fixed arms, without retry; final status retains arm failures.
Quota/configuration/unknown provider failures stop the run. Neither a completed
comparison nor passing mechanical checks proves novice project completion. The
ultimate acceptance remains an independently completed new project with the app's
mentor, including justified decisions and unresolved findings.
