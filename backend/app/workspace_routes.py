import uuid
from io import BytesIO
from typing import Literal

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    UploadFile,
    Response,
)

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
    WorkspaceDataPreviewResponse,
    WorkspaceTransformationRequest,
    DataEngineeringTaskTransformationResponse,
    WorkspaceVersionSummary,
    WorkspaceValidationCheck,
    WorkspaceValidationResponse,
    WorkspaceReviewResponse,
    WorkspaceFindingMentorResponse,
    WorkspaceFindingAttemptRequest,
    WorkspaceFindingAttemptResponse,
    LearningEvidenceDecision,
    PersonalProjectAnalysisRequest,
    PersonalProjectAnalysisResult,
    PersonalProjectAnalysisDeleteRequest,
    PersonalProjectKPISelectionRequest,
    PersonalProjectKPIDefinition,
    PersonalProjectDataModelPlan,
    WorkspaceWorkbenchOperation,
    WorkspaceWorkbenchOperationCreateRequest,
    WorkspaceWorkbenchTransformationRequest,
    WorkspaceWorkbenchTransformationResponse,
    WorkspaceDevelopmentSampleRequest,
    WorkspaceDevelopmentSampleResponse,
    WorkspaceFullPipelineResponse,
    PersonalProjectDataModelStudio,
)

import pandas as pd



from backend.app.data_profile_service import build_data_profile
from backend.app.data_ai_service import generate_data_recommendations

from backend.app.workspace_plan_service import (
    generate_workspace_execution_plan,
    generate_local_workspace_execution_plan,
)

from backend.app.workspace_data_service import (
    save_workspace_dataset,
    load_workspace_working_dataframe,
    dataframe_to_records,
    save_workspace_working_dataframe,
    create_workspace_version,
    delete_workspace_version,
    list_workspace_versions,
    load_workspace_version,
    load_workspace_source_dataframe,
    clear_workspace_versions,

)

from backend.app.mentor_service import (
    review_data_engineering_task_transformation,
    get_skill_for_data_quality_issue,
    review_data_quality_attempt,
)

from backend.app.local_data_quality_service import (
    analyze_dataframe_locally,
    merge_data_quality_analyses,
)

from backend.app.data_security_service import (
    evaluate_external_ai_policy,
)

from backend.app.local_data_quality_mentor_service import (
    build_local_mentor_response,
    get_local_assistance_level,
    review_task_transformation_locally,
)

from backend.app.personal_project_service import (
    build_personal_project_deliverables,
    complete_and_advance_personal_project_deliverable,
    reconcile_personal_project_deliverables,
)

from backend.app.personal_analysis_service import (
    build_personal_analysis_plan,
    build_personal_analysis_result,
)

from backend.app.personal_kpi_service import (
    build_personal_kpi_candidates_from_plan,
)

from backend.app.personal_data_model_service import (
    build_personal_data_model_plan,
)

from backend.app.personal_data_model_studio_service import (
    build_personal_data_model_studio,
    validate_personal_data_model_studio,
)

from backend.app.workspace_workbench_service import (
    add_user_workbench_operation,
    complete_workbench_operation,
    get_workbench_operation,
    sync_data_quality_workbench_operations,
)

from backend.app.transformation_validation_service import (
    validate_transformation_for_finding,
)

from backend.app.workspace_pipeline_service import (
    apply_replayable_workbench_pipeline,
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

    project_deliverables = []

    if request.usage_context == "personal":
        project_deliverables = (
            build_personal_project_deliverables(
                request.project_type
            )
        )

    workspace = Workspace(
        workspace_id=workspace_id,
        learner_id=request.learner_id,
        title=request.title,
        usage_context=request.usage_context,
        organization_id=request.organization_id,
        data_sensitivity=request.data_sensitivity,
        task_brief=request.task_brief,
        desired_outcome=request.desired_outcome,
        project_type=request.project_type,
        project_deliverables=project_deliverables,
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

    workspaces = database.get_workspaces_by_learner(
        learner_id=learner_id
    )

    for workspace in workspaces:
        if reconcile_personal_project_deliverables(
            workspace
        ):
            database.save_workspace(
                workspace=workspace
            )

    return workspaces


@router.post(
    "/workspaces/{learner_id}/{workspace_id}/workbench/operations",
    response_model=WorkspaceWorkbenchOperation,
)
def create_workspace_workbench_operation(
    learner_id: str,
    workspace_id: str,
    request: WorkspaceWorkbenchOperationCreateRequest,
):
    workspace = database.get_workspace(
        workspace_id,
        learner_id,
    )

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found.",
        )

    operation = add_user_workbench_operation(
        existing_operations=(
            workspace.workbench_operations
        ),
        request=request,
    )

    if operation.status == "active":
        workspace.workbench_active_operation_id = (
            operation.operation_id
        )

    database.save_workspace(
        workspace=workspace
    )

    return operation



@router.post(
    (
        "/workspaces/{learner_id}/{workspace_id}"
        "/workbench/transform"
    ),
    response_model=(
        WorkspaceWorkbenchTransformationResponse
    ),
)
def transform_workspace_workbench_data(
    learner_id: str,
    workspace_id: str,
    request: WorkspaceWorkbenchTransformationRequest,
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
        operation = get_workbench_operation(
            operations=(
                workspace.workbench_operations
            ),
            operation_id=request.operation_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    if operation.status != "active":
        raise HTTPException(
            status_code=400,
            detail=(
                "Yalnızca aktif Workbench operation "
                "submit edilebilir."
            ),
        )

    try:
        before_df = (
            load_workspace_working_dataframe(
                workspace_id
            )
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    after_df = pd.DataFrame(
        request.after_rows
    )

    if after_df.empty:
        raise HTTPException(
            status_code=400,
            detail=(
                "Transformation dataset içindeki "
                "bütün satırları silemez."
            ),
        )

    missing_source_columns = [
        column
        for column in operation.source_columns
        if column not in before_df.columns
    ]

    if missing_source_columns:
        raise HTTPException(
            status_code=400,
            detail=(
                "Transformation için gerekli source "
                "column bulunamadı: "
                + ", ".join(
                    missing_source_columns
                )
            ),
        )

    missing_expected_columns = [
        column
        for column in operation.expected_columns
        if column not in after_df.columns
    ]

    if missing_expected_columns:
        raise HTTPException(
            status_code=400,
            detail=(
                "Transformation beklenen column'ları "
                "oluşturmadı: "
                + ", ".join(
                    missing_expected_columns
                )
            ),
        )

    if operation.origin == "data_quality":

        if (
            workspace.dataset_analysis is None
            or operation.finding_index is None
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Data-quality operation için "
                    "trusted finding bulunamadı."
                ),
            )

        findings = (
            workspace.dataset_analysis.findings
        )

        if (
            operation.finding_index < 0
            or operation.finding_index
            >= len(findings)
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Workbench finding reference "
                    "geçersiz."
                ),
            )

        finding = findings[
            operation.finding_index
        ]

        validation = (
            validate_transformation_for_finding(
                before_df=before_df,
                after_df=after_df,
                finding=finding,
            )
        )

        if validation is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Bu data-quality operation için "
                    "deterministic validation "
                    "desteklenmiyor."
                ),
            )

        if not validation.success:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Transformation data-quality "
                    "requirement'ını henüz "
                    "karşılamıyor."
                ),
            )

    # --------------------------------------------------
    # VERSION SNAPSHOT
    # --------------------------------------------------
    #
    # Dataset değişmeden ÖNCE rollback noktası oluştur.
    # Workbench operation state'i de snapshot'a girer.

    task_snapshot = None

    if workspace.current_task_id is not None:
        task_snapshot = (
            database.get_data_engineering_task(
                task_id=(
                    workspace.current_task_id
                ),
                learner_id=learner_id,
            )
        )

    checkpoint_snapshot = (
        workspace.checkpoint.model_copy(
            deep=True
        )
    )

    operations_snapshot = [
        item.model_copy(
            deep=True
        )
        for item
        in workspace.workbench_operations
    ]

    version_number = create_workspace_version(
        workspace_id=workspace_id,
        df=before_df,
        task=task_snapshot,
        checkpoint=checkpoint_snapshot,
        workbench_operations=(
            operations_snapshot
        ),
        workbench_active_operation_id=(
            workspace
            .workbench_active_operation_id
        ),
        label=(
            "Before Workbench operation: "
            f"{operation.title}"
        ),
        operation_id=(
            operation.operation_id
        ),
        operation_title=(
            operation.title
        ),
        operation_type=(
            operation.operation_type
        ),
        transformation_code=(
            request.code
        ),
        before_columns=(
            before_df.columns.tolist()
        ),
        after_columns=(
            after_df.columns.tolist()
        ),
    )

    schema_changed = (
        list(before_df.columns)
        != list(after_df.columns)
    )

    try:
        save_workspace_working_dataframe(
            workspace_id=workspace_id,
            df=after_df,
        )

    except OSError as exc:

        delete_workspace_version(
            workspace_id=workspace_id,
            version_number=version_number,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Transformation doğrulandı fakat "
                "working dataset kaydedilemedi."
            ),
        ) from exc

    try:
        (
            completed_operation,
            next_operation_id,
        ) = complete_workbench_operation(
            operations=(
                workspace.workbench_operations
            ),
            operation_id=request.operation_id,
            code=request.code,
            rollback_version_number=(
                version_number
            ),
            pipeline_action=(
                request.pipeline_action
            ),
        )

    except ValueError as exc:

        # Operation state güncellenemiyorsa
        # dataset'i eski haline döndür.
        save_workspace_working_dataframe(
            workspace_id=workspace_id,
            df=before_df,
        )

        delete_workspace_version(
            workspace_id=workspace_id,
            version_number=version_number,
        )

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    workspace.workbench_active_operation_id = (
        next_operation_id
    )

    workspace.workbench_preview = None

    # Dataset değiştiği için downstream state artık
    # eski working dataset'e ait.
    workspace.validation_result = None

    workspace.analysis_plan = None
    workspace.analysis_result = None
    workspace.analysis_results = []

    workspace.kpi_candidates = []
    workspace.kpi_definitions = []

    workspace.data_model_plan = None
    workspace.data_model_studio = None

    if workspace.usage_context == "personal":

        invalidate_started = False

        for deliverable in (
            workspace.project_deliverables
        ):
            if (
                deliverable.code
                == "clean_dataset"
            ):
                deliverable.status = (
                    "in_progress"
                )

                invalidate_started = True

                continue

            if invalidate_started:
                deliverable.status = "pending"

    workspace.checkpoint.completed_items = [
        item
        for item
        in workspace.checkpoint.completed_items
        if item not in {
            "Validation passed",
            "Final review completed",
            "Handoff completed",
        }
    ]

    if next_operation_id is None:

        workspace.checkpoint.current_focus = (
            "Validate prepared dataset"
        )

        workspace.checkpoint.next_actions = [
            "Validate prepared dataset"
        ]

    else:

        next_operation = (
            get_workbench_operation(
                operations=(
                    workspace.workbench_operations
                ),
                operation_id=(
                    next_operation_id
                ),
            )
        )

        workspace.checkpoint.current_focus = (
            next_operation.title
        )

        workspace.checkpoint.next_actions = [
            next_operation.title
        ]

    workspace.checkpoint.last_error = None

    database.save_workspace(
        workspace=workspace
    )

    return (
        WorkspaceWorkbenchTransformationResponse(
            operation=completed_operation,
            active_operation_id=(
                next_operation_id
            ),
            before_row_count=len(before_df),
            after_row_count=len(after_df),
            schema_changed=schema_changed,
            working_data=(
                WorkspaceWorkingDataResponse(
                    columns=(
                        after_df.columns.tolist()
                    ),
                    row_count=len(after_df),
                    rows=dataframe_to_records(
                        after_df
                    ),
                )
            ),
        )
    )



@router.post(
    (
        "/workspaces/{learner_id}/{workspace_id}"
        "/apply-pipeline-full"
    ),
    response_model=(
        WorkspaceFullPipelineResponse
    ),
)
def apply_workspace_pipeline_to_full_dataset(
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
        source_df = (
            load_workspace_source_dataframe(
                workspace_id
            )
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    if not workspace.workbench_operations:
        raise HTTPException(
            status_code=400,
            detail=(
                "Full dataset'e uygulanacak "
                "Workbench pipeline bulunamadı."
            ),
        )

    try:
        (
            full_df,
            applied_operation_ids,
        ) = apply_replayable_workbench_pipeline(
            source_df=source_df,
            operations=(
                workspace.workbench_operations
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if full_df.empty:
        raise HTTPException(
            status_code=400,
            detail=(
                "Pipeline full dataset içindeki "
                "bütün satırları silemez."
            ),
        )

    save_workspace_working_dataframe(
        workspace_id=workspace_id,
        df=full_df,
    )

    clear_workspace_versions(
        workspace_id=workspace_id
    )

    workspace.development_sample_enabled = False
    workspace.development_sample_row_count = len(
        full_df
    )

    workspace.validation_result = None
    workspace.analysis_plan = None
    workspace.analysis_result = None
    workspace.analysis_results = []

    workspace.kpi_candidates = []
    workspace.kpi_definitions = []

    workspace.data_model_plan = None
    workspace.data_model_studio = None

    workspace.checkpoint.completed_items = [
        item
        for item
        in workspace.checkpoint.completed_items
        if item not in {
            "Validation passed",
            "Final review completed",
            "Handoff completed",
        }
    ]

    workspace.checkpoint.current_focus = (
        "Validate full prepared dataset"
    )

    workspace.checkpoint.next_actions = [
        "Validate full prepared dataset"
    ]

    workspace.checkpoint.blocked_reason = None
    workspace.checkpoint.last_error = None

    if workspace.usage_context == "personal":
        invalidate_started = False

        for deliverable in (
            workspace.project_deliverables
        ):
            if deliverable.code == "clean_dataset":
                deliverable.status = "in_progress"
                invalidate_started = True
                continue

            if invalidate_started:
                deliverable.status = "pending"

    database.save_workspace(
        workspace=workspace
    )

    return WorkspaceFullPipelineResponse(
        source_row_count=len(
            source_df
        ),
        working_row_count=len(
            full_df
        ),
        applied_operation_ids=(
            applied_operation_ids
        ),
        applied_operation_count=len(
            applied_operation_ids
        ),
        development_sample_disabled=True,
    )


@router.post(
    (
        "/workspaces/{learner_id}/{workspace_id}"
        "/development-sample"
    ),
    response_model=(
        WorkspaceDevelopmentSampleResponse
    ),
)
def create_workspace_development_sample(
    learner_id: str,
    workspace_id: str,
    request: WorkspaceDevelopmentSampleRequest,
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
        source_df = (
            load_workspace_source_dataframe(
                workspace_id
            )
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    source_row_count = len(
        source_df
    )

    if source_row_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Source dataset boş.",
        )

    sample_size = min(
        request.sample_size,
        source_row_count,
    )

    sampled = (
        sample_size
        < source_row_count
    )

    if sampled:
        working_df = (
            source_df.sample(
                n=sample_size,
                random_state=(
                    request.random_seed
                ),
            )
            .reset_index(drop=True)
        )
    else:
        working_df = (
            source_df.copy()
            .reset_index(drop=True)
        )

    save_workspace_working_dataframe(
        workspace_id=workspace_id,
        df=working_df,
    )

    clear_workspace_versions(
        workspace_id=workspace_id
    )

    # A different development sample invalidates
    # previous transformation results and downstream
    # state. Rebuild only trusted quality operations.
    findings = (
        workspace.dataset_analysis.findings
        if workspace.dataset_analysis
        is not None
        else []
    )

    (
        workspace.workbench_operations,
        workspace.workbench_active_operation_id,
    ) = sync_data_quality_workbench_operations(
        existing_operations=[],
        findings=findings,
    )

    workspace.workbench_preview = None

    workspace.development_sample_size = (
        request.sample_size
    )

    workspace.development_sample_strategy = (
        request.strategy
    )

    workspace.development_sample_seed = (
        request.random_seed
    )

    workspace.development_sample_row_count = (
        len(working_df)
    )

    workspace.development_sample_enabled = (
        sampled
    )

    workspace.validation_result = None

    workspace.analysis_plan = None
    workspace.analysis_result = None
    workspace.analysis_results = []

    workspace.kpi_candidates = []
    workspace.kpi_definitions = []

    workspace.data_model_plan = None
    workspace.data_model_studio = None

    workspace.current_task_id = None

    workspace.checkpoint.completed_items = [
        item
        for item
        in workspace.checkpoint.completed_items
        if item not in {
            "Execution plan created",
            "Validation passed",
            "Final review completed",
            "Handoff completed",
        }
    ]

    workspace.checkpoint.current_focus = (
        "Review development sample and build execution plan"
    )

    workspace.checkpoint.next_actions = [
        "Build execution plan"
    ]

    workspace.checkpoint.blocked_reason = None
    workspace.checkpoint.last_error = None

    if workspace.usage_context == "personal":
        invalidate_started = False

        for deliverable in (
            workspace.project_deliverables
        ):
            if deliverable.code == "data_profile":
                deliverable.status = "completed"
                continue

            if deliverable.code == "clean_dataset":
                deliverable.status = "in_progress"
                invalidate_started = True
                continue

            if invalidate_started:
                deliverable.status = "pending"

    database.save_workspace(
        workspace=workspace
    )

    return WorkspaceDevelopmentSampleResponse(
        source_row_count=source_row_count,
        working_row_count=len(
            working_df
        ),
        requested_sample_size=(
            request.sample_size
        ),
        strategy=request.strategy,
        random_seed=request.random_seed,
        sampled=sampled,
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

        # ==================================================
    # TRUSTED WORKSPACE DATA
    # ==================================================
    #
    # Execution plan için frontend'in gönderdiği
    # profile/findings güvenlik kaynağı değildir.
    #
    # Backend'in daha önce local olarak oluşturup
    # workspace'e kaydettiği veriyi kullanıyoruz.

    if workspace.dataset_profile is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Execution plan öncesinde "
                "dataset profile oluşturulmalı."
            ),
        )

    if workspace.dataset_analysis is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Execution plan öncesinde "
                "dataset analysis oluşturulmalı."
            ),
        )

    trusted_profile = (
        workspace.dataset_profile
    )

    trusted_findings = (
        workspace.dataset_analysis.findings
    )


    # ==================================================
    # SECURITY POLICY
    # ==================================================

    security_decision = (
        evaluate_external_ai_policy(
            usage_context=(
                workspace.usage_context
            ),
            data_sensitivity=(
                workspace.data_sensitivity
                or "unknown"
            ),
            organization_id=(
                workspace.organization_id
            ),
            organization_ai_allowed=None,
        )
    )


    # ==================================================
    # EXECUTION PLAN STRATEGY
    # ==================================================

    try:

        if (
            security_decision
            .external_ai_allowed
        ):

            try:
                task = (
                    generate_workspace_execution_plan(
                        workspace=workspace,
                        profile=trusted_profile,
                        findings=trusted_findings,
                    )
                )

            except Exception:

                # AI izinli olsa bile servis çökerse
                # junior tamamen durmaz.
                task = (
                    generate_local_workspace_execution_plan(
                        workspace=workspace,
                        findings=trusted_findings,
                    )
                )

        else:

            # Confidential / restricted / pending vb.
            # durumlarda OpenAI hiç çağrılmaz.
            task = (
                generate_local_workspace_execution_plan(
                    workspace=workspace,
                    findings=trusted_findings,
                )
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

    completed_items = list(
        dict.fromkeys(
            workspace.checkpoint.completed_items
        )
    )
    
    if "Dataset profile" not in completed_items:
        completed_items.append(
            "Dataset profile"
        )
    
    if (
        "Execution plan created"
        not in completed_items
    ):
        completed_items.append(
            "Execution plan created"
        )
    
    workspace.checkpoint.completed_items = (
        completed_items
    )

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

    # ==================================================
    # LOCAL DATA ANALYSIS
    # ==================================================
    #
    # Raw dataset üzerinde deterministic kontroller
    # HER ZAMAN local olarak çalışır.
    #
    # Bu işlem external AI izninden bağımsızdır.

    local_analysis = (
        analyze_dataframe_locally(
            df
        )
    )

    # ==================================================
    # SAFE PROFILE
    # ==================================================
    #
    # Raw sample rows external AI context'ine
    # dahil edilmez.

    profile = build_data_profile(
        df
    )

    safe_profile = {
        key: value
        for key, value in profile.items()
        if key != "sample_rows"
    }

    # ==================================================
    # DATA SECURITY POLICY
    # ==================================================

    security_decision = (
        evaluate_external_ai_policy(
            usage_context=(
                workspace.usage_context
            ),
            data_sensitivity=(
                workspace.data_sensitivity
                or "unknown"
            ),
            organization_id=(
                workspace.organization_id
            ),
            organization_ai_allowed=None,
        )
    )


    # ==================================================
    # ANALYSIS STRATEGY
    # ==================================================

    if (
        security_decision
        .external_ai_allowed
    ):

        try:
            ai_analysis = (
                generate_data_recommendations(
                    safe_profile
                )
            )

            analysis = (
                merge_data_quality_analyses(
                    local_analysis,
                    ai_analysis,
                )
            )

            analysis_source = (
                "local_and_ai"
            )

        except Exception:

            # External AI izinli olsa bile
            # servis çalışmazsa junior'ın işi
            # tamamen durmamalı.
            #
            # Local deterministic findings ile
            # devam ediyoruz.

            analysis = local_analysis

            analysis_source = (
                "local_ai_fallback"
            )

    else:

        # Confidential / restricted / unknown
        # veya organization policy izin vermiyorsa
        # external AI çağrısı yapılmaz.

        analysis = local_analysis

        analysis_source = "local"

    workspace.dataset_filename = file.filename

    workspace.development_sample_size = None
    workspace.development_sample_strategy = None
    workspace.development_sample_seed = None
    workspace.development_sample_row_count = len(df)
    workspace.development_sample_enabled = False

    workspace.dataset_profile = (
        safe_profile
    )

    (
    workspace.workbench_operations,
        workspace.workbench_active_operation_id,
    ) = sync_data_quality_workbench_operations(
        existing_operations=(
            workspace.workbench_operations
        ),
        findings=analysis.findings,
    )

    workspace.dataset_analysis = (
        analysis
    )

    workspace.dataset_ai_processing_status = (
        security_decision
        .ai_processing_status
    )

    workspace.dataset_analysis_source = (
        analysis_source
    )

    if workspace.usage_context == "personal":
        complete_and_advance_personal_project_deliverable(
            workspace=workspace,
            code="data_profile",
        )

    workspace.validation_result = None
    workspace.analysis_plan = None
    workspace.analysis_result = None
    workspace.analysis_results = []
    workspace.kpi_candidates = []
    workspace.kpi_definitions = []

    workspace.checkpoint.completed_items = [
        item
        for item in workspace.checkpoint.completed_items
        if item not in {
            "Validation passed",
            "Final review completed",
        }
    ]

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
        "workspace_id":
            workspace_id,

        "filename":
            file.filename,

        "profile":
            safe_profile,

        "analysis":
            analysis.model_dump(),

        "ai_processing_status":
            security_decision
            .ai_processing_status,

        "external_ai_allowed":
            security_decision
            .external_ai_allowed,

        "analysis_source":
            analysis_source,
    }

@router.post(
    (
        "/workspaces/{learner_id}/{workspace_id}"
        "/data/findings/{finding_index}/mentor"
    ),
    response_model=WorkspaceFindingMentorResponse,
)
def mentor_workspace_finding_locally(
    learner_id: str,
    workspace_id: str,
    finding_index: int,
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

    if workspace.dataset_analysis is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Workspace için dataset analysis "
                "henüz bulunmuyor."
            ),
        )

    findings = (
        workspace.dataset_analysis.findings
    )

    if (
        finding_index < 0
        or finding_index >= len(findings)
    ):
        raise HTTPException(
            status_code=404,
            detail="Finding bulunamadı.",
        )

    # Finding frontend'den gelmiyor.
    # Güvenilir workspace state içinden alınıyor.
    finding = findings[finding_index]

    skill_name = (
        get_skill_for_data_quality_issue(
            finding.issue_type
        )
    )

    if skill_name is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Bu finding için uygun "
                "mentor skill'i bulunamadı."
            ),
        )

    skill_state = database.get_skill_state(
        learner_id,
        skill_name,
    )

    if skill_state is None:

        database.insert_skill_state(
            learner_id,
            skill_name,
            status="new",
        )

        skill_status = "new"

    else:
        skill_status = (
            skill_state["status"]
        )

    assistance_level = (
        get_local_assistance_level(
            skill_status
        )
    )

    mentor_response = (
        build_local_mentor_response(
            finding=finding,
            skill_status=skill_status,
        )
    )

    return WorkspaceFindingMentorResponse(
        finding_index=finding_index,
        finding=finding,
        skill_name=skill_name,
        skill_status=skill_status,
        assistance_level=(
            assistance_level
        ),
        mentor_response=(
            mentor_response
        ),
        source="local",
    )

@router.post(
    (
        "/workspaces/{learner_id}/{workspace_id}"
        "/data/findings/{finding_index}/attempt"
    ),
    response_model=WorkspaceFindingAttemptResponse,
)
def review_workspace_finding_attempt(
    learner_id: str,
    workspace_id: str,
    finding_index: int,
    request: WorkspaceFindingAttemptRequest,
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

    if workspace.dataset_analysis is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Workspace için dataset analysis "
                "bulunamadı."
            ),
        )

    findings = (
        workspace.dataset_analysis.findings
    )

    if (
        finding_index < 0
        or finding_index >= len(findings)
    ):
        raise HTTPException(
            status_code=404,
            detail="Finding bulunamadı.",
        )

    # Frontend finding göndermiyor.
    # Trusted finding backend workspace state'inden geliyor.
    finding = findings[finding_index]

    skill_name = (
        get_skill_for_data_quality_issue(
            finding.issue_type
        )
    )

    if skill_name is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Bu finding için uygun "
                "mentor skill'i bulunamadı."
            ),
        )

    security_decision = (
        evaluate_external_ai_policy(
            usage_context=(
                workspace.usage_context
            ),
            data_sensitivity=(
                workspace.data_sensitivity
                or "unknown"
            ),
            organization_id=(
                workspace.organization_id
            ),
            organization_ai_allowed=None,
        )
    )

    # ==================================================
    # EXTERNAL AI ALLOWED
    # ==================================================

    if security_decision.external_ai_allowed:

        result = review_data_quality_attempt(
            learner_id=learner_id,
            finding=finding,
            attempt=request.attempt,
        )

        if result is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Attempt review için uygun "
                    "mentor skill'i bulunamadı."
                ),
            )

        return WorkspaceFindingAttemptResponse(
            finding_index=finding_index,
            skill_name=result.skill_name,
            skill_status=result.skill_status,
            mentor_response=(
                result.mentor_response
            ),
            evidence=result.evidence,
            source="external_ai",
        )


    # ==================================================
    # LOCAL SECURE MODE
    # ==================================================
    #
    # Free-text attempt'in semantik olarak doğru
    # olup olmadığını deterministic engine ile
    # uydurarak değerlendirmiyoruz.
    #
    # Gerçek success ancak transformation sonucunda
    # before/after data ile doğrulanacak.

    skill_state = database.get_skill_state(
        learner_id,
        skill_name,
    )

    if skill_state is None:

        database.insert_skill_state(
            learner_id,
            skill_name,
            status="new",
        )

        skill_status = "new"

    else:
        skill_status = (
            skill_state["status"]
        )

    local_guidance = (
        build_local_mentor_response(
            finding=finding,
            skill_status=skill_status,
        )
    )

    evidence = LearningEvidenceDecision(
        is_evidence=False,
        evidence_type=None,
        success=None,
        note=(
            "Free-text attempt local secure mode'da "
            "otomatik başarı evidence'ı olarak "
            "değerlendirilmedi. Gerçek sonuç "
            "transformation validation ile doğrulanmalı."
        ),
    )

    mentor_response = (
        "Bu açıklamayı local secure mode'da "
        "doğru veya yanlış diye puanlamıyorum. "
        f"{local_guidance}"
    )

    return WorkspaceFindingAttemptResponse(
        finding_index=finding_index,
        skill_name=skill_name,
        skill_status=skill_status,
        mentor_response=mentor_response,
        evidence=evidence,
        source="local",
    )


@router.get(
    "/workspaces/{learner_id}/{workspace_id}/data/preview",
    response_model=WorkspaceDataPreviewResponse,
)
def get_workspace_data_preview(
    learner_id: str,
    workspace_id: str,
    dataset: Literal[
        "source",
        "working",
    ] = "working",
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=25,
        ge=5,
        le=100,
    ),
    search: str | None = Query(
        default=None,
        max_length=200,
    ),
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
            load_workspace_source_dataframe(
                workspace_id
            )
            if dataset == "source"
            else load_workspace_working_dataframe(
                workspace_id
            )
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    total_row_count = len(df)

    filtered_df = df

    normalized_search = (
        search.strip()
        if search is not None
        else ""
    )

    if normalized_search:
        row_matches = pd.Series(
            False,
            index=df.index,
        )

        for column in df.columns:
            row_matches = (
                row_matches
                | df[column]
                .astype(str)
                .str.contains(
                    normalized_search,
                    case=False,
                    na=False,
                    regex=False,
                )
            )

        filtered_df = df.loc[
            row_matches
        ]

    filtered_row_count = len(
        filtered_df
    )

    total_pages = max(
        1,
        (
            filtered_row_count
            + page_size
            - 1
        )
        // page_size,
    )

    effective_page = min(
        page,
        total_pages,
    )

    start = (
        effective_page - 1
    ) * page_size

    page_df = filtered_df.iloc[
        start:
        start + page_size
    ]

    return WorkspaceDataPreviewResponse(
        dataset=dataset,
        columns=df.columns.tolist(),
        total_row_count=total_row_count,
        filtered_row_count=(
            filtered_row_count
        ),
        page=effective_page,
        page_size=page_size,
        total_pages=total_pages,
        rows=dataframe_to_records(
            page_df
        ),
    )


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
    "/workspaces/{learner_id}/{workspace_id}/versions",
    response_model=list[WorkspaceVersionSummary],
)
def get_workspace_versions(
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

    return list_workspace_versions(
        workspace_id=workspace_id
    )


@router.post(
    "/workspaces/{learner_id}/{workspace_id}/versions/{version_number}/restore"
)
def restore_workspace_version(
    learner_id: str,
    workspace_id: str,
    version_number: int,
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
        (
            restored_df,
            restored_task,
            restored_checkpoint,
            restored_operations,
            restored_active_operation_id,
        ) = load_workspace_version(
            workspace_id=workspace_id,
            version_number=version_number,
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except (
        ValueError,
        KeyError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    save_workspace_working_dataframe(
        workspace_id=workspace_id,
        df=restored_df,
    )

    if restored_task is not None:
        database.save_data_engineering_task(
            learner_id=learner_id,
            task=restored_task,
        )

        workspace.current_task_id = (
            restored_task.task_id
        )

    else:
        workspace.current_task_id = None

    workspace.checkpoint = (
        restored_checkpoint
    )

    if restored_operations is not None:
        workspace.workbench_operations = (
            restored_operations
        )

        workspace.workbench_active_operation_id = (
            restored_active_operation_id
        )

    workspace.workbench_preview = None

    workspace.validation_result = None

    workspace.analysis_plan = None
    workspace.analysis_result = None
    workspace.analysis_results = []

    workspace.kpi_candidates = []
    workspace.kpi_definitions = []

    workspace.data_model_plan = None
    workspace.data_model_studio = None

    if workspace.usage_context == "personal":

        invalidate_started = False

        for deliverable in (
            workspace.project_deliverables
        ):
            if (
                deliverable.code
                == "clean_dataset"
            ):
                deliverable.status = (
                    "in_progress"
                )

                invalidate_started = True
                continue

            if invalidate_started:
                deliverable.status = "pending"

    workspace.checkpoint.completed_items = [
        item
        for item
        in workspace.checkpoint.completed_items
        if item not in {
            "Validation passed",
            "Final review completed",
            "Handoff completed",
        }
    ]

    workspace.checkpoint.last_error = None

    database.save_workspace(
        workspace=workspace
    )

    return {
        "version_number":
            version_number,

        "message":
            "Workspace version restored.",

        "task": (
            restored_task.model_dump()
            if restored_task is not None
            else None
        ),

        "checkpoint":
            workspace.checkpoint,

        "workbench_operations": (
            workspace.workbench_operations
        ),

        "workbench_active_operation_id": (
            workspace
            .workbench_active_operation_id
        ),

        "working_data": {
            "columns":
                restored_df.columns.tolist(),

            "row_count":
                len(restored_df),

            "rows":
                dataframe_to_records(
                    restored_df
                ),
        },
    }

@router.post(
    "/workspaces/{learner_id}/{workspace_id}/data/transform",
    response_model=DataEngineeringTaskTransformationResponse,
)
def transform_workspace_data(
    learner_id: str,
    workspace_id: str,
    request: WorkspaceTransformationRequest,
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

    if workspace.current_task_id is None:
        raise HTTPException(
            status_code=400,
            detail="Workspace için aktif execution plan bulunamadı.",
        )

    task = database.get_data_engineering_task(
        task_id=workspace.current_task_id,
        learner_id=learner_id,
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Execution task bulunamadı.",
        )

    if task.status == "completed":
        raise HTTPException(
            status_code=400,
            detail="Execution task zaten tamamlanmış.",
        )

    try:
        before_df = (
            load_workspace_working_dataframe(
                workspace_id
            )
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    after_df = pd.DataFrame(
        request.after_rows
    )

    if after_df.empty:
        raise HTTPException(
            status_code=400,
            detail=(
                "Transformation dataset içindeki "
                "bütün satırları silemez."
            ),
        )

    if list(after_df.columns) != list(before_df.columns):
        raise HTTPException(
            status_code=400,
            detail=(
                "Transformation dataset şemasını "
                "değiştiremez."
            ),
        )

    current_step = next(
        (
            step
            for step in task.steps
            if step.status == "active"
        ),
        None,
    )

    if current_step is None:
        raise HTTPException(
            status_code=400,
            detail="Aktif task step bulunamadı.",
        )


    # Transformation'dan önceki task ve checkpoint
    # durumlarını bellekte de saklıyoruz.
    # Böylece dosya kaydı sırasında hata olursa
    # workflow state'ini eski haline döndürebiliriz.
    task_before = task.model_copy(
        deep=True
    )

    checkpoint_before = (
        workspace.checkpoint.model_copy(
            deep=True
        )
    )

    version_number = create_workspace_version(
        workspace_id=workspace_id,
        df=before_df,
        task=task_before,
        checkpoint=checkpoint_before,
        label=(
            f"Before step "
            f"{current_step.step_number}: "
            f"{current_step.title}"
        ),
    )

        # ==================================================
    # DATA SECURITY POLICY
    # ==================================================

    security_decision = (
        evaluate_external_ai_policy(
            usage_context=(
                workspace.usage_context
            ),
            data_sensitivity=(
                workspace.data_sensitivity
                or "unknown"
            ),
            organization_id=(
                workspace.organization_id
            ),
            organization_ai_allowed=None,
        )
    )


    # ==================================================
    # TRANSFORMATION REVIEW STRATEGY
    # ==================================================

    try:

        if (
            security_decision
            .external_ai_allowed
        ):

            result = (
                review_data_engineering_task_transformation(
                    learner_id=learner_id,
                    task=task,
                    before_df=before_df,
                    after_df=after_df,
                )
            )

        else:

            # Confidential / restricted / pending
            # work data external AI'ya gitmez.
            #
            # Validation, learning evidence ve
            # task progression local olarak yapılır.

            result = (
                review_task_transformation_locally(
                    learner_id=learner_id,
                    task=task,
                    before_df=before_df,
                    after_df=after_df,
                )
            )

    except ValueError as exc:

        delete_workspace_version(
            workspace_id=workspace_id,
            version_number=version_number,
        )

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    if result.validation.success:
        try:
            save_workspace_working_dataframe(
                workspace_id=workspace_id,
                df=after_df,
            )
            workspace.validation_result = None
            workspace.analysis_plan = None
            workspace.analysis_result = None
            workspace.analysis_results = []
            workspace.kpi_candidates = []
            workspace.kpi_definitions = []

        except OSError as exc:
            # Task review servisi başarılı validation
            # sonrası task'ı DB'ye kaydetmiş olabilir.
            # working.csv yazılamadıysa task state'i
            # eski haline döndürülür.
            database.save_data_engineering_task(
                learner_id=learner_id,
                task=task_before,
            )

            workspace.checkpoint = (
                checkpoint_before
            )

            database.save_workspace(
                workspace=workspace
            )

            delete_workspace_version(
                workspace_id=workspace_id,
                version_number=version_number,
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    "Transformation doğrulandı ancak "
                    "working dataset kaydedilemedi."
                ),
            ) from exc

        if (
            current_step.title
            not in workspace.checkpoint.completed_items
        ):
            workspace.checkpoint.completed_items.append(
                current_step.title
            )

        if result.task.status == "completed":
            workspace.checkpoint.current_focus = (
                "Review transformed dataset"
            )

            workspace.checkpoint.next_actions = [
                "Review transformation results"
            ]

        else:
            active_step = next(
                (
                    step
                    for step in result.task.steps
                    if step.status == "active"
                ),
                None,
            )

            workspace.checkpoint.current_focus = (
                active_step.title
                if active_step
                else None
            )

            workspace.checkpoint.next_actions = [
                step.title
                for step in result.task.steps
                if step.status == "pending"
            ]

        workspace.checkpoint.last_error = None

    else:
        # Validation başarısızsa hiçbir kalıcı
        # data/workflow değişikliği olmadığı için
        # oluşturduğumuz snapshot'a gerek yok.
        delete_workspace_version(
            workspace_id=workspace_id,
            version_number=version_number,
        )

        workspace.checkpoint.last_error = (
            "Transformation validation failed."
        )

    database.save_workspace(
        workspace=workspace
    )

    return result


@router.post(
    "/workspaces/{learner_id}/{workspace_id}/validate",
    response_model=WorkspaceValidationResponse,
)
def validate_workspace_result(
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

    if workspace.current_task_id is None:
        raise HTTPException(
            status_code=400,
            detail="Execution plan bulunamadı.",
        )

    task = database.get_data_engineering_task(
        task_id=workspace.current_task_id,
        learner_id=learner_id,
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Execution task bulunamadı.",
        )

    if task.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=(
                "Validation başlamadan önce "
                "transformation adımları tamamlanmalı."
            ),
        )

    try:
        source_df = (
            load_workspace_source_dataframe(
                workspace_id
            )
        )

        working_df = (
            load_workspace_working_dataframe(
                workspace_id
            )
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    source_profile = build_data_profile(
        source_df
    )

    working_profile = build_data_profile(
        working_df
    )

    checks: list[
        WorkspaceValidationCheck
    ] = []
    
    rows_exist = len(working_df) > 0
    
    checks.append(
        WorkspaceValidationCheck(
            name="Dataset integrity",
            status=(
                "passed"
                if rows_exist
                else "failed"
            ),
            message=(
                f"Working dataset contains "
                f"{len(working_df)} rows."
            ),
            code="dataset_integrity",
            params={
                "row_count": len(working_df),
            },
        )
    )
    
    schema_preserved = (
        source_df.columns.tolist()
        ==
        working_df.columns.tolist()
    )
    
    checks.append(
        WorkspaceValidationCheck(
            name="Schema preserved",
            status=(
                "passed"
                if schema_preserved
                else "failed"
            ),
            message=(
                "Working dataset columns match "
                "the original source."
                if schema_preserved
                else
                "Working dataset columns differ "
                "from the original source."
            ),
            code="schema_preserved",
            params={
                "preserved": schema_preserved,
            },
        )
    )
    
    for step in task.steps:
        finding = step.finding
    
        if (
            finding.issue_type
            == "duplicate_rows"
        ):
            duplicate_count = (
                working_profile[
                    "duplicate_count"
                ]
            )
    
            success = (
                duplicate_count == 0
            )
    
            checks.append(
                WorkspaceValidationCheck(
                    name="Duplicate rows",
                    status=(
                        "passed"
                        if success
                        else "failed"
                    ),
                    message=(
                        f"{duplicate_count} "
                        "duplicate rows remain."
                    ),
                    code="duplicate_rows",
                    params={
                        "duplicate_count":
                            duplicate_count,
                    },
                )
            )
    
        elif (
            finding.issue_type
            == "missing_values"
            and finding.column
        ):
            missing_count = (
                working_profile[
                    "null_counts"
                ].get(
                    finding.column,
                    0,
                )
            )
    
            success = (
                missing_count == 0
            )
    
            checks.append(
                WorkspaceValidationCheck(
                    name=(
                        f"Missing values · "
                        f"{finding.column}"
                    ),
                    status=(
                        "passed"
                        if success
                        else "failed"
                    ),
                    message=(
                        f"{missing_count} missing "
                        f"values remain in "
                        f"{finding.column}."
                    ),
                    code="missing_values",
                    params={
                        "column":
                            finding.column,
                        "missing_count":
                            missing_count,
                    },
                )
            )

    passed = all(
        check.status != "failed"
        for check in checks
    )

    if passed:

        if workspace.usage_context == "personal":
            complete_and_advance_personal_project_deliverable(
                workspace=workspace,
                code="clean_dataset",
            )

            workspace.analysis_plan = (
                build_personal_analysis_plan(
                    working_profile,
                    dataset_filename=(
                        workspace.dataset_filename
                    ),
                )
            )

            workspace.kpi_candidates = (
                build_personal_kpi_candidates_from_plan(
                    workspace.analysis_plan
                )
            )

        if (
            "Validation passed"
            not in workspace.checkpoint.completed_items
        ):
            workspace.checkpoint.completed_items.append(
                "Validation passed"
            )

        workspace.checkpoint.current_focus = (
            "Review transformed dataset"
        )

        workspace.checkpoint.next_actions = [
            "Review final dataset and changes"
        ]

        workspace.checkpoint.last_error = None

    else:
        workspace.checkpoint.current_focus = (
            "Resolve validation failures"
        )

        workspace.checkpoint.last_error = (
            "Final validation failed."
        )

    validation_result = WorkspaceValidationResponse(
        passed=passed,
        source_row_count=(
            source_profile["row_count"]
        ),
        working_row_count=(
            working_profile["row_count"]
        ),
        checks=checks,
    )
    
    workspace.validation_result = (
        validation_result
    )
    
    database.save_workspace(
        workspace=workspace
    )
    
    return validation_result

@router.post(
    "/workspaces/{learner_id}/{workspace_id}/review/complete",
    response_model=WorkspaceReviewResponse,
)

@router.post(
    (
        "/workspaces/{learner_id}/{workspace_id}"
        "/analysis/run"
    ),
    response_model=PersonalProjectAnalysisResult,
)
def run_personal_project_analysis(
    learner_id: str,
    workspace_id: str,
    request: PersonalProjectAnalysisRequest,
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

    if workspace.usage_context != "personal":
        raise HTTPException(
            status_code=400,
            detail=(
                "Personal project analysis yalnızca "
                "personal workspace için kullanılabilir."
            ),
        )

    if (
        workspace.validation_result is None
        or not workspace.validation_result.passed
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Analysis başlamadan önce "
                "final validation başarılı olmalı."
            ),
        )

    if workspace.analysis_plan is None:
        raise HTTPException(
            status_code=400,
            detail="Analysis plan bulunamadı.",
        )

    has_analysis_deliverable = any(
        deliverable.code == "analysis"
        for deliverable
        in workspace.project_deliverables
    )

    if not has_analysis_deliverable:
        raise HTTPException(
            status_code=400,
            detail=(
                "Bu personal project type "
                "analysis deliverable içermiyor."
            ),
        )

    if (
        request.measure
        not in
        workspace.analysis_plan.measure_candidates
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Geçersiz analysis measure."
            ),
        )

    if (
        request.dimension is not None
        and request.dimension
        not in
        workspace.analysis_plan.dimension_candidates
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Geçersiz analysis dimension."
            ),
        )

    try:
        working_df = (
            load_workspace_working_dataframe(
                workspace_id
            )
        )

        result = (
            build_personal_analysis_result(
                df=working_df,
                measure=request.measure,
                dimension=request.dimension,
            )
        )
        result = result.model_copy(
            update={
                "analysis_id": str(
                    uuid.uuid4()
                )
            }
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    # Son çalıştırılan analysis mevcut kodlarla
    # uyumluluk için burada kalır.
    workspace.analysis_result = result
    
    # Bütün analysis sonuçlarını ayrıca saklıyoruz.
    workspace.analysis_results.append(
        result
    )
    

    complete_and_advance_personal_project_deliverable(
        workspace=workspace,
        code="analysis",
    )

    workspace.checkpoint.current_focus = (
        "Build analytical data model"
    )

    workspace.checkpoint.next_actions = [
        "Build data model"
    ]

    workspace.checkpoint.last_error = None

    database.save_workspace(
        workspace=workspace
    )

    return result


@router.delete(
    (
        "/workspaces/{learner_id}/{workspace_id}"
        "/analysis"
    ),
    response_model=Workspace,
)
def delete_personal_project_analysis(
    learner_id: str,
    workspace_id: str,
    request: PersonalProjectAnalysisDeleteRequest,
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

    if workspace.usage_context != "personal":
        raise HTTPException(
            status_code=400,
            detail=(
                "Analysis silme yalnızca personal "
                "workspace için kullanılabilir."
            ),
        )

    existing_count = len(
        workspace.analysis_results
    )

    workspace.analysis_results = [
        result
        for result
        in workspace.analysis_results
        if result.analysis_id
        != request.analysis_id
    ]

    if (
        len(workspace.analysis_results)
        == existing_count
    ):
        raise HTTPException(
            status_code=404,
            detail="Analysis bulunamadı.",
        )

    # Latest analysis silindiyse son kalan
    # analysis'i active/latest olarak kullan.
    if (
        workspace.analysis_result is not None
        and workspace.analysis_result.analysis_id
        == request.analysis_id
    ):
        workspace.analysis_result = (
            workspace.analysis_results[-1]
            if workspace.analysis_results
            else None
        )


    database.save_workspace(
        workspace=workspace
    )

    return workspace


@router.post(
    (
        "/workspaces/{learner_id}/{workspace_id}"
        "/kpis/select"
    ),
    response_model=list[
        PersonalProjectKPIDefinition
    ],
)
def select_personal_project_kpis(
    learner_id: str,
    workspace_id: str,
    request: PersonalProjectKPISelectionRequest,
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

    if workspace.usage_context != "personal":
        raise HTTPException(
            status_code=400,
            detail=(
                "KPI selection yalnızca "
                "personal workspace için kullanılabilir."
            ),
        )

    if workspace.data_model_plan is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "KPI seçilmeden önce "
                "data model oluşturulmalı."
            ),
        )

    has_kpi_deliverable = any(
        deliverable.code == "kpi_definitions"
        for deliverable
        in workspace.project_deliverables
    )

    if not has_kpi_deliverable:
        raise HTTPException(
            status_code=400,
            detail=(
                "Bu project type KPI definitions "
                "deliverable içermiyor."
            ),
        )

    if not workspace.kpi_candidates:
        raise HTTPException(
            status_code=400,
            detail="KPI candidate bulunamadı.",
        )

    candidates_by_code = {
        candidate.code: candidate
        for candidate
        in workspace.kpi_candidates
    }

    selected_codes = list(
        dict.fromkeys(
            request.codes
        )
    )

    invalid_codes = [
        code
        for code in selected_codes
        if code not in candidates_by_code
    ]

    if invalid_codes:
        raise HTTPException(
            status_code=400,
            detail=(
                "Geçersiz KPI candidate: "
                + ", ".join(invalid_codes)
            ),
        )

    selected_definitions = [
        candidates_by_code[code]
        for code in selected_codes
    ]

    workspace.kpi_definitions = (
        selected_definitions
    )

    complete_and_advance_personal_project_deliverable(
        workspace=workspace,
        code="kpi_definitions",
    )

    workspace.checkpoint.current_focus = (
        "Prepare Power BI-ready dataset"
    )
    
    workspace.checkpoint.next_actions = [
        "Prepare Power BI-ready dataset"
    ]

    workspace.checkpoint.last_error = None

    database.save_workspace(
        workspace=workspace
    )

    return selected_definitions


@router.post(
    (
        "/workspaces/{learner_id}/{workspace_id}"
        "/data-model/build"
    ),
    response_model=PersonalProjectDataModelPlan,
)
def build_personal_project_data_model(
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

    if workspace.usage_context != "personal":
        raise HTTPException(
            status_code=400,
            detail=(
                "Data model yalnızca personal "
                "workspace için oluşturulabilir."
            ),
        )

    if workspace.analysis_plan is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Data model oluşturulmadan önce "
                "analysis plan gerekli."
            ),
        )

    

    has_data_model_deliverable = any(
        deliverable.code == "data_model"
        for deliverable
        in workspace.project_deliverables
    )

    if not has_data_model_deliverable:
        raise HTTPException(
            status_code=400,
            detail=(
                "Bu project type data model "
                "deliverable içermiyor."
            ),
        )

    data_model_plan = (
        build_personal_data_model_plan(
            dataset_filename=(
                workspace.dataset_filename
            ),
            analysis_plan=(
                workspace.analysis_plan
            ),
        )
    )

    workspace.data_model_plan = (
        data_model_plan
    )

    workspace.data_model_studio = (
        build_personal_data_model_studio(
            data_model_plan=data_model_plan,
        )
    )

    complete_and_advance_personal_project_deliverable(
        workspace=workspace,
        code="data_model",
    )

    workspace.checkpoint.current_focus = (
        "Define project KPIs and measures"
    )

    workspace.checkpoint.next_actions = [
        "Define KPIs"
    ]

    workspace.checkpoint.last_error = None

    database.save_workspace(
        workspace=workspace
    )

    return data_model_plan


@router.put(
    (
        "/workspaces/{learner_id}/{workspace_id}"
        "/data-model/studio"
    ),
    response_model=PersonalProjectDataModelStudio,
)
def update_personal_project_data_model_studio(
    learner_id: str,
    workspace_id: str,
    studio: PersonalProjectDataModelStudio,
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

    if workspace.usage_context != "personal":
        raise HTTPException(
            status_code=400,
            detail=(
                "Model Studio yalnızca personal "
                "workspace için düzenlenebilir."
            ),
        )

    if workspace.data_model_plan is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Model Studio düzenlenmeden önce "
                "data model oluşturulmalı."
            ),
        )

    try:
        validated_studio = (
            validate_personal_data_model_studio(
                studio
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    workspace.data_model_studio = (
        validated_studio
    )

    workspace.checkpoint.current_focus = (
        "Review data model and define KPIs"
    )

    workspace.checkpoint.next_actions = [
        "Review model relationships",
        "Define KPIs",
    ]

    workspace.checkpoint.last_error = None

    database.save_workspace(
        workspace=workspace
    )

    return validated_studio

def complete_workspace_review(
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

    if workspace.validation_result is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Review tamamlanmadan önce "
                "final validation çalıştırılmalı."
            ),
        )

    if not workspace.validation_result.passed:
        raise HTTPException(
            status_code=400,
            detail=(
                "Başarısız validation sonucu ile "
                "review tamamlanamaz."
            ),
        )

    try:
        working_df = (
            load_workspace_working_dataframe(
                workspace_id
            )
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    if (
        "Final review completed"
        not in workspace.checkpoint.completed_items
    ):
        workspace.checkpoint.completed_items.append(
            "Final review completed"
        )

    workspace.checkpoint.current_focus = (
        "Prepare handoff"
    )

    workspace.checkpoint.next_actions = [
        "Prepare final dataset handoff"
    ]

    workspace.checkpoint.last_error = None

    database.save_workspace(
        workspace=workspace
    )

    return WorkspaceReviewResponse(
        completed=True,
        message="Final review completed.",
        working_row_count=len(working_df),
    )


@router.get(
    "/workspaces/{learner_id}/{workspace_id}/handoff/export"
)
def export_workspace_handoff(
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

    if (
        "Final review completed"
        not in workspace.checkpoint.completed_items
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Final dataset export edilmeden önce "
                "review tamamlanmalı."
            ),
        )

    if (
        workspace.validation_result is None
        or not workspace.validation_result.passed
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Geçerli başarılı validation sonucu "
                "bulunamadı."
            ),
        )

    try:
        working_df = (
            load_workspace_working_dataframe(
                workspace_id
            )
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    csv_content = working_df.to_csv(
        index=False
    )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                'attachment; '
                'filename="datapilot_final.csv"'
            )
        },
    )


@router.post(
    "/workspaces/{learner_id}/{workspace_id}/handoff/complete",
    response_model=Workspace,
)
def complete_workspace_handoff(
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

    if (
        "Final review completed"
        not in workspace.checkpoint.completed_items
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Handoff tamamlanmadan önce "
                "final review tamamlanmalı."
            ),
        )

    if (
        workspace.validation_result is None
        or not workspace.validation_result.passed
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Handoff için başarılı bir "
                "validation sonucu gerekli."
            ),
        )

    if (
        "Handoff completed"
        not in workspace.checkpoint.completed_items
    ):
        workspace.checkpoint.completed_items.append(
            "Handoff completed"
        )

    workspace.checkpoint.current_focus = (
        "Workspace completed"
    )

    workspace.checkpoint.next_actions = []

    workspace.checkpoint.last_error = None

    workspace.status = "completed"

    database.save_workspace(
        workspace=workspace
    )

    return workspace

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

    if reconcile_personal_project_deliverables(
        workspace
    ):
        database.save_workspace(
            workspace=workspace
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