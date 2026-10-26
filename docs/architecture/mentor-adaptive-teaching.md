# Pending-task teaching: implementation and acceptance boundary

26 October 2026. The three-entry hint selector is removed. This change does not
prove novice usability or end-to-end project completion.

## Ownership and context

The investigation workflow owns task identity, scope, the read-only expression
and completion receipts. The teacher generates an explanation, one small
prerequisite action and its purpose. It cannot install a task or mark one complete.
Messages to a pending inspection reach teaching without a special help keyword.

The model receives the pending expression contract and contracts of successful,
current, version-verified observations. A missing count is not recorded as a row
filter. Normalized distributions retain the normalize option. Data-free syntax
flags show partial attempts, such as a missing condition without a distribution;
they are explicitly not correctness evidence. The last two accepted explanations
for the same task signature and scope are included. At most twelve teaching
turns are retained. Requests do not imply learning or skill mastery.

## Model use and failure

One bounded call uses the existing mentor runtime and billing/usage guards.
There is no classifier or automatic repair-call cascade. The response is a
TeachingExplanation with matching task identity. Mechanical checks reject code,
numerical claims, known unrelated columns and exact repeated explanations. Only
the backend can display the existing validated code after positive consent;
negative consent suppresses it. Stale tasks do not call the teacher.

These checks are not a semantic proof: generated prose may still be unhelpful,
introduce a wrong prerequisite, or make an unsupported claim in words. It cannot
advance the task from such a sentence. Live conversation and human review remain
required to evaluate teaching quality.

On failure, the same task stays pending and the local presenter supplies fallback
guidance. The visible message identifies it as fallback. Diagnostics distinguish
`accepted` (valid workflow task) from `teaching_accepted` (mechanically accepted
generated explanation), with provider attempts and safe failure reasons. Provider
exception bodies and credentials are not persisted in diagnostics.

### Presentation validation correction (26 October)

A live user turn reached Groq and fell back with `code_or_numeric_claim`.
The original rejected candidate was not retained, so that aggregate diagnostic
does not identify the exact trigger in that turn. Inspection reproduced false
positives for inline identifier markup and ordinary prose with parentheses.

The validator now separates presentation normalization from content checks:
single inline identifiers lose their backticks, and one leading list ordinal
is removed. Fenced blocks, compound code expressions, calls, unrelated columns
and numerical measurements still fail validation. A word followed by a space
and a parenthesis is no longer alone evidence of a function call. Spaced known
notebook method calls remain rejected. These are bounded checks, not a proof
that all possible generated prose is appropriate or code-free.

Rejections now record field/category pairs in `validation_violations` without
capturing user values in the trace. The last bounded, parsed rejected candidate
is retained locally as `last_rejected_teaching`, separately from accepted
lessons. It is not included in provider prompts or server logs. In generic mode
it keeps anonymous aliases; no actual user candidate is published in fixtures.
This makes a future rejection inspectable without guessing or another model
request. A fresh live-model acceptance turn is still required.

## Data boundary

For policy-allowed data the bounded learner question, structural contracts,
experience enum and previous explanations may leave the process. Rows, execution
output and the relationship map are excluded. Questions and schema can still
contain sensitive information; this mode requires the existing external AI policy.

Personal projects currently have no sensitivity selector. For absent/unknown
classification, a generic concept mode sends only operation types, anonymous
FIELD aliases, boolean display options, fixed help intent flags, language and an
experience enum. It excludes actual column labels, comparison literals, the
original question, outputs, workspace IDs and arbitrary metadata. Prior lessons
are reused only in their original neutral form. Real column labels are restored
locally in the reply. This can teach general concepts, but cannot understand
nuances removed from the original question. Known confidential/restricted data
and work contexts lacking approval stay on local fallback. This change does not
make every other mentor path an enterprise privacy boundary.

## Verification and reproduction

The tests use invented data and controlled responses, covering count-versus-filter
context, normalized distributions, partial attempts, history, scope changes,
task ownership, code consent, failures and prompt minimization. They do not prove
live model quality.

An isolated probe never touches user projects or executes generated code:

```powershell
python -m backend.benchmarks.run_mentor_teaching_probe --live
```

It makes at most two configured provider attempts, stops on the first failed
teaching response, and checks code consent locally. Default mode matches an
unclassified personal project; `--public-synthetic` tests the full synthetic
question mode. The report contains actual replies and human review questions.
Mechanical passage leaves novice usability and project completion unproven.

No Groq key is configured in the implementation environment, so live teaching
quality is not verified here. The existing Orders notebook is the next novice
acceptance scenario; no new dataset or workspace is needed for this check.
