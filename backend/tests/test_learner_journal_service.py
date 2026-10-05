import backend.app.database as database

from backend.app.learner_journal_service import (
    add_note,
    edit_note,
    get_journal,
    remove_note,
    save_resume_state,
)
from backend.app.models import (
    LearnerNoteCreateRequest,
    LearnerNoteUpdateRequest,
    LearnerResumePayload,
    LearnerResumeStateUpsertRequest,
)


def _seed(tmp_path):
    database.DATABASE_PATH = (
        tmp_path / "learner_journal.db"
    )
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-journal",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
        preferred_language="en",
    )


def test_resume_state_upserts_and_journal_returns_it(
    tmp_path,
):
    _seed(tmp_path)

    first = save_resume_state(
        learner_id="learner-journal",
        request=LearnerResumeStateUpsertRequest(
            context_type="practice",
            context_key="python:loops",
            state=LearnerResumePayload(
                topic_id="python",
                subtopic_id="loops",
                practice_mode="code",
                difficulty="easy",
                source_id="exercism-python",
                source_exercise_id="binary-search",
            ),
        ),
    )

    assert first.state.source_exercise_id == (
        "binary-search"
    )

    save_resume_state(
        learner_id="learner-journal",
        request=LearnerResumeStateUpsertRequest(
            context_type="practice",
            context_key="python:loops",
            state=LearnerResumePayload(
                topic_id="python",
                subtopic_id="loops",
                practice_mode="code",
                difficulty="medium",
                source_id="exercism-python",
                source_exercise_id="eliuds-eggs",
            ),
        ),
    )

    journal = get_journal(
        learner_id="learner-journal",
        context_type="practice",
        context_key="python:loops",
    )

    assert journal.resume_state is not None
    assert (
        journal.resume_state.state.difficulty
        == "medium"
    )
    assert (
        journal.resume_state.state.source_exercise_id
        == "eliuds-eggs"
    )


def test_notes_are_persistent_and_scoped(
    tmp_path,
):
    _seed(tmp_path)

    note = add_note(
        learner_id="learner-journal",
        request=LearnerNoteCreateRequest(
            context_type="practice",
            context_key="python:loops",
            title="Loop reminder",
            body=(
                "enumerate gives index and value."
            ),
            source_exercise_id="binary-search",
        ),
    )

    add_note(
        learner_id="learner-journal",
        request=LearnerNoteCreateRequest(
            context_type="workspace",
            context_key="workspace-001",
            title="Validation",
            body="Compare row count before and after.",
        ),
    )

    practice_journal = get_journal(
        learner_id="learner-journal",
        context_type="practice",
        context_key="python:loops",
    )

    assert len(practice_journal.notes) == 1
    assert practice_journal.notes[0].note_id == (
        note.note_id
    )
    assert practice_journal.notes[0].body == (
        "enumerate gives index and value."
    )


def test_note_can_be_edited_and_deleted(
    tmp_path,
):
    _seed(tmp_path)

    note = add_note(
        learner_id="learner-journal",
        request=LearnerNoteCreateRequest(
            context_type="practice",
            context_key="python:loops",
            body="Old note",
        ),
    )

    updated = edit_note(
        learner_id="learner-journal",
        note_id=note.note_id,
        request=LearnerNoteUpdateRequest(
            title="Updated",
            body="New note",
        ),
    )

    assert updated is not None
    assert updated.title == "Updated"
    assert updated.body == "New note"

    assert remove_note(
        learner_id="learner-journal",
        note_id=note.note_id,
    ) is True

    journal = get_journal(
        learner_id="learner-journal",
        context_type="practice",
        context_key="python:loops",
    )

    assert journal.notes == []


def test_same_journal_feature_supports_workspace_context(
    tmp_path,
):
    _seed(tmp_path)

    save_resume_state(
        learner_id="learner-journal",
        request=LearnerResumeStateUpsertRequest(
            context_type="workspace",
            context_key="workspace-001",
            state=LearnerResumePayload(
                workspace_id="workspace-001",
                stage="prepare",
                current_view="workbench",
            ),
        ),
    )

    add_note(
        learner_id="learner-journal",
        request=LearnerNoteCreateRequest(
            context_type="workspace",
            context_key="workspace-001",
            body=(
                "Check schema after type conversion."
            ),
        ),
    )

    journal = get_journal(
        learner_id="learner-journal",
        context_type="workspace",
        context_key="workspace-001",
    )

    assert journal.resume_state is not None
    assert (
        journal.resume_state.state.current_view
        == "workbench"
    )
    assert len(journal.notes) == 1
