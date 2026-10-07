from __future__ import annotations

from backend.app.models import (
    DataQualityFinding,
    Workspace,
    WorkspaceLearningLoop,
)


ISSUE_SUPERVISOR_POLICIES: dict[str, dict] = {
    "missing_values": {
        "objective": (
            "Understand whether missingness is material and patterned before "
            "choosing any treatment."
        ),
        "minimum_evidence": (
            "magnitude",
            "subset_pattern",
            "baseline_comparison",
        ),
        "max_targeted_pattern_checks": 1,
        "exit_phase": "decide",
        "stop_rule": (
            "After one justified pattern comparison has both a missing-subset "
            "distribution and an overall baseline, stop opening new columns. "
            "Interpret that evidence, then move to a treatment decision."
        ),
    },
    "duplicate_rows": {
        "objective": (
            "Determine whether repeated rows violate the intended grain before "
            "removing anything."
        ),
        "minimum_evidence": (
            "duplicate_count",
            "grain_or_key_check",
        ),
        "max_targeted_pattern_checks": 1,
        "exit_phase": "decide",
        "stop_rule": (
            "Once duplicate magnitude and grain/key meaning are established, "
            "do not keep searching unrelated columns; decide the dedupe rule."
        ),
    },
    "data_type_issue": {
        "objective": (
            "Establish the semantic type and risky values before conversion."
        ),
        "minimum_evidence": (
            "current_type",
            "problem_examples",
            "intended_semantic_type",
        ),
        "max_targeted_pattern_checks": 1,
        "exit_phase": "decide",
        "stop_rule": (
            "Once type, problematic examples and intended semantic use are "
            "clear, stop exploring and choose a conversion policy."
        ),
    },
    "suspicious_values": {
        "objective": (
            "Decide whether unusual values are plausible observations or data "
            "quality defects."
        ),
        "minimum_evidence": (
            "suspicious_range_or_examples",
            "distribution_context",
        ),
        "max_targeted_pattern_checks": 1,
        "exit_phase": "decide",
        "stop_rule": (
            "After one justified context/distribution check, do not keep trying "
            "more columns unless the evidence is contradictory."
        ),
    },
    "schema_issue": {
        "objective": (
            "Resolve the schema mismatch without breaking downstream contracts."
        ),
        "minimum_evidence": (
            "current_schema",
            "expected_contract",
        ),
        "max_targeted_pattern_checks": 1,
        "exit_phase": "decide",
        "stop_rule": (
            "Once current and expected schema are known, decide the smallest "
            "compatible correction."
        ),
    },
}


STAGE_SUPERVISOR_POLICIES: dict[str, dict] = {
    "source": {
        "objective": "Understand the raw source before changing it.",
        "exit_gate": (
            "Profile and data-quality findings are available; raw source remains immutable."
        ),
        "next_stage": "prepare",
    },
    "prepare": {
        "objective": (
            "Resolve or consciously accept data-quality issues with replayable "
            "transformations and trusted validation."
        ),
        "exit_gate": (
            "Required findings have decisions, replayable operations and validation."
        ),
        "next_stage": "data_model",
    },
    "data_model": {
        "objective": "Lock grain, keys, relationships and semantic structure.",
        "exit_gate": "Fact grain and relationships are coherent and validated.",
        "next_stage": "kpis",
    },
    "kpis": {
        "objective": "Define business measures with correct aggregation semantics.",
        "exit_gate": "Required KPIs have justified formulas and aggregation behavior.",
        "next_stage": "bi_dataset",
    },
    "bi_dataset": {
        "objective": "Confirm the semantic model exposed to analysis.",
        "exit_gate": "Model fields and measures are ready for analysis.",
        "next_stage": "analysis",
    },
    "analysis": {
        "objective": "Answer concrete analytical questions from the semantic model.",
        "exit_gate": "Key analyses are saved and interpretable.",
        "next_stage": "dashboard",
    },
    "dashboard": {
        "objective": "Communicate validated KPIs and analyses clearly.",
        "exit_gate": "Dashboard supports the intended decisions and filters correctly.",
        "next_stage": "insights",
    },
    "insights": {
        "objective": "Convert analytical results into defensible insights.",
        "exit_gate": "Insights are tied to actual analysis evidence.",
        "next_stage": "docs",
    },
    "docs": {
        "objective": "Document the project, decisions and evidence for handoff.",
        "exit_gate": "Project decisions, validation and outputs are documented.",
        "next_stage": None,
    },
}


def _profile_columns(profile: dict) -> list[str]:
    columns = profile.get("columns")
    if not isinstance(columns, list):
        return []
    return [
        str(item)
        for item in columns
        if isinstance(item, str)
    ]


def select_pattern_comparison_column(
    *,
    profile: dict,
    target_name: str | None,
) -> str | None:
    """
    Dataset-agnostic comparison-column selection.

    Prefer low-cardinality categorical/boolean fields. Numeric fields are only
    used when they are genuinely low-cardinality. Column names never imply
    business meaning.
    """
    columns = _profile_columns(profile)
    data_types = profile.get("data_types")
    distinct_counts = profile.get("distinct_counts")
    row_count = int(profile.get("row_count") or 0)

    if not isinstance(data_types, dict):
        data_types = {}
    if not isinstance(distinct_counts, dict):
        distinct_counts = {}

    categorical: list[tuple[int, int, str]] = []
    numeric: list[tuple[int, int, str]] = []

    max_reasonable = min(
        30,
        max(
            8,
            int((row_count or 64) ** 0.5),
        ),
    )

    for index, column in enumerate(columns):
        if column == target_name:
            continue

        distinct = distinct_counts.get(column)
        if not isinstance(distinct, int):
            continue
        if distinct < 2 or distinct > max_reasonable:
            continue

        dtype = str(
            data_types.get(column)
            or ""
        ).casefold()

        if any(
            token in dtype
            for token in (
                "object",
                "string",
                "category",
                "bool",
            )
        ):
            categorical.append(
                (distinct, index, column)
            )
            continue

        if (
            any(
                token in dtype
                for token in (
                    "int",
                    "float",
                    "number",
                )
            )
            and distinct <= 12
        ):
            numeric.append(
                (distinct, index, column)
            )

    pool = categorical or numeric
    if not pool:
        return None

    pool.sort(
        key=lambda item: (
            item[0],
            item[1],
        )
    )

    return pool[0][2]


def _missing_value_evidence(
    *,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    profile: dict,
) -> dict:
    target = finding.column
    row_count = profile.get("row_count")
    null_counts = profile.get("null_counts")

    missing_count = None
    missing_rate = None

    if (
        isinstance(null_counts, dict)
        and target in null_counts
        and isinstance(null_counts.get(target), int)
    ):
        missing_count = int(
            null_counts[target]
        )

    if (
        isinstance(row_count, int)
        and row_count > 0
        and isinstance(missing_count, int)
    ):
        missing_rate = round(
            missing_count / row_count,
            6,
        )

    investigation = (
        loop.active_investigation
        if isinstance(
            loop.active_investigation,
            dict,
        )
        else {}
    )

    subset_output = investigation.get(
        "subset_output"
    )
    baseline_output = investigation.get(
        "baseline_output"
    )

    return {
        "magnitude": {
            "complete": (
                missing_count is not None
                and isinstance(row_count, int)
            ),
            "row_count": row_count,
            "missing_count": missing_count,
            "missing_rate": missing_rate,
        },
        "subset_pattern": {
            "complete": bool(subset_output),
            "comparison_column":
                investigation.get(
                    "comparison_column"
                ),
            "output": subset_output,
        },
        "baseline_comparison": {
            "complete": bool(baseline_output),
            "comparison_column":
                investigation.get(
                    "comparison_column"
                ),
            "output": baseline_output,
        },
    }


def _generic_issue_evidence(
    *,
    finding: DataQualityFinding,
    profile: dict,
) -> dict:
    return {
        "trusted_finding": {
            "complete": bool(
                finding.observation
            ),
            "observation":
                finding.observation,
        },
        "profile_available": {
            "complete": bool(profile),
        },
    }


def build_issue_supervisor_context(
    *,
    loop: WorkspaceLearningLoop,
    finding: DataQualityFinding,
    profile: dict,
    execution_diagnosis: dict | None = None,
) -> dict:
    policy = ISSUE_SUPERVISOR_POLICIES.get(
        finding.issue_type,
        {
            "objective": (
                "Gather only the minimum evidence required before acting."
            ),
            "minimum_evidence": (),
            "max_targeted_pattern_checks": 1,
            "exit_phase": "decide",
            "stop_rule": (
                "Do not keep exploring once the current phase has enough evidence."
            ),
        },
    )

    if finding.issue_type == "missing_values":
        evidence = _missing_value_evidence(
            loop=loop,
            finding=finding,
            profile=profile,
        )
    else:
        evidence = _generic_issue_evidence(
            finding=finding,
            profile=profile,
        )

    required = list(
        policy.get(
            "minimum_evidence",
            (),
        )
    )

    completed = [
        key
        for key in required
        if isinstance(
            evidence.get(key),
            dict,
        )
        and evidence[key].get(
            "complete"
        ) is True
    ]

    missing = [
        key
        for key in required
        if key not in completed
    ]

    investigation = (
        loop.active_investigation
        if isinstance(
            loop.active_investigation,
            dict,
        )
        else {}
    )

    used_checks = (
        1
        if investigation
        else 0
    )

    max_checks = int(
        policy.get(
            "max_targeted_pattern_checks",
            1,
        )
    )

    external_evidence_complete = (
        bool(required)
        and not missing
    )

    recommended_investigation = None

    if (
        finding.issue_type == "missing_values"
        and loop.current_phase in {
            "observe",
            "reason",
        }
        and not investigation
        and used_checks < max_checks
    ):
        comparison = (
            select_pattern_comparison_column(
                profile=profile,
                target_name=finding.column,
            )
        )

        if comparison is not None:
            recommended_investigation = {
                "kind":
                    "missingness_pattern_frequency",
                "target_column":
                    finding.column,
                "comparison_column":
                    comparison,
                "why": (
                    "Use one low-cardinality field to test whether missingness "
                    "is concentrated; compare the missing subset with the overall baseline."
                ),
            }

    if loop.current_phase == "reason":
        if external_evidence_complete:
            status = "interpret_then_exit_reason"
            next_objective = (
                "Interpret the collected evidence. Do not inspect another column. "
                "If the interpretation is defensible, move to the decision phase."
            )
            stop_exploration = True
        else:
            status = "collect_minimum_reasoning_evidence"
            next_objective = (
                "Collect only the remaining minimum evidence for this issue."
            )
            stop_exploration = (
                used_checks >= max_checks
                and bool(investigation)
            )
    elif loop.current_phase == "observe":
        status = "establish_scope"
        next_objective = (
            "Confirm trusted scope and magnitude, then enter reasoning."
        )
        stop_exploration = False
    elif loop.current_phase == "decide":
        status = "make_evidence_based_decision"
        next_objective = (
            "Choose the treatment/rule from the evidence already collected; "
            "do not restart exploration."
        )
        stop_exploration = True
    elif loop.current_phase in {
        "implement",
        "validate",
    }:
        status = "apply_and_validate"
        next_objective = (
            "Implement the chosen rule in working data and validate it with trusted evidence."
        )
        stop_exploration = True
    elif loop.current_phase == "explain":
        status = "explain_completed_work"
        next_objective = (
            "Explain the decision and validation; do not open a new investigation."
        )
        stop_exploration = True
    else:
        status = "completed"
        next_objective = (
            "This issue learning loop is complete."
        )
        stop_exploration = True

    blocker = None
    if (
        isinstance(execution_diagnosis, dict)
        and execution_diagnosis.get(
            "status"
        )
        in {
            "error",
            "wrong_context",
            "premature_action",
            "logic_mismatch",
            "off_task",
        }
    ):
        blocker = {
            "status":
                execution_diagnosis.get(
                    "status"
                ),
            "issue_code":
                execution_diagnosis.get(
                    "issue_code"
                ),
        }

    result = {
        "version": "v3",
        "scope": "issue",
        "issue_type": finding.issue_type,
        "target_name": finding.column,
        "objective":
            policy.get("objective"),
        "current_phase":
            loop.current_phase,
        "status": status,
        "minimum_evidence": required,
        "evidence": evidence,
        "completed_evidence": completed,
        "missing_evidence": missing,
        "external_evidence_complete":
            external_evidence_complete,
        "exploration_budget": {
            "max_targeted_checks":
                max_checks,
            "used_targeted_checks":
                used_checks,
            "remaining_targeted_checks":
                max(
                    0,
                    max_checks - used_checks,
                ),
        },
        "stop_exploration":
            stop_exploration,
        "stop_rule":
            policy.get("stop_rule"),
        "recommended_investigation":
            recommended_investigation,
        "next_objective":
            next_objective,
        "exit_gate": {
            "target_phase":
                policy.get(
                    "exit_phase",
                    "decide",
                ),
            "external_evidence_ready":
                external_evidence_complete,
            "requires_learner_reasoning":
                loop.current_phase
                == "reason",
        },
        "blocker": blocker,
    }

    loop.supervisor_state = {
        "version": "v3",
        "issue_type": finding.issue_type,
        "status": status,
        "completed_evidence": completed,
        "missing_evidence": missing,
        "stop_exploration":
            stop_exploration,
        "next_objective":
            next_objective,
    }

    return result


def build_workspace_supervisor_context(
    *,
    workspace: Workspace,
    ui_context: dict | None,
) -> dict:
    active_stage = (
        (ui_context or {}).get(
            "active_workspace_stage"
        )
        or "source"
    )

    policy = STAGE_SUPERVISOR_POLICIES.get(
        active_stage,
        {
            "objective": (
                "Complete the current stage with evidence before moving on."
            ),
            "exit_gate": (
                "Current stage evidence is complete."
            ),
            "next_stage": None,
        },
    )

    progress = {
        "dataset_profile_ready":
            workspace.dataset_profile
            is not None,
        "data_quality_analysis_ready":
            workspace.dataset_analysis
            is not None,
        "validation_available":
            workspace.validation_result
            is not None,
        "processed_dataset_ready":
            workspace.active_processed_dataset_id
            is not None,
        "data_model_started":
            workspace.data_model_studio
            is not None,
        "saved_kpi_count":
            len(
                workspace.kpi_definitions
                or []
            ),
        "analysis_result_count":
            len(
                workspace.analysis_results
                or []
            ),
    }

    return {
        "version": "v3",
        "scope": "project_stage",
        "active_stage": active_stage,
        "objective":
            policy["objective"],
        "exit_gate":
            policy["exit_gate"],
        "next_stage":
            policy["next_stage"],
        "known_progress": progress,
        "principle": (
            "Advance when the stage exit gate is met; do not keep collecting "
            "extra evidence merely because more checks are possible."
        ),
    }
