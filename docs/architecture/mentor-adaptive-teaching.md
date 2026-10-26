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

### Existing-code explanation versus new solution code (26 October)

A subsequent local replay of the actual rejected response established a more
specific failure: the model correctly explained the recorded expression, while
the no-code validator rejected its quotations of that existing expression.
The replay required no provider call. The actual user transcript is not included
in repository fixtures; regression tests use invented fields and explanations.

The backend now renders inline references to the latest verified expression as
prose before validating teaching. Eligibility is derived from the supported
source AST: an exact subexpression or observed method signature can be named as
the existing column selection, condition or operation. Quotes with different
fields, calls or method arguments remain code violations. Fences remain rejected.
Only the explanation field permits source references; first_action and why keep
the no-code constraints. Source references are displayed as prose labels rather
than reproducing a program when the learner has requested no code.

Generic mode has no verified expression and receives no such allowance. Raw
measurements are not excused by the presence of an existing-code reference.
No code is executed, no task is assigned/completed, and no second provider call
is made by this rendering step. Diagnostics count the references rendered. This
is a bounded provenance check, not proof of semantic teaching quality.

## Data boundary

For policy-allowed data the bounded learner question, structural contracts,
experience enum and previous explanations may leave the process. Rows, execution
output and the relationship map are excluded. Questions and schema can still
contain sensitive information; this mode requires classification policy approval
or the scoped personal-project choice described below.

For absent/unknown personal classification without scoped sharing permission,
a generic concept mode sends only operation types, anonymous
FIELD aliases, boolean display options, fixed help intent flags, language and an
experience enum. It excludes actual column labels, comparison literals, the
original question, outputs, workspace IDs and arbitrary metadata. Prior lessons
are reused only in their original neutral form. Real column labels are restored
locally in the reply. This can teach general concepts, but cannot understand
nuances removed from the original question. This limitation was visible in a
live conceptual question: the original question was reduced to generic flags,
and the answer repeated the task instead of explaining the requested operations.
It was an information-loss problem, not evidence that the learner needed to
repeat the question more clearly.

The personal-project Mentor panel now exposes the effective notebook teaching
mode and a persisted choice. `ProjectMentorSetup.notebook_teaching_context` can
be `generic` or `question_and_code`; null retains the pre-existing classification
policy. Explicit `generic` also restricts public personal data to generic mode.
The scoped detailed choice permits the bounded learner message, previous
accepted questions/lessons, relevant column names and the latest successful,
version-verified supported inspection expression. The expression is rendered
from AST to remove comments. Arbitrary or unsupported code is not exported.
The payload also identifies the execution surface as Python notebook. Raw rows,
execution outputs, the local relationship map and broader metadata remain excluded.
Values typed in a message or supported code may be shared; this is stated before
the save action. This preference is not dataset reclassification, does not change
other mentor paths, and never bypasses confidential/restricted classification or
work policy. The personal-only PATCH endpoint checks workspace ownership using
the existing learner-ID mechanism; it is not enterprise authentication.

Turning sharing off excludes previous detailed-mode dialogue and the verified
expression from subsequent generic requests. Task identity, progress, notebooks,
data sensitivity and other learner setup preferences stay unchanged.

Known confidential/restricted data
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
unclassified personal project; `--question-and-code` tests explicit scoped sharing
without dataset reclassification. `--public-synthetic` tests the full synthetic
question mode. The report contains actual replies and human review questions.
Mechanical passage leaves novice usability and project completion unproven.

No Groq key is configured in the implementation environment, so live teaching
quality is not verified here. The existing Orders notebook is the next novice
acceptance scenario; no new dataset or workspace is needed for this check.

## Shared-core follow-up

The teacher now consumes the same investigation projection as the research
planner, with an explicit conversation kind and evidence references. The default
and question/code modes still exclude output values. An additional explicitly
saved personal-project preference permits only bounded parsed inspection
summaries, goals/preferences and investigation notes, never raw rows or arbitrary
cell output. See [the core implementation and retirement review](mentor-core-audit.md#implemented-follow-up-shared-investigation-and-conversation-contract)
for the new contract, six-turn probe, privacy boundaries and outstanding live
acceptance. Accepted provider candidates are retained separately from the
normalized teaching journal and are not replayed into provider prompts.

## Concept explanations without forced assignments

The October 26 live orders probe passed its first turn and rejected the second
because the model included a new illustrative selection expression despite the
no-code request. That rejection was a code-display-policy decision, not a numeric
claim or evidence that the model could not explain boolean filtering. The useful
prose and the weak follow-up instruction must be evaluated separately.

Two changes address the interface rather than accepting the whole raw proposal:

- `first_action` and `why` may be null. A concept-only question does not require
  another assignment. The current question should update the inferred learner
  need rather than repeat the previous difficulty. The workflow remains pending;
  an explanation is never an execution or proof of understanding.
- A narrow AST renderer can turn an inline, illustrative placeholder selection
  on the verified source dataframe into a generic prose role. This applies only
  to concept explanations, never instructions or reasons. It does not infer the
  placeholder's existence/type, execute it, validate its result, or display its
  syntax. It is counted separately from verified source references. Calls,
  nested filters, literals, unknown fields, assignments, fences and unquoted
  code retain the existing checks. Generic privacy mode has no source expression
  and cannot enable this rendering.

A zero-provider-call local replay of both actual synthetic probe candidates
retained the same pending task and displayed no unrequested code. The second
candidate required one conceptual-reference rendering; it did not become a
verified source reference. Its old first_action was retained and remains a weak
teaching step. Presentation acceptance is not pedagogical acceptance, and the
new nullable-action behavior still needs live testing.

No uploaded diagnostic transcript is checked into the repository. Invented
regression cases cover alternate placeholder names/accessors, all supported
languages, protected rendering boundaries, null actions in generic/detailed
contexts and task continuity. The CLI now prints failed-candidate details and
violation fields for synthetic probes and explicitly reports failed protocol
checks. `workflow_valid`, `content_accepted` and `teaching_accepted` distinguish
valid retained state from an accepted answer; legacy `accepted` is preserved.
