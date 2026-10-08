"""Dataset-agnostic, zero-LLM action evidence for workspace mentoring.

Only server-executed results are verified. Browser state and learner messages
must not be promoted to trusted evidence.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

MAX_EVENTS = 80


def record_action_evidence(
    workspace: Any,
    *,
    action: str,
    dataset: str,
    parameters: dict,
    result: dict,
    data_version: str | None = None,
) -> bool:
    """Record a verified backend action, deduplicating identical observations.

    Returns True only if a new record was appended.
    """
    identity = {
        "action": action,
        "dataset": dataset,
        "parameters": parameters,
        "result": result,
        "data_version": data_version,
    }
    fingerprint = hashlib.sha256(
        json.dumps(identity, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()[:24]
    events = list(workspace.action_evidence_events)
    if any(item.get("fingerprint") == fingerprint for item in events):
        return False
    events.append({
        "fingerprint": fingerprint,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "dataset": dataset,
        "parameters": parameters,
        "result": result,
        "data_version": data_version,
        "execution_status": "success",
        "verification_status": "verified",
        "origin": "backend",
    })
    workspace.action_evidence_events = events[-MAX_EVENTS:]
    return True


def concise_action_evidence(workspace: Any, limit: int = 4) -> list[dict]:
    """Bounded evidence for Mentor; no large row payloads or raw data."""
    return [
        {
            "action": item.get("action"),
            "dataset": item.get("dataset"),
            "parameters": item.get("parameters"),
            "result": item.get("result"),
            "verification_status": item.get("verification_status"),
            "data_version": item.get("data_version"),
        }
        for item in workspace.action_evidence_events[-max(0, min(limit, 8)):]
    ]
