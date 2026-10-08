from pydantic import ValidationError
import pytest

from backend.app.models import ProjectMentorSetup, Workspace, WorkspaceCreateRequest


def test_project_mentor_setup_request_accepts_preferences():
    request = WorkspaceCreateRequest(
        learner_id="demo-learner",
        title="Flight Delays",
        usage_context="personal",
        mentor_setup={
            "intent": "practice",
            "experience_level": "intermediate",
            "approach": "guided",
            "learning_focus": ["python", "sql", "quality"],
        },
    )
    assert request.mentor_setup.intent == "practice"
    assert request.mentor_setup.learning_focus == ["python", "sql", "quality"]


def test_project_mentor_setup_rejects_unknown_preferences():
    with pytest.raises(ValidationError):
        ProjectMentorSetup(intent="unknown")


def test_older_workspace_without_mentor_setup_remains_valid():
    workspace = Workspace(
        workspace_id="legacy-workspace",
        learner_id="demo-learner",
        title="Existing Project",
        workspace_type="data_engineering",
    )
    assert workspace.mentor_setup is None
    assert Workspace.model_validate(workspace.model_dump()).mentor_setup is None


def test_workspace_mentor_setup_survives_serialization():
    workspace = Workspace(
        workspace_id="flight-project",
        learner_id="demo-learner",
        title="Flight Delays",
        workspace_type="data_engineering",
        usage_context="personal",
        mentor_setup=ProjectMentorSetup(
            intent="learning",
            experience_level="beginner",
            approach="balanced",
            learning_focus=["pipelines", "modeling"],
        ),
    )
    restored = Workspace.model_validate(workspace.model_dump())
    assert restored.mentor_setup == workspace.mentor_setup
