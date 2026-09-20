import uuid
from io import BytesIO
from fastapi import (
    APIRouter,
    HTTPException,
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
    update_personal_project_deliverable,
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
    workspace.dataset_profile = (
        safe_profile
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
        update_personal_project_deliverable(
            workspace=workspace,
            code="data_profile",
            status="completed",
        )

    workspace.validation_result = None

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
        ) = load_workspace_version(
            workspace_id=workspace_id,
            version_number=version_number,
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except (
        ValueError,
        KeyError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    # Önce data'yı geri getir.
    save_workspace_working_dataframe(
        workspace_id=workspace_id,
        df=restored_df,
    )

    # Sonra task state'ini geri getir.
    database.save_data_engineering_task(
        learner_id=learner_id,
        task=restored_task,
    )

    # Workspace tekrar snapshot'taki task'a
    # bağlı kalmalı.
    workspace.current_task_id = (
        restored_task.task_id
    )

    workspace.checkpoint = (
        restored_checkpoint
    )
    workspace.validation_result = None

    workspace.checkpoint.completed_items = [
        item
        for item in workspace.checkpoint.completed_items
        if item not in {
            "Validation passed",
            "Final review completed",
        }
    ]

    workspace.checkpoint.last_error = None

    database.save_workspace(
        workspace=workspace
    )

    return {
        "version_number": version_number,
        "message": "Workspace version restored.",
        "task": restored_task,
        "checkpoint": restored_checkpoint,
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
            update_personal_project_deliverable(
                workspace=workspace,
                code="clean_dataset",
                status="completed",
            )
    
        if (
            "Validation passed"
            not in
            workspace.checkpoint.completed_items
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