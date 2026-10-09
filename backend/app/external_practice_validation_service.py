from __future__ import annotations

import hashlib
from uuid import uuid4

import backend.app.database as database

from backend.app.models import (
    ExternalPracticeValidationEvent,
    ExternalPracticeValidationEventRequest,
)


def record_client_validation_event(
    *,
    request: ExternalPracticeValidationEventRequest,
) -> ExternalPracticeValidationEvent:
    solution_hash = hashlib.sha256(
        request.answer.encode("utf-8")
    ).hexdigest()

    event = ExternalPracticeValidationEvent(
        event_id=str(uuid4()),
        learner_id=request.learner_id,
        source_id=request.source_id,
        source_exercise_id=request.source_exercise_id,
        topic_id=request.topic_id,
        subtopic_id=request.subtopic_id,
        practice_mode=request.practice_mode,
        difficulty=request.difficulty,
        content_hash=request.content_hash,
        validation_bundle_hash=(
            request.validation_bundle_hash
        ),
        solution_hash=solution_hash,
        client_reported_success=(
            request.client_reported_success
        ),
        tests_run=request.tests_run,
        trust_level="client_sandbox",
    )

    return database.record_external_practice_validation_event(
        event=event
    )
