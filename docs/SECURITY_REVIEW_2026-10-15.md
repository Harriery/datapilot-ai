# Security review · 15 October 2026

## Decision

**Keep evaluation local, single-user and limited to public learning data. Shared/public deployment is blocked by missing authenticated access control.** This review does not establish that the project has been compromised, nor that every identified risk is remotely exploitable.

## Scope and evidence

Source reviewed at documentation base `7f95c707dccf9d757bfff93b00240ea0af1c49b5`, whose application code matches `main` at `3d9e5e6b5bb80e3b35e9e85302d6a133fea52354`. Separate fix branches and the developer's Windows integration checkout are outside the verified runtime scope. Review covers selected API routes, policy/access helpers, storage ingestion, browser execution, example configuration, the frontend lockfile and a limited reachable-history secret-pattern scan.

This is a focused source review and dependency audit, not a penetration test, complete data-flow audit or security certification. No live user records were accessed or deleted. No real model calls were made.

## Findings and remediation order

| ID | Priority / status | Evidence | Consequence and next action |
| --- | --- | --- | --- |
| SEC-01 | **High · source confirmed** | `backend/app/session_routes.py`: create/read/delete session handlers have no authenticated principal. `backend/app/main.py`: no global authentication dependency/middleware is installed. | A caller who can reach the API and has a session ID can request its history or deletion without proving ownership. UUID secrecy is not authentication. Add authenticated identity and enforce ownership on each operation; test missing identity and cross-user access. |
| SEC-02 | **High · source confirmed trust gap** | `backend/app/workspace_routes.py` scopes lookups with path-provided `learner_id`; `backend/app/document_access_service.py` compares stored ownership to a supplied requester ID. | Checks exist, but the requester identity is not established by authentication. Bind learner/organization scope to a server-verified principal rather than caller claims; test cross-workspace, cross-document and cross-tenant requests. This is part of the same access-control boundary as SEC-01, not a separate proof of exploitation. |
| SEC-03 | **High on a shared/exposed service · source confirmed gap** | `backend/app/workspace_data_service.py:save_workspace_dataset_stream` copies chunks until EOF without a total byte ceiling. `backend/app/document_routes.py` reads allowed document contents into memory without an application-level size cap in the inspected handler. | Chunking limits per-read memory, not total disk consumption. Enforce streaming byte limits, parser/resource limits and request/concurrency controls; reject oversized input and verify temporary-file cleanup and source preservation. Multipart/library/proxy limits were not comprehensively tested. |
| SEC-04 | **Medium · source confirmed; impact conditional** | `frontend/src/pythonRunner.ts` executes supplied Python in a shared Pyodide instance and loads assets from `cdn.jsdelivr.net`. | Browser Python is not an independently verified hostile-code boundary. Treat pasted/generated code as trusted local code for now. Review JS interop, network access, state isolation and resource exhaustion; design an isolated origin/runtime and enforce limits before supporting untrusted/shared notebooks. This is not evidence of backend arbitrary-code execution. |
| SEC-05 | **High audit severity · dependency matches confirmed** | `npm audit --package-lock-only --json` on 15 October returned **5 high, 0 critical package entries**. See the table below. | Review dependency paths, update compatible versions in a dedicated fix and rerun build/audit. Reachability from attacker-controlled input has not been demonstrated. Do not apply `npm audit fix --force` blindly; the suggested static-copy change includes a major downgrade. |

### Frontend dependency audit

The five package entries overlap: npm propagates a vulnerable transitive dependency's severity to parent packages. They are **not five independently reproduced application attacks**. The source-map and file-watching/glob paths require exposure analysis; a build-tool finding does not by itself demonstrate an exploitable deployed browser bundle.

| Package | Locked version | Audit evidence |
| --- | --- | --- |
| `brace-expansion` | `5.0.9` | [GHSA-qhr7-859c-m2p7](https://github.com/advisories/GHSA-qhr7-859c-m2p7), [GHSA-6j4f-fj2g-mc7p](https://github.com/advisories/GHSA-6j4f-fj2g-mc7p), [GHSA-q2hr-2g5m-vwhr](https://github.com/advisories/GHSA-q2hr-2g5m-vwhr) · denial-of-service advisories |
| `braces` | `3.0.3` | [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) · stack-exhaustion denial of service |
| `chokidar` | `3.6.0` | Inherits the `braces` finding |
| `vite-plugin-static-copy` | `4.1.1` | Inherits through `chokidar` |
| `source-map-js` | `1.2.1` | [GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q) · event-loop denial of service |

## Python dependency audit

`pip-audit -r backend/requirements.txt --no-deps --disable-pip` queried the pinned requirements on 15 October. It reported **19 advisory records across 2 packages**; two repeated pypdf entries reduce this to **17 distinct advisory IDs**. This checks the listed pins, not a resolved transitive environment or every platform dependency.

| Package | Pin | Distinct advisories | Reported fix versions / relevance |
| --- | --- | --- | --- |
| `anyio` | `4.14.1` | 3 | `4.14.2` for the returned advisories; includes conditional TLS hostname and subprocess/process-pool issues. Project exposure needs review. |
| `pypdf` | `6.14.2` | 14 | Returned fixes span `6.15.0`–`6.19.0`; assess a compatible version covering all findings and re-audit. Several affect PDF parsing/text extraction, a path present in document ingestion. Others concern operations not confirmed in this application. |

**SEC-06 · High remediation priority:** untrusted PDF input can exercise parser paths associated with resource-exhaustion advisories. No crafted PDF was executed; practical exploitability and severity per path were not tested. Combine dependency updates with byte, time and memory limits rather than relying on version changes alone.

Representative primary advisories: [pypdf font-width resource exhaustion](https://github.com/advisories/GHSA-fwg2-594c-jp42), [pypdf XForm text extraction](https://github.com/advisories/GHSA-763m-79hh-57f2), [AnyIO TLS hostname handling](https://github.com/advisories/GHSA-82r6-8w77-94w6). Machine-readable audit evidence is retained alongside this report.

## Existing protections observed

- `main.py` restricts CORS origins to localhost/127.0.0.1 port 5173. CORS is a browser-origin rule, not authentication or a firewall.
- `workspace_data_service.py` parses workspace IDs as UUIDs before constructing storage paths and uses unique staging files plus replacement/cleanup logic. No path-traversal flaw is claimed in this helper.
- `data_security_service.py` defaults to denying unknown context/sensitivity and blocks external AI for confidential/restricted classifications. Inspected document ingestion checks policy before content processing. Full enforcement across all model paths still needs a data-flow review.
- `ai_usage_guard.py` implements provider/billing checks and local request/output limits. These are not a substitute for authenticated rate limits or an enforceable guarantee about provider billing.
- `.env` is ignored and the tracked `.env.example` contains empty key fields. No real keys are needed for this review.

## Secrets scan result and limits

A limited pattern scan inspected selected text-file types across all locally fetched refs, covering **1,157 reachable commits**. It found **no matches** for the selected Groq/OpenAI/GitHub/AWS key formats or private-key headers. Values were not printed.

This does not prove the absence of secrets. Other credential formats, binary assets, removed remote refs, releases, issues, logs, local untracked files and provider dashboards were not audited. Add maintained secret scanning and a key-rotation process; do not rotate keys based solely on this negative scan.

## Privacy and operational boundaries still to verify

- Authenticated ownership, organization policy enforcement, tenant isolation and retention.
- Exact context/row samples sent to each external provider, redaction and prompt-injection handling.
- SQL execution paths and functions, export/formula safety, parser abuse, storage permissions, backup security and audit logs.
- Browser-origin isolation and timeout behavior for Notebook execution; CDN/offline strategy.
- Resolved transitive Python dependency coverage and reproducible installation; the pin-only audit above is not complete environment coverage.
- Deployment-level TLS, firewall, reverse-proxy limits, egress and monitoring. No deployed service configuration was inspected.

## Next security work

1. Establish an authenticated principal and deny unauthenticated data operations; add meaningful cross-user tests.
2. Resolve dependency findings with compatible upgrades and build/regression checks.
3. Bound uploads and expensive operations with resource and concurrency limits.
4. Trace external-AI data flows and isolate untrusted code execution.

Application code and dependency versions were deliberately left unchanged in this README-focused change. The [security roadmap](SECURITY_ROADMAP.md) remains the broader backlog; its checkboxes are not substitutes for these findings or acceptance tests.

## Primary guidance consulted

- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html): verify permissions on each request and derive access from trusted identity/context.
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html): bound uploads and validate input as part of layered controls.
- [Pyodide documentation](https://pyodide.org/en/stable/usage/faq.html): Python/JavaScript interoperation and browser-runtime behavior.

Guidance informs the recommendations; project-specific findings above come from the inspected source and audit output.
