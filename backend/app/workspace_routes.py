import uuid
from io import BytesIO
from fastapi import APIRouter, HTTPException, UploadFile

import backend.app.database as database

from backend.app.models import (
    Workspace,
    WorkspaceCreateRequest,
    WorkspaceCheckpointUpdateRequest,
    WorkspaceResumeResponse,
    WorkspaceStatusUpdateRequest,
    WorkspaceExecutionPlanRequest,
    WorkspaceExecutionPlanResponse,
    WorkspaceWorkingDataResponse,
)

import pandas as pd



from backend.app.data_profile_service import build_data_profile
from backend.app.data_ai_service import generate_data_recommendations
from backend.app.workspace_plan_service import (
    generate_workspace_execution_plan,
)

from backend.app.workspace_data_service import (
    save_workspace_dataset,
    load_workspace_working_dataframe,
    dataframe_to_records,
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
        usage_context=request.usage_context,
        data_sensitivity=request.data_sensitivity,
        task_brief=request.task_brief,
        desired_outcome=request.desired_outcome,
        workflow_type=request.workflow_type,
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


@router.post(
    "/workspaces/{learner_id}/{workspace_id}/plan",
    response_model=WorkspaceExecutionPlanResponse,
)
def create_workspace_execution_plan(
    learner_id: str,
    workspace_id: str,
    request: WorkspaceExecutionPlanRequest,
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

    # Aynı workspace için zaten bir task oluşturulduysa
    # gereksiz yere ikinci bir task üretmeyelim.
    if workspace.current_task_id is not None:
        existing_task = (
            database.get_data_engineering_task(
                task_id=workspace.current_task_id,
                learner_id=learner_id,
            )
        )

        if existing_task is not None:
            return WorkspaceExecutionPlanResponse(
                task=existing_task
            )

    try:
        task = generate_workspace_execution_plan(
            workspace=workspace,
            profile=request.profile,
            findings=request.findings,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    database.save_data_engineering_task(
        learner_id=learner_id,
        task=task,
    )

    workspace.current_task_id = task.task_id

    workspace.checkpoint.completed_items = [
        *workspace.checkpoint.completed_items,
        "Dataset profile",
        "Execution plan created",
    ]

    workspace.checkpoint.current_focus = (
        task.steps[0].title
    )

    workspace.checkpoint.blocked_reason = None
    workspace.checkpoint.last_error = None

    workspace.checkpoint.next_actions = [
        step.title
        for step in task.steps[1:]
    ]

    database.save_workspace(
        workspace=workspace
    )

    return WorkspaceExecutionPlanResponse(
        task=task
    )



@router.post(
    "/workspaces/{learner_id}/{workspace_id}/data/profile"
)
def profile_workspace_data(
    learner_id: str,
    workspace_id: str,
    file: UploadFile,
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

    if file.content_type != "text/csv":
        raise HTTPException(
            status_code=400,
            detail="Yalnızca CSV dosyası yükleyebilirsiniz.",
        )

    try:
        content = file.file.read()

        df = pd.read_csv(
            BytesIO(content)
        )

    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=400,
            detail="CSV dosyası boş.",
        )

    except pd.errors.ParserError:
        raise HTTPException(
            status_code=400,
            detail="CSV dosyası geçersiz veya bozuk.",
        )

    profile = build_data_profile(df)

    analysis = generate_data_recommendations(
        profile
    )

    safe_profile = {
        key: value
        for key, value in profile.items()
        if key != "sample_rows"
    }

    workspace.dataset_filename = file.filename
    workspace.dataset_profile = safe_profile
    workspace.dataset_analysis = analysis

    # Yeni dataset yüklendiyse eski execution plan
    # artık güvenilir olmayabilir.
    workspace.current_task_id = None

    completed_items = [
        item
        for item in workspace.checkpoint.completed_items
        if item != "Execution plan created"
    ]

    if "Dataset profile" not in completed_items:
        completed_items.append("Dataset profile")

    workspace.checkpoint.completed_items = (
        completed_items
    )

    workspace.checkpoint.current_focus = (
        "Review dataset profile and build execution plan"
    )

    workspace.checkpoint.next_actions = [
        "Build execution plan"
    ]

    workspace.checkpoint.blocked_reason = None
    workspace.checkpoint.last_error = None

    save_workspace_dataset(
        workspace_id=workspace_id,
        content=content,
    )

    database.save_workspace(
        workspace=workspace
    )

    return {
        "workspace_id": workspace_id,
        "filename": file.filename,
        "profile": safe_profile,
        "analysis": analysis.model_dump(),
    }

@router.get(
    "/workspaces/{learner_id}/{workspace_id}/data/working",
    response_model=WorkspaceWorkingDataResponse,
)
def get_workspace_working_data(
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

    try:
        df = (
            load_workspace_working_dataframe(
                workspace_id
            )
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    # MVP sırasında browser-side workbench için
    # makul bir sınır koyuyoruz.
    if len(df) > 5000:
        raise HTTPException(
            status_code=413,
            detail=(
                "Bu MVP workbench şu anda "
                "en fazla 5000 satır destekliyor."
            ),
        )

    return WorkspaceWorkingDataResponse(
        columns=df.columns.tolist(),
        row_count=len(df),
        rows=dataframe_to_records(df),
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