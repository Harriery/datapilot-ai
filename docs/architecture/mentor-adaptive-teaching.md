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

The nullable-action change is retained: `first_action` and `why` may be null;
concept explanations do not require an assignment. An explanation never completes
a task or proves understanding.

An earlier generic-placeholder renderer converted new illustrative selection
syntax to prose. That shortcut has been retired. Only exact references to the
verified source expression are eligible for source-reference rendering. New
code inside an explanation is rejected rather than translated or removed
sentence by sentence. The earlier replay established presentation behavior only;
it did not establish pedagogical quality.

## Independent explanation, guidance and code contract

The existing provider fields now pass through one delivery compiler, rather than
one all-or-nothing content gate. No new mentor route or task owner is introduced.

| Section | Authority and checks | Failure behavior |
| --- | --- | --- |
| Explanation | Self-contained prose; same task, current verified evidence references, existing code/measurement/field and repetition checks. | Block delivery if invalid. Do not trim sentences, discard provenance, or rewrite new code into an approved explanation. |
| Optional guidance | One action and its dependent reason; same field/content checks. No generated code or unsupported measurements. | If either field is invalid, omit both, retain a valid explanation and record model noncompliance. A reason without an action is also omitted. |
| Code artifact | Only the existing validated pending-task expression, displayed by the backend after positive user consent. | Model prose and omitted guidance cannot become a code artifact or execute anything. |

The compiler validates the explanation independently before considering optional
guidance. Task/evidence/repetition failures remain blocking. Safe degradation
returns the original valid prose with null guidance; it does not invent replacement
instructions. `provider_contract_accepted=false`, `delivery_mode=explanation_only`,
field-level violations and omitted sections remain visible in diagnostics.
`teaching_accepted`/`content_accepted` describe delivered content, not full
compliance or learning quality. `workflow_valid` describes retained state;
legacy `accepted` still must not be read as a quality score.

Only displayed text enters subsequent teaching history. The original rejected
candidate remains a bounded local diagnostic and is not replayed in provider
prompts. No extra model/repair call is made. Privacy modes, protected-data gates,
execution receipts, explicit code consent and task completion remain unchanged.

Local zero-provider-call replays of the two actual synthetic reports distinguish
three outcomes: a fully admissible old turn; a code-contaminated explanation
that remains blocked; and a valid explanation delivered without its invalid
optional action/reason. All retained the pending task and displayed no
unrequested code. These are presentation/control results, not improved live
teaching acceptance. Uploaded transcripts are not committed as fixtures.

The six-turn scripted probe now separates content delivery from model compliance.
It collects deterministic content failures across the fixed scenario instead of
hiding later cases behind the first failure. Continuations after blocked replies
are marked explicitly; later fixed execution receipts are supplied test inputs,
not evidence that a novice learned or followed the mentor successfully. It stops
on provider/configuration/policy/schema failures rather than repeatedly spending
requests on them. The maximum remains six requests, one per turn, no retries.
Any model contract rejection keeps the protocol result failed, even if valid
explanations reached the screen. Raw candidates, omitted sections and the final
visible responses are reported separately for human review.

Live model consistency, question fulfillment, teaching quality and independent
novice project completion are still unproven. Retaining valid prose does not
establish that it answers a request for an actionable next step. Evaluate that
separately; never count a degraded reply as a complete pedagogical success.

## Isolated paired comparison: current versus simple

The existing probe CLI includes `--paired-comparison`. It does not change the
application's mentor, task ownership, prompts or validators. It compares two
bundles with the same configured free Groq model:

- **Current:** the production pending-task path, its actual provider input and
  structured proposal, followed by the current compiler/displayed reply.
- **Simple:** project goal, beginner level, question, known columns, sample scope,
  the unexecuted pending step and the supplied notebook code/output. It has no
  backend analysis-contract keys. A small answer-only schema returns the raw
  mentor answer; this experiment does not install that answer in the application.

This changes context, rules, output schema and rendering together. It cannot
attribute a difference exclusively to context. Comparing the current arm's raw
proposal with its displayed answer helps identify presentation losses separately.
A successful simple answer demonstrates only a capability on that checkpoint,
not a general model-quality or product-readiness result. Failure of both arms
alone does not prove model incapacity.

Both arms use the same source checkpoint and question, model, output-token cap
(at most 1200), input-character bound (9000), reasoning option and one guarded
request attempt. Prompt lengths/schema overhead intentionally differ and are
recorded. Call order alternates. There are no repair retries or automatic winner.
Usage tokens, elapsed time, actual instructions/inputs, raw candidates and final
current output are retained for human review. Guarded request counts can include
an attempt stopped locally before network access.

Three datasets have different missingness patterns, category labels and exception
structures. Checkpoints cover counting versus selecting, a syntax-error attempt
and a normalized-distribution result. They are independent frozen checkpoints,
not a live novice conversation: previous model answers are never used to seed the
other arm, and supplied execution receipts are not proof of learning. The default
three pairs cover all three schemas and question types (at most six attempts).
`--pairs 9` explicitly expands to the full matrix (at most eighteen attempts).

Project/research state is held in isolated memory. No suggested code is executed
and no real workspace, notebook or dataset is loaded or changed. The real
application AI usage ledger and normal guarded request/billing policies are
retained; isolation must not reset spending limits. Only a free-only, allowlisted
Groq runtime is accepted. API keys/provider exception bodies are never reported.
Configuration/provider failures stop the experiment and completed pairs remain
checkpointed. This is not an enterprise privacy guarantee for other app paths.

Prepare requests with zero provider access:

```powershell
& ".\venv\Scripts\python.exe" -m backend.benchmarks.run_mentor_teaching_probe --offline --paired-comparison
```

Collect matched live answers using the computer's existing `.env` configuration:

```powershell
& ".\venv\Scripts\python.exe" -m backend.benchmarks.run_mentor_teaching_probe --live --paired-comparison --pairs 3
```

At implementation time, all nine request pairs were prepared locally with zero
provider calls and controlled tests verified state isolation, the actual usage
guard/ledger, model/budget equality, raw-versus-displayed separation and partial
failure retention. A live attempt in the development environment stopped at
`blocked_configuration` with zero attempts: no Groq key/runtime was configured.
No live comparison winner, novice-learning benefit or improved mentor quality is
claimed. Human review scores remain empty until actual answers are assessed.
