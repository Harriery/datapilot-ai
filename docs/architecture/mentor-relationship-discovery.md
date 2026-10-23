# Local relationship discovery for notebook mentoring

Status: bounded experimental missingness discovery, not end-to-end mentor
acceptance. It uses the existing `AI_NOTEBOOK_RESEARCH_ENABLED` flag. Flight
remains paused; all new tests use invented datasets.

## Ownership and flow

The first mentor request with a selected working notebook builds a local map
of its persisted working input. This is lazy, not another blocking upload scan.
`mentor_relationship_service.py` computes and caches the map in SQLite.
`mentor_relationship_planner.py` turns a candidate into a small notebook
comparison. The existing investigation controller still owns pending tasks,
help, execution matching and completion; there is no second task lifecycle.

The input map is deliberately not notebook execution evidence. A user may have
filtered or transformed the in-memory `df` after loading. The presenter says
that input discovery has not yet verified the relationship in the notebook.
Only the existing checked execution path can mark a proposed task observed.

## Discovery contract

The current families are:

- Co-missingness: target missingness differs between helper-missing and
  helper-present records.
- Low-cardinality grouping: target missingness differs between an observed
  helper category and the rest. Numbers such as 0/1 receive no business meaning.

Use a deterministic random half for discovery and the other half for checking
the same selected contrast. Both groups require at least 20 rows in each half;
the absolute difference in missingness rates must be at least 0.25 in each
half and have the same sign. These are conservative exploration heuristics,
not a significance test, causal proof or multiple-comparison correction.
A random split within one working input does not establish generalization to
new sources or future time periods. Absence of candidates is not proof that
no relationship exists.

The bounded scan reads at most 20,001 records and analyzes at most 20,000, from
a working CSV at most 32 MiB. It examines up to 64 columns, prioritizing missing
targets, and up to 12 targets. At most three candidates per target are retained.
Rows/columns omitted and prefix selection are explicit. Large raw CSVs and
processed notebooks are not scanned by this component. It does not compute
continuous numeric relationships, temporal dependencies, business-key duplicate
semantics or arbitrary multi-column rules yet.

## Investigation contract

For a selected candidate, the planner requests one read-only expression at a
time: the helper distribution among target-missing rows, then the counterpart
among target-present rows. `normalize=True` makes these within-group proportions
rather than incomparable counts from different-sized populations. `dropna=False`
keeps the helper's missing category visible.

For co-missingness, compare the helper's `isna()` boolean indicator, rather than
enumerating potentially thousands of distinct measurements. The AST contract
supports only a direct literal single-column selection followed by `isna()` or
`isnull()` and `value_counts`; arbitrary transforms remain rejected. Rendering
labels True as missing and False as present, not as raw source values.

Existing matching current observations cover either side; the planner does not
request it again. Pending tasks still win over new planning. A version mismatch,
failed/stale latest execution, unsupported observation, explanation-only request
or absent justified candidate cannot assign this comparison. Both saved outputs
close this bounded comparison; they do not automatically validate a business
rule, cause, cleaning treatment or the input-map association. The existing
learner-requested deferral ledger remains available.

When both saved normalized Series are complete and unambiguous, the presenter
compares the printed labels' proportions and reports their approximate
percentage-point difference. This is a comparison of recorded outputs, not an
inference of label types, domain meaning or statistical significance. Duplicate
printed labels, truncated/empty outputs, invalid proportions or incomplete
distributions produce no numerical interpretation. If the notebook outputs
contradict the input candidate, the comparison follows those outputs rather
than repeating the candidate as a conclusion.

## Freshness, cost and disclosure

The cache uses input version, configured selection and algorithm version. A file
change during scanning discards the result. Changed inputs rebuild the map;
up to four maps per workspace are retained. It uses the existing file-stat
freshness mechanism, not a cryptographic content identity. No provider requests
are required for discovery or the selected two-sided local plan.

The map contains column names, bounded aggregate effect differences and status;
it stores no rows or category labels. Neither provider request builder includes
`local_relationship_map`. This is not a claim that the entire application sends
no data externally: existing chat messages, notebook outputs and column names
have their own paths and disclosure risks. The current implementation does not
deliver complete corporate isolation or anonymization. A separate enforced
outbound policy remains necessary for that claim.

## Verification and open acceptance

Tests cover renamed schemas, 31-column inputs, co-missingness, unrelated and
constant helpers, high-cardinality identifiers, tiny groups, contradictory
held-out patterns, budget coverage, input-map exclusion from both prompt
builders, cache reuse/invalidation and the saved workspace → real context →
`/chat` route. Full task trajectories verify both populations, explicit code
consent, pending help, new matching execution and no repeated assignments or
provider calls. Negative AST cases retain the safe expression boundary.

These are deterministic system checks. Live-model research choices, novice
comprehension, real browser interaction, full-source validation and a whole
data project still require acceptance. No learning-benefit claim is made.

Local verification on 23 October 2026: 973 backend tests passed, including 31
new relationship checks. Trajectories include notebook outputs that contradict
the preliminary input pattern: the visible comparison then reports equal
50%/50% proportions and zero percentage-point difference, instead of defending
the initial candidate. No provider-backed or human-learning acceptance is
claimed by these results.
