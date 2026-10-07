from __future__ import annotations


STAGE_PLAYBOOKS: dict[str, dict] = {
    "source": {
        "goal": "Establish trustworthy raw-source facts before changing anything.",
        "sequence": [
            "confirm dataset/profile scope",
            "inspect nulls/duplicates/types/suspicious ranges",
            "separate observation from treatment",
        ],
        "evidence_gate": "A claim must be visible in raw/profile evidence.",
        "avoid": ["transforming raw source", "guessing semantics from names"],
    },
    "prepare.profile": {
        "goal": "Turn profile findings into evidence-backed investigation questions.",
        "sequence": [
            "quantify the finding",
            "inspect affected raw rows",
            "identify what evidence would distinguish plausible explanations",
        ],
        "evidence_gate": "Do not choose a treatment before the cause/pattern is investigated.",
        "avoid": ["automatic fill/drop", "business-rule invention"],
    },
    "prepare.workbench": {
        "goal": "Experiment safely, then promote only justified replayable changes.",
        "sequence": [
            "choose raw vs working dataset deliberately",
            "inspect/experiment in notebook when needed",
            "define the smallest transformation",
            "send transformation logic to pipeline",
        ],
        "evidence_gate": "Analysis code and transformation code must be distinguished.",
        "avoid": ["mutating raw", "productionizing exploratory code"],
    },
    "prepare.validate": {
        "goal": "Prove the transformation achieved its purpose without collateral damage.",
        "sequence": [
            "compare before/after target metric",
            "check row count",
            "check schema",
            "check replay/integrity",
            "reconcile warnings",
        ],
        "evidence_gate": "Code running successfully is not validation.",
        "avoid": ["single-metric validation", "ignoring unexpected row loss"],
    },
    "prepare.understand": {
        "goal": "Understand grain, roles and analytical structure before model design.",
        "sequence": [
            "state row grain",
            "identify keys/identifiers",
            "separate measures from attributes",
            "review cardinality and time fields",
            "challenge model-discovery suggestions",
        ],
        "evidence_gate": "Every proposed role should be supported by data semantics/cardinality.",
        "avoid": ["numeric means measure", "high-cardinality means dimension table"],
    },
    "data_model": {
        "goal": "Build a model that preserves grain and supports intended analysis.",
        "sequence": [
            "lock fact grain",
            "choose dimensions for analytical value",
            "define keys and foreign keys",
            "create relationships/cardinality",
            "add justified semantic derivations",
            "review ambiguity/duplication risk",
        ],
        "evidence_gate": "Relationships must respect keys/cardinality and not change fact meaning.",
        "avoid": ["mechanical normalization", "invented dimensions", "grain drift"],
    },
    "kpis": {
        "goal": "Define measures whose aggregation matches business semantics.",
        "sequence": [
            "state the business question",
            "select fact/measure source",
            "check additivity",
            "choose aggregation",
            "add dimension/filter only when meaningful",
            "sanity-check the result",
        ],
        "evidence_gate": "Aggregation must be semantically valid for the measure.",
        "avoid": ["blind SUM", "formula before meaning", "non-additive KPI misuse"],
    },
    "bi_dataset": {
        "goal": "Confirm semantic-model readiness before analysis.",
        "sequence": [
            "review model relationships",
            "review KPI definitions",
            "check semantic/time roles",
            "resolve readiness warnings",
            "confirm model",
        ],
        "evidence_gate": "Required semantic checks must be ready before confirmation.",
        "avoid": ["confirming around unresolved model risks"],
    },
    "analysis": {
        "goal": "Answer one analytical question with a defensible KPI/dimension definition.",
        "sequence": [
            "state the question",
            "choose KPI/measure",
            "choose dimension when needed",
            "choose sort/top-N semantics",
            "inspect plausibility",
            "save only useful analyses",
        ],
        "evidence_gate": "The definition must answer the question, not merely produce a chartable result.",
        "avoid": ["arbitrary Top N", "wrong aggregation", "analysis without a question"],
    },
    "dashboard": {
        "goal": "Communicate validated analyses clearly and interactively.",
        "sequence": [
            "choose visual for analytical relationship",
            "bind measure/dimension",
            "add useful slicers",
            "arrange hierarchy/layout",
            "tune labels/axes/legend",
            "test interactions and readability",
        ],
        "evidence_gate": "Visual encoding must match measure/dimension semantics.",
        "avoid": ["decorative visuals", "non-additive pie totals", "unreadable labels"],
    },
    "insights": {
        "goal": "Turn analyses into evidence-backed findings without inventing causality.",
        "sequence": [
            "identify meaningful result",
            "tie it to analysis evidence",
            "state limitation/uncertainty",
            "confirm only defensible insights",
        ],
        "evidence_gate": "Every insight must trace to an analysis result.",
        "avoid": ["causal claims from correlation", "invented missing context"],
    },
    "docs": {
        "goal": "Produce a handoff that explains validated decisions and outputs.",
        "sequence": [
            "summarize prepared data",
            "document model/KPI decisions",
            "document analyses/dashboard",
            "state validation/limitations",
            "export/complete handoff",
        ],
        "evidence_gate": "Documentation must reflect saved/validated workspace state.",
        "avoid": ["documenting unsaved assumptions"],
    },
    "practice": {
        "goal": "Close diagnosed gaps with targeted exercises until independent evidence improves.",
        "sequence": [
            "select highest-priority diagnosed skill",
            "choose matching focus/mode/difficulty",
            "attempt independently",
            "use hints progressively",
            "record mastery evidence",
        ],
        "evidence_gate": "Practice priority should come from performance/independence/misconceptions.",
        "avoid": ["random practice unrelated to learner gaps"],
    },
    "progress": {
        "goal": "Interpret performance and independence trends, not just raw attempt counts.",
        "sequence": [
            "review success",
            "review assistance/independence",
            "review recurring misconceptions",
            "identify targeted practice priority",
        ],
        "evidence_gate": "Observed signals and assessed attempts must remain distinguishable.",
        "avoid": ["equating many attempts with mastery"],
    },
    "tasks": {
        "goal": "Keep active work, blockers, review and handoff status visible.",
        "sequence": [
            "identify active/blocked task",
            "open relevant workspace",
            "continue from trusted current step",
        ],
        "evidence_gate": "Task status should reflect workspace state.",
        "avoid": ["starting a duplicate task when an active one exists"],
    },
}


def _playbook_for_path(path: str) -> dict | None:
    if path in STAGE_PLAYBOOKS:
        return STAGE_PLAYBOOKS[path]

    parts = path.split(".")
    while len(parts) > 1:
        parts.pop()
        parent = ".".join(parts)
        if parent in STAGE_PLAYBOOKS:
            return STAGE_PLAYBOOKS[parent]

    return None


def get_relevant_stage_playbooks(
    product_context: dict,
) -> list[dict]:
    paths: list[str] = []

    current = product_context.get("current")
    if isinstance(current, dict):
        path = current.get("path")
        if isinstance(path, str):
            paths.append(path)

    for item in product_context.get("referenced", []):
        if isinstance(item, dict):
            path = item.get("path")
            if isinstance(path, str) and path not in paths:
                paths.append(path)

    result = []
    for path in paths:
        playbook = _playbook_for_path(path)
        if playbook is not None:
            result.append({
                "path": path,
                **playbook,
            })

    return result
