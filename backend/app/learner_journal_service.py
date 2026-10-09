from __future__ import annotations

import backend.app.database as database

from backend.app.models import (
    LearnerJournalResponse,
    LearnerNote,
    LearnerNoteCreateRequest,
    LearnerNoteUpdateRequest,
    LearnerResumeState,
    LearnerResumeStateUpsertRequest,
)


def save_resume_state(
    *,
    learner_id: str,
    request: LearnerResumeStateUpsertRequest,
) -> LearnerResumeState:
    return database.upsert_learner_resume_state(
        learner_id=learner_id,
        context_type=request.context_type,
        context_key=request.context_key,
        state=request.state,
    )


def add_note(
    *,
    learner_id: str,
    request: LearnerNoteCreateRequest,
) -> LearnerNote:
    return database.create_learner_note(
        learner_id=learner_id,
        context_type=request.context_type,
        context_key=request.context_key,
        title=request.title,
        body=request.body,
        source_exercise_id=(
            request.source_exercise_id
        ),
    )


def edit_note(
    *,
    learner_id: str,
    note_id: str,
    request: LearnerNoteUpdateRequest,
) -> LearnerNote | None:
    return database.update_learner_note(
        learner_id=learner_id,
        note_id=note_id,
        title=request.title,
        body=request.body,
    )


def remove_note(
    *,
    learner_id: str,
    note_id: str,
) -> bool:
    return database.delete_learner_note(
        learner_id=learner_id,
        note_id=note_id,
    )


def get_journal(
    *,
    learner_id: str,
    context_type: str,
    context_key: str,
) -> LearnerJournalResponse:
    return LearnerJournalResponse(
        learner_id=learner_id,
        context_type=context_type,
        context_key=context_key,
        resume_state=(
            database.get_learner_resume_state(
                learner_id=learner_id,
                context_type=context_type,
                context_key=context_key,
            )
        ),
        notes=database.list_learner_notes(
            learner_id=learner_id,
            context_type=context_type,
            context_key=context_key,
        ),
    )
