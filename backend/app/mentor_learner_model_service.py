from __future__ import annotations

import json
from collections import Counter

import backend.app.database as database
from backend.app.progress_service import (
    get_learner_progress,
)


def _context_from_row(row) -> dict:
    try:
        raw = row["context_json"]
    except Exception:
        return {}

    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}

    return parsed if isinstance(parsed, dict) else {}


def build_learner_snapshot(
    *,
    learner_id: str,
    skill_name: str,
) -> dict:
    progress = get_learner_progress(
        learner_id=learner_id
    )

    skill = next(
        (
            item
            for item in progress.skills
            if item.skill_name == skill_name
        ),
        None,
    )

    evidence = database.get_learning_evidence_by_skill(
        learner_id=learner_id,
        skill_name=skill_name,
    )

    misconception_counts: Counter[str] = Counter()

    for item in evidence:
        misconception = _context_from_row(
            item
        ).get("misconception")

        if (
            isinstance(misconception, str)
            and misconception.strip()
        ):
            misconception_counts[
                misconception
            ] += 1

    recurring = [
        {"code": code, "count": count}
        for code, count
        in misconception_counts.most_common(5)
    ]

    if skill is None:
        return {
            "skill_name": skill_name,
            "status": "new",
            "attempts": 0,
            "success_rate": 0.0,
            "independence_trend": "insufficient_data",
            "independence_score": 0,
            "practice_priority": "high",
            "recurring_misconceptions": recurring,
        }

    return {
        "skill_name": skill.skill_name,
        "status": skill.status,
        "attempts": skill.attempts,
        "success_rate": skill.success_rate,
        "last_assistance_level": skill.last_assistance_level,
        "independence_trend": skill.independence_trend,
        "independence_score": skill.independence_score,
        "practice_priority": skill.practice_priority,
        "recurring_misconceptions": recurring,
    }


def has_execution_observation(
    *,
    learner_id: str,
    skill_name: str,
    observation_id: str,
) -> bool:
    if not observation_id:
        return True

    evidence = database.get_learning_evidence_by_skill(
        learner_id=learner_id,
        skill_name=skill_name,
    )

    for item in evidence:
        context = _context_from_row(item)
        metadata = context.get("metadata")

        if (
            isinstance(metadata, dict)
            and metadata.get(
                "execution_observation_id"
            )
            == observation_id
        ):
            return True

    return False


def record_execution_signal(
    *,
    learner_id: str,
    workspace_id: str,
    skill_name: str,
    phase: str,
    assistance_level: str,
    diagnosis: dict | None,
) -> None:
    if not diagnosis:
        return

    misconception = diagnosis.get(
        "misconception"
    )
    observation_id = str(
        diagnosis.get("observation_id")
        or ""
    )

    if (
        not misconception
        or has_execution_observation(
            learner_id=learner_id,
            skill_name=skill_name,
            observation_id=observation_id,
        )
    ):
        return

    database.record_observed_learning_signal(
        learner_id=learner_id,
        skill_name=skill_name,
        assistance_level=assistance_level,
        success=False,
        evidence_type="debugging",
        note=str(
            diagnosis.get("message")
            or diagnosis.get("issue_code")
            or "Notebook execution issue."
        )[:500],
        context={
            "workspace_id": workspace_id,
            "stage": "prepare",
            "learning_phase": phase,
            "task_type": "notebook_execution",
            "target_type": "code",
            "target_name": diagnosis.get("cell_id"),
            "user_authored": True,
            "deterministic_validation": True,
            "misconception": misconception,
            "metadata": {
                "origin": "mentor_execution_observer",
                "execution_observation_id": observation_id,
                "issue_code": diagnosis.get("issue_code"),
                "practice_tags": diagnosis.get("practice_tags", []),
            },
        },
    )
