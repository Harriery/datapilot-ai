# DataPilot AI — Security Roadmap

## Purpose

DataPilot must allow junior data professionals to work safely with personal,
public, company, and client data.

Security must not depend on the junior making the correct decision.

The system should enforce security rules at backend level and use
defense-in-depth so that one mistake does not automatically expose data.

The long-term goal is:

> A junior can make a mistake without automatically causing company data
> to leave the trusted environment.

---

# 1. Security Principles

## Default Deny

External AI access is denied unless policy explicitly allows it.

## Backend Enforcement

Frontend metadata must never be treated as trusted authorization.

Security decisions must be enforced by backend services.

## Local-First for Sensitive Data

Confidential and restricted data should remain local.

## External AI Is Optional

Core Data Engineering workflows must continue without external AI.

## Deterministic Validation

LLMs do not decide whether a technical transformation is correct.

Actual dataset changes are validated by deterministic code.

## Defense in Depth

Security must use multiple independent controls:

- authentication
- authorization
- tenant isolation
- data classification
- AI policy
- network controls
- encryption
- audit logging
- secure storage
- secure application design

---

# 2. Current Security Foundation

## Completed

- [x] Personal / Work usage context
- [x] Data sensitivity classification
- [x] Central external AI security policy
- [x] Default-deny behavior
- [x] Unknown context blocks external AI
- [x] Unknown sensitivity blocks external AI
- [x] Confidential data blocks external AI
- [x] Restricted data blocks external AI
- [x] Work data requires organization scope
- [x] Work + internal data requires organization AI policy
- [x] Local deterministic data-quality engine
- [x] Local execution-plan fallback
- [x] Local mentor fallback
- [x] Local free-text guidance without false learning evidence
- [x] Local deterministic transformation validation
- [x] Local learning evidence from validated transformations
- [x] Generic Data Quality routes moved to local-safe processing
- [x] Workspace findings are loaded from trusted backend state
- [x] Workspace planning uses trusted backend profile/findings
- [x] Confidential workspace analysis does not call external AI
- [x] Confidential workspace transformation review does not call external AI
- [x] Documents and Workspace use one central AI security policy

---

# 3. Local AI / Offline Security

## Local LLM

- [ ] Add Local LLM provider abstraction
- [ ] Add local model runtime support
- [ ] Benchmark models suitable for low-resource machines
- [ ] Local mentor conversations
- [ ] Local explanation of findings
- [ ] Local code / transformation guidance
- [ ] Local document Q&A
- [ ] Local embeddings or local retrieval
- [ ] Ensure Local LLM only sees authorized workspace context

## Offline Mode

- [ ] Explicit OFFLINE_MODE configuration
- [ ] External AI disabled when offline mode is active
- [ ] Application works without OpenAI API key
- [ ] Application works without internet connection
- [ ] Tests prove external model calls cannot occur
- [ ] Clear UI indicator for Local Secure Mode

## Air-Gapped Mode

- [ ] No runtime internet dependency
- [ ] No CDN assets
- [ ] No remote telemetry
- [ ] No external analytics
- [ ] No automatic remote model downloads
- [ ] Local frontend/backend assets
- [ ] Local model storage
- [ ] Network egress blocked at deployment level
- [ ] Air-gap regression test / deployment checklist

---

# 4. Identity and Access Security

## Authentication

- [ ] Replace learner_id trust with authenticated identity
- [ ] SSO / OIDC
- [ ] Microsoft Entra ID support
- [ ] Optional Google Workspace / Okta support
- [ ] Session security
- [ ] Secure logout
- [ ] MFA through identity provider where appropriate

## Authorization

- [ ] Organization membership validation
- [ ] Workspace ownership validation
- [ ] Role-based authorization
- [ ] Personal / Work server-side separation
- [ ] Prevent IDOR attacks
- [ ] Prevent learner_id spoofing

## Tenant Isolation

- [ ] Organization-level tenant isolation
- [ ] Database queries always scoped to authorized tenant
- [ ] Document isolation
- [ ] Workspace isolation
- [ ] Task isolation
- [ ] Local LLM context isolation
- [ ] Cross-tenant regression tests

---

# 5. Organization Security Policy

- [ ] Persist organization AI policies
- [ ] External AI allowed / blocked
- [ ] Approved AI providers
- [ ] Allowed sensitivity levels
- [ ] Local-only organization mode
- [ ] Organization retention policy
- [ ] Data residency settings if needed
- [ ] Organization administrators
- [ ] Policy versioning
- [ ] Policy decision audit records

The junior must not be able to override company policy.

---

# 6. Data Storage Security

## Raw Data

- [ ] Secure storage for blocked documents
- [ ] Secure workspace dataset storage
- [ ] Encryption at rest
- [ ] Encryption key management
- [ ] Secure temporary files
- [ ] Automatic temporary-file cleanup
- [ ] Prevent path traversal
- [ ] Safe file names
- [ ] File size limits
- [ ] Supported file-type validation

## Database

- [ ] Database encryption strategy
- [ ] Least-privilege database access
- [ ] Tenant-aware queries
- [ ] Sensitive metadata review
- [ ] Secure backup storage

---

# 7. Network Security

- [ ] External AI calls only through one controlled provider layer
- [ ] Central network egress policy
- [ ] Offline mode blocks network calls
- [ ] Allow-list approved external services
- [ ] TLS for production traffic
- [ ] Secure headers
- [ ] CORS hardening
- [ ] Rate limiting
- [ ] Request-size limits
- [ ] Abuse / DoS protection

---

# 8. Secrets Security

- [ ] No API keys in source code
- [ ] No secrets committed to Git
- [ ] Production secrets manager
- [ ] Separate development and production secrets
- [ ] Key rotation process
- [ ] Secret scanning in CI
- [ ] `.env` remains excluded from Git

---

# 9. Logging and Audit

## Secure Logging

- [ ] Raw datasets must not be written to logs
- [ ] Confidential prompts must not be written to logs
- [ ] Avoid sensitive traceback payloads
- [ ] PII / sensitive-value filtering
- [ ] Configurable logging levels

## Audit Trail

Record important actions such as:

- [ ] login
- [ ] workspace access
- [ ] document access
- [ ] dataset upload
- [ ] security classification
- [ ] external AI decision
- [ ] external AI request
- [ ] blocked external AI request
- [ ] local model use
- [ ] data export
- [ ] policy change
- [ ] administrative action

---

# 10. File and Input Security

- [ ] MIME validation
- [ ] Extension validation
- [ ] File-signature validation where appropriate
- [ ] File-size limits
- [ ] CSV parsing limits
- [ ] PDF parsing hardening
- [ ] Malformed input handling
- [ ] Formula-injection protection for exported CSV files
- [ ] Path traversal protection
- [ ] Dangerous archive handling
- [ ] Upload scanning strategy if required

---

# 11. Application Security

- [ ] Input validation
- [ ] Output encoding
- [ ] SQL injection review
- [ ] XSS review
- [ ] CSRF strategy where relevant
- [ ] IDOR tests
- [ ] Authorization tests
- [ ] Secure error responses
- [ ] Rate-limit sensitive endpoints
- [ ] Security headers
- [ ] Production debug mode disabled

---

# 12. AI-Specific Security

- [ ] Prompt injection threat model
- [ ] Retrieved document content treated as untrusted
- [ ] Tool calls require authorization
- [ ] LLM cannot override security policy
- [ ] LLM cannot change data classification
- [ ] LLM cannot grant itself external AI access
- [ ] Limit context to current authorized workspace
- [ ] Prevent cross-workspace context leakage
- [ ] Prevent cross-user context leakage
- [ ] Structured-output validation
- [ ] Deterministic validators remain source of truth

---

# 13. Dependency and Supply-Chain Security

- [ ] Pin important Python dependencies
- [ ] Pin frontend dependencies
- [ ] Dependency vulnerability scanning
- [ ] Automated security updates
- [ ] Review high-risk dependencies
- [ ] Lock files
- [ ] CI security checks
- [ ] Build provenance strategy for production

---

# 14. Backup and Recovery

- [ ] Backup strategy
- [ ] Encrypted backups
- [ ] Restore testing
- [ ] Workspace recovery
- [ ] Incident recovery procedure
- [ ] Data deletion / retention procedure

---

# 15. Security Testing

- [ ] Unit tests for every policy branch
- [ ] External-AI no-call regression tests
- [ ] Offline-mode network-block tests
- [ ] Tenant-isolation tests
- [ ] Authorization tests
- [ ] IDOR tests
- [ ] Upload-security tests
- [ ] Logging-leak tests
- [ ] Prompt-injection tests
- [ ] Local-LLM isolation tests
- [ ] Dependency scanning in CI
- [ ] Periodic security review

---

# 16. Threat Model

Create and maintain a threat model covering at least:

- malicious external attacker
- compromised user account
- junior user mistake
- malicious uploaded file
- malicious dataset content
- prompt injection
- cross-tenant access
- leaked API credentials
- vulnerable dependency
- compromised external AI provider
- compromised local model/runtime
- accidental logging
- insecure backup
- network egress
- insider misuse

For every important threat document:

1. asset
2. threat
3. attack path
4. prevention
5. detection
6. recovery

---

# 17. Production Security Gate

DataPilot must not be described as enterprise-security-ready until the
production security gate is completed.

Required before that claim:

- [ ] Real authentication
- [ ] Server-side authorization
- [ ] Tenant isolation
- [ ] Secure storage
- [ ] Encryption strategy
- [ ] Organization policies
- [ ] Audit logging
- [ ] Network controls
- [ ] Secrets management
- [ ] Security regression tests
- [ ] Threat model review
- [ ] Production deployment hardening

Until then, Work Mode should be presented as:

> Secure Work Mode — Preview / In Development