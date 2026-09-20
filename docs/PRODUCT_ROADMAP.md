# DataPilot AI — Product Roadmap

## Product Vision

DataPilot AI should not only help a junior clean a dataset.

It should guide a junior data professional from raw data to a validated,
documented, usable data product while gradually reducing mentor dependency.

The target outcome is:

> Raw data → structured work → validated result → deliverable data product.

---

# 1. Product Modes

DataPilot will have two clearly separated working areas.

## Personal Projects

For:

- learning
- portfolio projects
- open/public datasets
- personal datasets
- experimentation
- independent Data Engineering / Analytics projects

Personal Projects should be a usable Functional MVP.

## Secure Work

For:

- employer datasets
- freelance client datasets
- organization projects
- internal company work
- confidential or restricted data

Secure Work must prioritize security over convenience.

Current public-facing status:

> Secure Work Mode — Preview / In Development

The Work area may be visible and explorable, but unfinished enterprise
security features must be clearly identified.

---

# 2. Personal Projects — Core Idea

Personal Projects must not end after:

> inspect data → clean data → validate data.

The user should finish with a concrete deliverable.

Possible outputs include:

- cleaned dataset
- transformation pipeline
- analytics report
- Power BI-ready dataset
- Power BI dashboard
- data model
- KPI specification
- data-quality report
- documented portfolio project
- client-ready deliverable

---

# 3. Personal Project Workflow

Target workflow:

1. Project Goal
2. Data Source
3. Data Profiling
4. Data Quality
5. Cleaning
6. Transformation
7. Data Modeling
8. Analysis
9. KPI Definition
10. Visualization / BI
11. Validation
12. Documentation
13. Final Deliverable
14. Portfolio / Handoff

DataPilot should always remember the original project goal.

Completing data cleaning does not mean the project is complete.

---

# 4. New Personal Project

When the user creates a Personal Project, ask:

## What do you want to build?

Possible project types:

- Data Engineering Project
- Data Analysis Project
- BI / Dashboard Project
- Data Quality Project
- Portfolio Project

Later we can add additional templates.

---

# 5. Project Goal

Every Personal Project should have a meaningful outcome.

Example:

> Analyze public library usage and build a dashboard showing visitor trends,
> busiest locations, and districts with declining usage.

The project goal should drive:

- transformations
- analysis
- metrics
- model design
- visualization
- final deliverables

---

# 6. Deliverables

A project should contain explicit deliverables.

Example:

## Project Outcome

Create a Power BI report showing:

- library usage by district
- monthly visitor trends
- busiest library locations
- declining usage areas

## Deliverables

- [x] Dataset profile
- [x] Data-quality review
- [ ] Clean dataset
- [ ] Transformation pipeline
- [ ] Data model
- [ ] KPI definitions
- [ ] Power BI-ready dataset
- [ ] Dashboard
- [ ] Insight summary
- [ ] Data dictionary
- [ ] Methodology
- [ ] Portfolio README

The project is complete only when required deliverables are complete.

---

# 7. Example Personal Project

Example source:

Public/open library dataset.

Possible flow:

```text
Raw dataset
    ↓
Profile
    ↓
Quality findings
    ↓
Cleaning
    ↓
Transformations
    ↓
Business questions
    ↓
KPIs
    ↓
Data model
    ↓
Power BI-ready tables
    ↓
Dashboard
    ↓
Insights
    ↓
README / final report

Possible project output:
library-analysis/
├── data/
│   └── cleaned_library_data.csv
├── transformations/
│   └── transform.py
├── analysis/
│   └── insights.md
├── model/
│   └── data_model.md
├── powerbi/
│   └── dashboard_spec.md
├── documentation/
│   ├── data_dictionary.md
│   └── methodology.md
└── README.md
8. BI / Power BI Workflow
Power BI should become an important Personal Project outcome.
Initial integration does not need to automate Power BI itself.
First target:
Power BI-ready output.

DataPilot can guide the learner through:
1. Business questions
2. KPI selection
3. Fact / dimension identification
4. Star-schema design
5. Aggregation strategy
6. Clean output tables
7. Dashboard layout
8. Recommended visuals
9. Validation
10. Insight writing
Example:
FactLibraryVisits
- date_id
- library_id
- visitor_count
- loan_count

DimLibrary
- library_id
- name
- district

DimDate
- date_id
- month
- quarter
- year
Future possibilities:
- Power BI template support
- DAX mentoring
- Power BI model validation
- direct integration where practical
9. Portfolio Outcome
Personal Projects should help the learner build evidence of real ability.
Possible generated/supporting artifacts:
- README
- project summary
- architecture diagram
- dataset description
- methodology
- transformation explanation
- data dictionary
- KPI definitions
- screenshots
- lessons learned
- validation evidence
The final project should be suitable for:
- GitHub
- portfolio website
- interview discussion
- mentor review
- networking conversations
10. Freelance / Client Work
A useful future use case is independent paid work.
However:
Personal Projects should only contain:
- personal data
- public data
- open data
- learning datasets
Real client data belongs under Secure Work.
Future Work project types may include:
- Employer
- Freelance Client
- Non-profit / Organization
- Internal Team Project
This prevents real third-party data from being incorrectly treated as
personal data.
11. Secure Work Workflow
Secure Work is designed around the junior's assigned role and task.
Example:
Company task brief
    ↓
Authorized workspace
    ↓
Dataset / documents
    ↓
Local profiling
    ↓
Security policy
    ↓
Execution plan
    ↓
Junior performs task
    ↓
Deterministic validation
    ↓
Mentor guidance
    ↓
Review
    ↓
Handoff
The system should not invent responsibilities outside the junior's role.
12. Local AI Architecture
Target architecture:
                   DataPilot
                      │
        ┌─────────────┼─────────────┐
        │             │             │
Deterministic     Local LLM     External AI
Local Engine                       │
        │                           │
        └──── Security Policy ──────┘
Core work must remain usable without external AI.
Priority order for sensitive environments:
1. Deterministic local engine
2. Local LLM
3. External AI only when policy permits
13. Offline / Air-Gapped Mode
Future target:
Offline / Air-Gapped
        ↓
External AI unavailable
        ↓
Local Data Engine
        +
Local LLM
        ↓
Project continues
External AI must be an enhancement, not a core dependency.
14. Product UI Direction
The main product should clearly present two areas.
Personal Projects
Status:
Functional MVP

Message:
Build complete data projects with public or personal datasets.

Show capabilities such as:
- profiling
- data quality
- transformation
- analysis
- modeling
- BI
- validation
- portfolio outputs
Secure Work
Status:
Preview / In Development

Message:
Work with company or client data using security controls and local-first processing.

Visible status panel:
- Local Data Engine: Active
- External AI Policy: Active
- Confidential Data Blocking: Active
- Local LLM: In Development
- Offline Mode: Planned
- SSO / Tenant Isolation: In Development
- Audit / Encryption: Planned
Do not claim enterprise-production readiness until the Security Roadmap gate
is complete.
15. Workspace Security Status UI
Example Personal Project:
PERSONAL

Local Data Engine: Active
External AI: Available when allowed
Project Type: BI / Dashboard
Example Work Project:
WORK · CONFIDENTIAL

Secure Local Mode
Local Data Engine: Active
External AI: Blocked
Local LLM: In Development
Security state should be visible rather than hidden.
16. Immediate Development Plan
Phase A — Preserve the Plan
- Define Personal vs Work product direction
- Define Security roadmap
- Define Personal Project outcome
- Define data-product concept
Phase B — Make the Product Visible
- Create clear Personal Projects / Secure Work entry experience
- Mark Personal as Functional MVP
- Mark Secure Work as Preview
- Add security-state UI
- Keep unfinished security capabilities clearly labelled
Phase C — Personal Data Product Workflow
- Add project_type
- Add project_goal
- Add deliverables
- Add project completion state
- Add Analysis stage
- Add Data Modeling stage
- Add KPI stage
- Add BI / Dashboard stage
- Add Documentation stage
- Add Portfolio export / project package
Phase D — Local AI
- AI provider abstraction
- Offline-mode routing
- Local LLM provider
- Local mentor
- Local document retrieval
- Local RAG
Phase E — Secure Work Hardening
Follow SECURITY_ROADMAP.md.
Key priorities:
- authentication
- authorization
- tenant isolation
- organization policy
- encrypted storage
- audit
- network controls
- threat model
17. Product Definition
DataPilot should evolve toward:
An AI-assisted workspace that guides junior data professionals from raw data
to a validated, documented, and deliverable data product while helping them
become increasingly independent.