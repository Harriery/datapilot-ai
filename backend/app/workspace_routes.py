import uuid

from fastapi import APIRouter, HTTPException

import backend.app.database as database

from backend.app.models import (
    Workspace,
    WorkspaceCreateRequest,
    WorkspaceCheckpointUpdateRequest,
    WorkspaceResumeResponse,
    WorkspaceStatusUpdateRequest,
)


router = APIRouter()


@router.post(
    "/workspaces",
    response_model=Workspace,
)
def create_workspace(
    request: WorkspaceCreateRequest,
):
    learner = database.get_learner_profile_by_id(
        request.learner_id
    )

    if learner is None:
        raise HTTPException(
            status_code=404,
            detail="Learner bulunamadı.",
        )

    workspace_id = str(uuid.uuid4())
    mentor_session_id = str(uuid.uuid4())

    # Her workspace kendi mentor konuşma geçmişine
    # sahip olsun.
    database.insert_session(
        mentor_session_id
    )

    workspace = Workspace(
        workspace_id=workspace_id,
        learner_id=request.learner_id,
        title=request.title,
        workspace_type=request.workspace_type,
        current_task_id=request.current_task_id,
        mentor_session_id=mentor_session_id,
    )

    database.save_workspace(
        workspace=workspace
    )

    return workspace


@router.get(
    "/workspaces/{learner_id}",
    response_model=list[Workspace],
)
def list_workspaces(
    learner_id: str,
):
    learner = database.get_learner_profile_by_id(
        learner_id
    )

    if learner is None:
        raise HTTPException(
            status_code=404,
            detail="Learner bulunamadı.",
        )

    return database.get_workspaces_by_learner(
        learner_id=learner_id
    )


@router.get(
    "/workspaces/{learner_id}/{workspace_id}",
    response_model=Workspace,
)
def get_workspace(
    learner_id: str,
    workspace_id: str,
):
    workspace = database.get_workspace(
        workspace_id=workspace_id,
        learner_id=learner_id,
    )

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace bulunamadı.",
        )

    return workspace

@router.put(
    "/workspaces/{learner_id}/{workspace_id}/checkpoint",
    response_model=Workspace,
)
def update_workspace_checkpoint(
    learner_id: str,
    workspace_id: str,
    request: WorkspaceCheckpointUpdateRequest,
):
    workspace = database.get_workspace(
        workspace_id=workspace_id,
        learner_id=learner_id,
    )

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace bulunamadı.",
        )

    workspace.checkpoint = request.checkpoint

    database.save_workspace(
        workspace=workspace
    )

    return workspace


@router.get(
    "/workspaces/{learner_id}/{workspace_id}/resume",
    response_model=WorkspaceResumeResponse,
)
def resume_workspace(
    learner_id: str,
    workspace_id: str,
):
    workspace = database.get_workspace(
        workspace_id=workspace_id,
        learner_id=learner_id,
    )

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace bulunamadı.",
        )

    next_action = None

    if workspace.checkpoint.next_actions:
        next_action = (
            workspace.checkpoint.next_actions[0]
        )

    return WorkspaceResumeResponse(
        workspace_id=workspace.workspace_id,
        title=workspace.title,
        status=workspace.status,
        checkpoint=workspace.checkpoint,
        next_action=next_action,
    )

@router.put(
    "/workspaces/{learner_id}/{workspace_id}/status",
    response_model=Workspace,
)
def update_workspace_status(
    learner_id: str,
    workspace_id: str,
    request: WorkspaceStatusUpdateRequest,
):
    workspace = database.get_workspace(
        workspace_id=workspace_id,
        learner_id=learner_id,
    )

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace bulunamadı.",
        )

    workspace.status = request.status

    database.save_workspace(
        workspace=workspace
    )

    return workspace