from __future__ import annotations

"""
Dataset-agnostic Data Engineering reasoning playbooks for Mentor V2.
"""

PLAYBOOKS: dict[str, dict] = {
    "missing_values": {
        "skill": "null_analysis",
        "principles": [
            "Do not choose fill/drop/zero before understanding missingness.",
            "Separate raw-source investigation from working-data validation.",
            "Treat column names as hints, not business semantics.",
        ],
        "phases": {
            "observe": {
                "goal": "Confirm the target, missing count/rate, and raw scope.",
                "evidence": ["target column", "missing count", "raw rows visible"],
                "avoid": ["imputation", "deletion", "business-rule assumptions"],
            },
            "reason": {
                "goal": "Test whether missingness shows a pattern and what evidence could explain it.",
                "evidence": ["pattern check by relevant existing attributes", "raw-data context"],
                "avoid": ["arbitrary grouping", "mean/median/mode recommendation", "causal claims from names"],
            },
            "decide": {
                "goal": "Choose keep/fill/derive/drop/flag only after evidence is sufficient.",
                "evidence": ["reason for treatment", "expected impact"],
                "avoid": ["default fill rule", "unjustified row deletion"],
            },
            "implement": {
                "goal": "Apply the smallest replayable transformation to working data.",
                "evidence": ["explicit operation", "replayable pipeline step"],
                "avoid": ["mutating raw source", "hidden notebook-only transformation"],
            },
            "validate": {
                "goal": "Confirm intended null change without unintended row/schema damage.",
                "evidence": ["null count", "row count", "schema", "pipeline replay"],
                "avoid": ["success based only on code running"],
            },
            "explain": {
                "goal": "Explain what changed, why, and which evidence proves it.",
                "evidence": ["decision rationale", "validation evidence"],
                "avoid": ["generic explanation disconnected from result"],
            },
        },
    },
    "duplicate_rows": {
        "skill": "duplicate_analysis",
        "principles": [
            "Duplicate-looking rows are not automatically invalid duplicates.",
            "Confirm grain and key semantics before removing rows.",
        ],
        "phases": {
            "observe": {"goal": "Confirm duplicate count and affected rows.", "evidence": ["duplicate count", "examples"], "avoid": ["immediate drop_duplicates"]},
            "reason": {"goal": "Determine whether repeats violate intended grain.", "evidence": ["candidate key/grain", "differing attributes"], "avoid": ["assuming identical means invalid"]},
            "decide": {"goal": "Choose keep/deduplicate/consolidate with a key-based reason.", "evidence": ["dedupe rule"], "avoid": ["blanket deletion"]},
            "implement": {"goal": "Apply a deterministic dedupe rule.", "evidence": ["operation"], "avoid": ["untracked row removal"]},
            "validate": {"goal": "Confirm expected duplicate reduction and row loss.", "evidence": ["before/after rows", "duplicate count"], "avoid": ["code-ran-only validation"]},
            "explain": {"goal": "Explain the grain rule and validation.", "evidence": ["reason", "result"], "avoid": []},
        },
    },
    "data_type_issue": {
        "skill": "data_type_analysis",
        "principles": ["Type conversion can create nulls or semantic corruption."],
        "phases": {
            "observe": {"goal": "Confirm current/inferred type and problematic values.", "evidence": ["type", "examples"], "avoid": ["blind conversion"]},
            "reason": {"goal": "Determine intended semantic type.", "evidence": ["value patterns", "downstream use"], "avoid": ["name-only inference"]},
            "decide": {"goal": "Choose conversion/coercion policy.", "evidence": ["invalid-value policy"], "avoid": ["silent coercion"]},
            "implement": {"goal": "Apply replayable conversion.", "evidence": ["operation"], "avoid": []},
            "validate": {"goal": "Compare nulls, schema and representative values.", "evidence": ["before/after nulls", "type"], "avoid": []},
            "explain": {"goal": "Explain semantic type and conversion safety.", "evidence": ["reason", "validation"], "avoid": []},
        },
    },
    "suspicious_values": {
        "skill": "suspicious_value_analysis",
        "principles": ["Outlier-looking values are not automatically errors."],
        "phases": {
            "observe": {"goal": "Confirm suspicious range/examples.", "evidence": ["min/max/examples"], "avoid": ["automatic clipping"]},
            "reason": {"goal": "Check plausibility and pattern.", "evidence": ["distribution/context"], "avoid": ["arbitrary threshold"]},
            "decide": {"goal": "Choose retain/flag/correct/remove with evidence.", "evidence": ["criterion"], "avoid": ["default IQR deletion"]},
            "implement": {"goal": "Apply smallest justified change.", "evidence": ["operation"], "avoid": []},
            "validate": {"goal": "Check distribution and row impact.", "evidence": ["before/after"], "avoid": []},
            "explain": {"goal": "Explain why the suspicious values were handled that way.", "evidence": ["criterion", "result"], "avoid": []},
        },
    },
    "schema_issue": {
        "skill": "schema_analysis",
        "principles": ["Schema fixes must preserve downstream contracts."],
        "phases": {
            "observe": {"goal": "Confirm the schema mismatch.", "evidence": ["expected/current schema"], "avoid": []},
            "reason": {"goal": "Identify likely source/downstream impact.", "evidence": ["consumer expectations"], "avoid": []},
            "decide": {"goal": "Choose a compatible schema correction.", "evidence": ["contract"], "avoid": []},
            "implement": {"goal": "Apply replayable schema change.", "evidence": ["operation"], "avoid": []},
            "validate": {"goal": "Confirm schema and pipeline replay.", "evidence": ["schema", "replay"], "avoid": []},
            "explain": {"goal": "Explain the contract and correction.", "evidence": ["reason", "validation"], "avoid": []},
        },
    },
}


def get_playbook_context(
    issue_type: str,
    phase: str,
) -> dict:
    playbook = PLAYBOOKS.get(issue_type)

    if not playbook:
        return {
            "issue_type": issue_type,
            "phase": phase,
            "goal": "Gather evidence before choosing an action.",
            "principles": [],
            "evidence": [],
            "avoid": [],
        }

    phase_spec = playbook.get("phases", {}).get(
        phase,
        {},
    )

    return {
        "issue_type": issue_type,
        "skill": playbook.get("skill"),
        "phase": phase,
        "goal": phase_spec.get("goal"),
        "principles": playbook.get("principles", []),
        "evidence": phase_spec.get("evidence", []),
        "avoid": phase_spec.get("avoid", []),
    }
