# Personal data mentor

This is an opt-in personal-project learning path, selected with **Kişisel verimle
birlikte çalışan mentor** in the existing mentor context selector. The saved value
is `personal_data`. It is routed before the old notebook research/planner,
classifier and discovery/review reply filters, independently of
`AI_NOTEBOOK_RESEARCH_ENABLED`. The UI displays which data context is selected;
the default is unchanged. No new branch, provider account or dataset is required.

## What changes

The model receives the project goal, learner preferences, current product screen,
data types, missing counts, example values and rows, recent notebook code/output,
saved quality checks and recent conversation. This is real personal project data
sent to the configured external mentor provider. Selecting the option explicitly
enables that sharing without reclassifying the data. Company workspaces and
confidential/restricted data cannot enable it.

There is no model-generated task contract to satisfy before answering a conceptual
question, forced answer JSON schema, missing-value-only action grammar, automatic
style rewrite, or post-generation discovery filter in this path. The role prompt
asks the model to mentor the learner using their actual work. Model output remains
unverified dialogue; it is not automatically executed or certified as correct.

The existing configured mentor model is retained. For GPT-OSS on Groq this path
requests medium reasoning. The same AI usage guard, free-only policy and account
quota apply to every generation attempt. Maximum output is 1500 tokens, further
limited by the existing configured output cap. No paid fallback is introduced.

## Data scope and inspection

The snapshot comes from the selected notebook's working/raw/processed CSV. The
existing CSV notebook sampling rule is reproduced: up to the configured rows,
using pandas `sample(random_state=42)` when the persisted input is larger. An input
version is checked before and after loading. The initial implementation handles
files up to 32 MiB and configured snapshots up to 20,000 rows. Larger inputs return
an explicit unavailable/budget status; no different sample is silently substituted.
The large raw DuckDB sampler is not yet connected to this path.

**The snapshot is the notebook INPUT, not the live browser Python `df`.** Model
tools cannot see unsaved in-memory transformations. Recorded notebook executions
remain separate observations. New executions save the code used and output
truncation flag, so edited drafts and legacy code/output pairs can be distinguished.

The model can request `inspect_data_sql` against the snapshot table `data`.
Examples include group counts, distributions, missingness comparisons and summary
statistics. Each query is a single SELECT in an ephemeral DuckDB connection with
external file/network access and Python replacement scans disabled. It has one
thread, a 128 MiB connection memory limit, no disk spill and a five-second interrupt.
Queries are at most 2,000 characters. Results return at most 20 rows and 12 columns,
with explicit truncation, then a bounded text-size projection. Counts and row scope
remain in the tool result rather than being inferred from model prose.

A turn permits at most two tool requests in one batch and two guarded model
attempts total: initial response, then interpretation of the tool results. There
are no automatic correction retries. The account may still reject a request for
quota/TPM, and the configured SDK transport retry settings remain unchanged.
Quota or incomplete output is not a teaching-quality result.

Up to six bounded server inspections are saved separately from learner execution
evidence. The next turn can receive the last three matching the same data version
and dataset kind. These inspections do not complete a learner task, write data,
record a business decision or mark project completion. Chat history is still
bounded; model-authored earlier statements are not promoted to evidence.

## Limits and acceptance

Transmitted context has explicit omission/truncation information. Initial context
is bounded to approximately 11,000 characters, recent conversation to six messages,
and total request messages to 18,000 characters. Full CSVs and unlimited notebook
history are not sent. A profile or example cannot establish a domain definition;
the mentor must distinguish exploration from confirmed business rules.

Controlled tests exercise actual CSV loading, notebook-equivalent sampling, SQL
results, persisted inspection memory, scope invalidation, quota accounting, actual
`/chat` routing and opt-in persistence. They cannot establish live model quality,
instruction following, effective teaching or novice project completion. No live
Groq credential is available in the implementation environment.

The next acceptance step uses the existing personal test dataset in the UI. Assess
whether the mentor can explain the project, use an actual inspection, teach a small
step, interpret the learner's next output, and retain the thread across follow-ups.
Do not equate a delivered answer or tool result with successful learning.
