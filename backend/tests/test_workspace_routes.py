import pandas as pd
from fastapi.testclient import TestClient

import backend.app.database as database

import backend.app.workspace_routes as workspace_routes

from backend.app.models import (
    DataQualityAnalysis,
    DataQualityFinding,
    Workspace,
    WorkspaceTransformationRequest,
    DataEngineeringTask,
    DataEngineeringTaskStep,
    DataEngineeringTaskTransformationResponse,
    MissingValuesValidationResult,
    LearningEvidenceDecision,
    DataQualityAttemptResponse,
    PersonalProjectAnalysisPlan,
    WorkspaceValidationResponse,
    PersonalProjectKPIDefinition,
    PersonalProjectAnalysisResult,
    PersonalProjectDataModelPlan,
    
)

from backend.app.main import app


client = TestClient(app)


def prepare_database(tmp_path):
    database.DATABASE_PATH = (
        tmp_path / "test.db"
    )

    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )


def test_create_workspace(tmp_path):
    prepare_database(tmp_path)

    response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Data Quality",

            "usage_context": "work",
            "organization_id": "company-001",
            "data_sensitivity": "internal",

            "workspace_type": "data_engineering",
            "current_task_id": "task-001",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["learner_id"] == "learner-001"
    assert body["title"] == "Customer Data Quality"

    assert (
        body["workspace_type"]
        == "data_engineering"
    )

    assert body["workspace_id"] is not None
    assert body["mentor_session_id"] is not None

    assert (
        body["checkpoint"]["completed_items"]
        == []
    )

    assert body["usage_context"] == "work"

    assert (
        body["organization_id"]
        == "company-001"
    )

    assert (
        body["data_sensitivity"]
        == "internal"
    )


def test_list_workspaces(tmp_path):
    prepare_database(tmp_path)

    client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Data Quality",
            "workspace_type": "data_engineering",
        },
    )

    client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "SQL Practice",
            "workspace_type": "practice",
        },
    )

    response = client.get(
        "/workspaces/learner-001"
    )

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 2


def test_get_workspace(tmp_path):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Data Quality",
            "workspace_type": "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    response = client.get(
        f"/workspaces/learner-001/{workspace_id}"
    )

    assert response.status_code == 200

    body = response.json()

    assert (
        body["workspace_id"]
        == workspace_id
    )


def test_get_workspace_returns_404_for_wrong_learner(
    tmp_path,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Data Quality",
            "workspace_type": "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    response = client.get(
        f"/workspaces/wrong-learner/{workspace_id}"
    )

    assert response.status_code == 404

def test_update_workspace_checkpoint(tmp_path):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Data Quality",
            "workspace_type": "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    response = client.put(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/checkpoint"
        ),
        json={
            "checkpoint": {
                "completed_items": [
                    "Duplicate kayıtlar temizlendi.",
                    "Duplicate validation başarılı.",
                ],
                "current_focus": (
                    "age kolonundaki null değerler"
                ),
                "blocked_reason": (
                    "Imputation yöntemi seçilmedi."
                ),
                "last_error": (
                    "Null sayısı azalmadı."
                ),
                "next_actions": [
                    "age dağılımını incele",
                    "transformation seç",
                    "sonucu validate et",
                ],
            }
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert (
        body["checkpoint"]["current_focus"]
        == "age kolonundaki null değerler"
    )

    assert (
        body["checkpoint"]["last_error"]
        == "Null sayısı azalmadı."
    )


def test_resume_workspace_returns_checkpoint(
    tmp_path,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Data Quality",
            "workspace_type": "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    client.put(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/checkpoint"
        ),
        json={
            "checkpoint": {
                "completed_items": [
                    "Duplicate temizlendi."
                ],
                "current_focus": (
                    "age null değerleri"
                ),
                "blocked_reason": None,
                "last_error": (
                    "Null sayısı azalmadı."
                ),
                "next_actions": [
                    "age dağılımını incele",
                    "transformation uygula",
                ],
            }
        },
    )

    response = client.get(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/resume"
        )
    )

    assert response.status_code == 200

    body = response.json()

    assert (
        body["title"]
        == "Customer Data Quality"
    )

    assert (
        body["checkpoint"]["current_focus"]
        == "age null değerleri"
    )

    assert (
        body["next_action"]
        == "age dağılımını incele"
    )

def test_update_workspace_status_to_completed(
    tmp_path,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Data Quality",
            "workspace_type": "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    response = client.put(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/status"
        ),
        json={
            "status": "completed",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "completed"

    stored_workspace = database.get_workspace(
        workspace_id=workspace_id,
        learner_id="learner-001",
    )

    assert stored_workspace is not None
    assert stored_workspace.status == "completed"


def test_profile_workspace_data_does_not_send_sample_rows_to_ai(
    tmp_path,
    monkeypatch,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Private Dataset Test",
        
            "usage_context": "personal",
            "data_sensitivity": "public",
        
            "workspace_type": "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    captured_profile = {}

    def fake_generate_data_recommendations(
        profile: dict,
    ):
        captured_profile.update(profile)

        return DataQualityAnalysis(
            findings=[]
        )

    monkeypatch.setattr(
        workspace_routes,
        "generate_data_recommendations",
        fake_generate_data_recommendations,
    )

    monkeypatch.setattr(
        workspace_routes,
        "save_workspace_dataset",
        lambda workspace_id, content: None,
    )

    csv_content = (
        b"customer_id,name,age\n"
        b"1001,Alice,31\n"
        b"1002,Bob,29\n"
    )

    response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/data/profile"
        ),
        files={
            "file": (
                "private.csv",
                csv_content,
                "text/csv",
            )
        },
    )

    assert response.status_code == 200

    assert "sample_rows" not in captured_profile

    assert captured_profile["row_count"] == 2

    body = response.json()

    assert "sample_rows" not in body["profile"]

    assert (
        body["external_ai_allowed"]
        is True
    )

    assert (
        body["analysis_source"]
        == "local_and_ai"
    )
def test_personal_workspace_has_no_organization(
    tmp_path,
):
    prepare_database(tmp_path)

    response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Personal Practice",
            "usage_context": "personal",
            "data_sensitivity": "internal",
            "workspace_type": "practice",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["usage_context"] == "personal"

    assert body["organization_id"] is None


def test_confidential_workspace_uses_local_analysis_without_ai(
    tmp_path,
    monkeypatch,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id":
                "learner-001",

            "title":
                "Confidential Company Data",

            "usage_context":
                "work",

            "organization_id":
                "company-001",

            "data_sensitivity":
                "confidential",

            "workspace_type":
                "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()[
            "workspace_id"
        ]
    )


    ai_called = False

    def fake_generate_data_recommendations(
        profile: dict,
    ):
        nonlocal ai_called

        ai_called = True

        return DataQualityAnalysis(
            findings=[]
        )


    monkeypatch.setattr(
        workspace_routes,
        "generate_data_recommendations",
        fake_generate_data_recommendations,
    )

    monkeypatch.setattr(
        workspace_routes,
        "save_workspace_dataset",
        lambda workspace_id, content: None,
    )


    csv_content = (
        b"id,age,city\n"
        b"1,20,Amsterdam\n"
        b"2,,Rotterdam\n"
        b"2,,Rotterdam\n"
    )


    response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/data/profile"
        ),
        files={
            "file": (
                "confidential.csv",
                csv_content,
                "text/csv",
            )
        },
    )


    assert response.status_code == 200

    body = response.json()


    # External AI kesinlikle çağrılmamalı.
    assert ai_called is False

    assert (
        body["external_ai_allowed"]
        is False
    )

    assert (
        body["ai_processing_status"]
        == "blocked"
    )

    assert (
        body["analysis_source"]
        == "local"
    )


    finding_types = {
        finding["issue_type"]
        for finding
        in body["analysis"]["findings"]
    }

    assert (
        "missing_values"
        in finding_types
    )

    assert (
        "duplicate_rows"
        in finding_types
    )


    stored_workspace = (
        database.get_workspace(
            workspace_id=workspace_id,
            learner_id="learner-001",
        )
    )

    assert stored_workspace is not None

    assert (
        stored_workspace
        .dataset_analysis_source
        == "local"
    )

    assert (
        stored_workspace
        .dataset_ai_processing_status
        == "blocked"
    )

def test_confidential_workspace_finding_uses_local_mentor(
    tmp_path,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id":
                "learner-001",

            "title":
                "Confidential Dataset",

            "usage_context":
                "work",

            "organization_id":
                "company-001",

            "data_sensitivity":
                "confidential",

            "workspace_type":
                "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()[
            "workspace_id"
        ]
    )

    workspace = database.get_workspace(
        workspace_id=workspace_id,
        learner_id="learner-001",
    )

    workspace.dataset_analysis = (
        DataQualityAnalysis(
            findings=[
                DataQualityFinding(
                    issue_type=(
                        "missing_values"
                    ),
                    column="age",
                    severity="medium",
                    observation=(
                        "2 missing values found."
                    ),
                    suggested_action=(
                        "Inspect missing values."
                    ),
                )
            ]
        )
    )

    workspace.dataset_ai_processing_status = (
        "blocked"
    )

    workspace.dataset_analysis_source = (
        "local"
    )

    database.save_workspace(
        workspace
    )

    response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/data/"
            "findings/0/mentor"
        )
    )

    assert response.status_code == 200

    body = response.json()

    assert body["source"] == "local"

    assert (
        body["finding"]["column"]
        == "age"
    )

    assert (
        body["skill_status"]
        == "new"
    )

    assert (
        body["assistance_level"]
        == "GUIDE"
    )

    assert (
        "age"
        in body["mentor_response"]
    )

def test_workspace_finding_mentor_rejects_invalid_index(
    tmp_path,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id":
                "learner-001",

            "title":
                "Local Mentor Test",

            "usage_context":
                "personal",

            "data_sensitivity":
                "public",

            "workspace_type":
                "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()[
            "workspace_id"
        ]
    )

    workspace = database.get_workspace(
        workspace_id=workspace_id,
        learner_id="learner-001",
    )

    workspace.dataset_analysis = (
        DataQualityAnalysis(
            findings=[]
        )
    )

    database.save_workspace(
        workspace
    )

    response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/data/"
            "findings/99/mentor"
        )
    )

    assert response.status_code == 404

def test_confidential_workspace_plan_never_calls_ai(
    tmp_path,
    monkeypatch,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Confidential Plan Test",
            "usage_context": "work",
            "organization_id": "company-001",
            "data_sensitivity": "confidential",
            "workspace_type": "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()[
            "workspace_id"
        ]
    )

    workspace = database.get_workspace(
        workspace_id=workspace_id,
        learner_id="learner-001",
    )

    workspace.dataset_profile = {
        "row_count": 3,
        "column_count": 2,
    }

    workspace.dataset_analysis = (
        DataQualityAnalysis(
            findings=[
                DataQualityFinding(
                    issue_type="missing_values",
                    column="age",
                    severity="medium",
                    observation=(
                        "2 missing values found."
                    ),
                    suggested_action=(
                        "Inspect missing values."
                    ),
                ),
                DataQualityFinding(
                    issue_type="duplicate_rows",
                    column=None,
                    severity="medium",
                    observation=(
                        "1 duplicate row found."
                    ),
                    suggested_action=(
                        "Inspect duplicate rows."
                    ),
                ),
            ]
        )
    )

    database.save_workspace(
        workspace
    )

    ai_called = False

    def fake_ai_plan(*args, **kwargs):
        nonlocal ai_called
        ai_called = True

        raise AssertionError(
            "AI planner must not be called."
        )

    monkeypatch.setattr(
        workspace_routes,
        "generate_workspace_execution_plan",
        fake_ai_plan,
    )

    response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/plan"
        ),
        json={
            # Bilerek sahte frontend verisi.
            # Backend bunu kullanmamalı.
            "profile": {
                "fake": True,
            },
            "findings": [],
        },
    )

    assert response.status_code == 200

    assert ai_called is False

    body = response.json()

    steps = body["task"]["steps"]

    assert len(steps) == 2

    # Local plan duplicate kontrolünü önce yapar.
    assert (
        steps[0]["finding"]["issue_type"]
        == "duplicate_rows"
    )

    assert (
        steps[1]["finding"]["issue_type"]
        == "missing_values"
    )

def test_confidential_transformation_uses_local_reviewer(
    tmp_path,
    monkeypatch,
):
    prepare_database(tmp_path)

    finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation=(
            "1 missing value found."
        ),
        suggested_action=(
            "Inspect missing values."
        ),
    )

    task = DataEngineeringTask(
        task_id="task-local-001",
        title="Confidential Plan",
        steps=[
            DataEngineeringTaskStep(
                step_number=1,
                title=(
                    "age kolonundaki "
                    "eksik değerleri incele"
                ),
                finding=finding,
                status="active",
            )
        ],
        current_step_number=1,
        status="active",
    )

    workspace = Workspace(
        workspace_id="workspace-local-001",
        learner_id="learner-001",
        title="Confidential Workspace",
        usage_context="work",
        organization_id="company-001",
        data_sensitivity="confidential",
        workspace_type="data_engineering",
        current_task_id="task-local-001",
    )

    before_df = pd.DataFrame(
        {
            "age": [
                20,
                None,
            ]
        }
    )

    fake_result = (
        DataEngineeringTaskTransformationResponse(
            task=task,
            skill_name="null_analysis",
            skill_status="new",
            validation=(
                MissingValuesValidationResult(
                    column="age",
                    before_null_count=1,
                    after_null_count=1,
                    success=False,
                )
            ),
            evidence=LearningEvidenceDecision(
                is_evidence=True,
                evidence_type="application",
                success=False,
                note=(
                    "Null count did not decrease."
                ),
            ),
        )
    )

    monkeypatch.setattr(
        database,
        "get_workspace",
        lambda **kwargs: workspace,
    )

    monkeypatch.setattr(
        database,
        "get_data_engineering_task",
        lambda **kwargs: task,
    )

    monkeypatch.setattr(
        workspace_routes,
        "load_workspace_working_dataframe",
        lambda workspace_id: before_df,
    )

    monkeypatch.setattr(
        workspace_routes,
        "create_workspace_version",
        lambda **kwargs: 1,
    )

    monkeypatch.setattr(
        workspace_routes,
        "delete_workspace_version",
        lambda **kwargs: None,
    )

    monkeypatch.setattr(
        database,
        "save_workspace",
        lambda workspace: None,
    )


    local_called = False
    ai_called = False


    def fake_local_review(**kwargs):
        nonlocal local_called

        local_called = True

        return fake_result


    def fake_ai_review(**kwargs):
        nonlocal ai_called

        ai_called = True

        raise AssertionError(
            "External AI reviewer must not be called."
        )


    monkeypatch.setattr(
        workspace_routes,
        "review_task_transformation_locally",
        fake_local_review,
    )

    monkeypatch.setattr(
        workspace_routes,
        "review_data_engineering_task_transformation",
        fake_ai_review,
    )


    result = (
        workspace_routes.transform_workspace_data(
            learner_id="learner-001",
            workspace_id="workspace-local-001",
            request=WorkspaceTransformationRequest(
                after_rows=[
                    {
                        "age": 20,
                    },
                    {
                        "age": None,
                    },
                ]
            ),
        )
    )


    assert local_called is True

    assert ai_called is False

    assert (
        result.validation.success
        is False
    )

def test_confidential_workspace_attempt_never_calls_external_ai(
    tmp_path,
    monkeypatch,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Secure Attempt Test",
            "usage_context": "work",
            "organization_id": "company-001",
            "data_sensitivity": "confidential",
            "workspace_type": "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()[
            "workspace_id"
        ]
    )

    workspace = database.get_workspace(
        workspace_id=workspace_id,
        learner_id="learner-001",
    )

    workspace.dataset_analysis = (
        DataQualityAnalysis(
            findings=[
                DataQualityFinding(
                    issue_type="missing_values",
                    column="age",
                    severity="medium",
                    observation=(
                        "2 missing values found."
                    ),
                    suggested_action=(
                        "Inspect missing values."
                    ),
                )
            ]
        )
    )

    workspace.dataset_ai_processing_status = (
        "blocked"
    )

    workspace.dataset_analysis_source = (
        "local"
    )

    database.save_workspace(
        workspace
    )

    ai_called = False

    def fake_ai_attempt(**kwargs):
        nonlocal ai_called

        ai_called = True

        raise AssertionError(
            "External AI attempt reviewer "
            "must not be called."
        )

    monkeypatch.setattr(
        workspace_routes,
        "review_data_quality_attempt",
        fake_ai_attempt,
    )

    response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/data/"
            "findings/0/attempt"
        ),
        json={
            "attempt": (
                "Age kolonundaki null değerleri "
                "inceledim."
            )
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert ai_called is False

    assert body["source"] == "local"

    assert (
        body["skill_name"]
        == "null_analysis"
    )

    assert (
        body["evidence"]["is_evidence"]
        is False
    )

    assert (
        body["evidence"]["success"]
        is None
    )

def test_personal_public_workspace_attempt_can_use_external_ai(
    tmp_path,
    monkeypatch,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Personal Public Attempt",
            "usage_context": "personal",
            "data_sensitivity": "public",
            "workspace_type": "data_engineering",
        },
    )

    workspace_id = (
        create_response.json()[
            "workspace_id"
        ]
    )

    workspace = database.get_workspace(
        workspace_id=workspace_id,
        learner_id="learner-001",
    )

    workspace.dataset_analysis = (
        DataQualityAnalysis(
            findings=[
                DataQualityFinding(
                    issue_type="missing_values",
                    column="age",
                    severity="medium",
                    observation=(
                        "2 missing values found."
                    ),
                    suggested_action=(
                        "Inspect missing values."
                    ),
                )
            ]
        )
    )

    workspace.dataset_ai_processing_status = (
        "allowed"
    )

    workspace.dataset_analysis_source = (
        "local_and_ai"
    )

    database.save_workspace(
        workspace
    )

    ai_called = False
    captured_finding = None
    captured_attempt = None

    def fake_ai_attempt(
        learner_id,
        finding,
        attempt,
    ):
        nonlocal ai_called
        nonlocal captured_finding
        nonlocal captured_attempt

        ai_called = True
        captured_finding = finding
        captured_attempt = attempt

        return DataQualityAttemptResponse(
            mentor_response=(
                "Evet, bu uygun bir adım."
            ),
            skill_name="null_analysis",
            skill_status="learning",
            evidence=LearningEvidenceDecision(
                is_evidence=True,
                evidence_type="application",
                success=True,
                note=(
                    "Junior missing values "
                    "üzerinde anlamlı bir kontrol yaptı."
                ),
            ),
        )

    monkeypatch.setattr(
        workspace_routes,
        "review_data_quality_attempt",
        fake_ai_attempt,
    )

    response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/data/"
            "findings/0/attempt"
        ),
        json={
            "attempt": (
                "Age kolonundaki null "
                "değerleri kontrol ettim."
            )
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert ai_called is True

    assert (
        body["source"]
        == "external_ai"
    )

    assert (
        body["evidence"]["success"]
        is True
    )

    # Finding frontend'den değil,
    # backend workspace state'inden geldi.
    assert (
        captured_finding.column
        == "age"
    )

    assert (
        captured_finding.issue_type
        == "missing_values"
    )

    assert captured_attempt == (
        "Age kolonundaki null "
        "değerleri kontrol ettim."
    )

def test_create_personal_workspace_saves_project_type(
    tmp_path,
):
    prepare_database(tmp_path)

    response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Housing Dashboard",
            "usage_context": "personal",
            "project_type": "bi_dashboard",
            "task_brief": (
                "Analyze housing price trends."
            ),
            "desired_outcome": (
                "Power BI-ready dashboard."
            ),
            "workspace_type": "data_engineering",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["usage_context"] == "personal"

    assert (
        body["project_type"]
        == "bi_dashboard"
    )

def test_bi_dashboard_project_gets_deliverables(
    tmp_path,
):
    prepare_database(tmp_path)

    response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Housing Dashboard",
            "usage_context": "personal",
            "project_type": "bi_dashboard",
            "task_brief": (
                "Analyze housing price trends."
            ),
            "desired_outcome": (
                "Create a Power BI dashboard."
            ),
            "workspace_type": "data_engineering",
        },
    )

    assert response.status_code == 200

    body = response.json()

    deliverables = (
        body["project_deliverables"]
    )

    deliverable_codes = [
        item["code"]
        for item in deliverables
    ]

    assert deliverable_codes == [
        "data_profile",
        "clean_dataset",
        "data_model",
        "kpi_definitions",
        "bi_ready_dataset",
        "analysis",
        "dashboard",
        "insight_summary",
        "documentation",
    ]

    assert all(
        item["status"] == "pending"
        for item in deliverables
    )

def test_personal_dataset_profile_completes_deliverable(
    tmp_path,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Housing Dashboard",
            "usage_context": "personal",
            "project_type": "bi_dashboard",
            "task_brief": (
                "Analyze housing price trends."
            ),
            "desired_outcome": (
                "Create a Power BI dashboard."
            ),
            "workspace_type": "data_engineering",
        },
    )

    assert create_response.status_code == 200

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    profile_response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/data/profile"
        ),
        files={
            "file": (
                "housing.csv",
                (
                    "region,year,price\n"
                    "Den Haag,2025,450000\n"
                    "Rotterdam,2025,390000\n"
                ),
                "text/csv",
            )
        },
    )

    assert profile_response.status_code == 200

    workspace_response = client.get(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}"
        )
    )

    assert workspace_response.status_code == 200

    workspace = workspace_response.json()

    deliverables = {
        item["code"]: item
        for item in workspace[
            "project_deliverables"
        ]
    }

    assert (
        deliverables["data_profile"]["status"]
        == "completed"
    )

    assert (
        deliverables["clean_dataset"]["status"]
        == "in_progress"
    )

def test_successful_personal_validation_completes_clean_dataset(
    tmp_path,
    monkeypatch,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Housing Dashboard",
            "usage_context": "personal",
            "project_type": "bi_dashboard",
            "task_brief": (
                "Analyze housing data."
            ),
            "desired_outcome": (
                "Create a dashboard."
            ),
            "workspace_type": "data_engineering",
        },
    )

    assert create_response.status_code == 200

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    finding = DataQualityFinding(
        issue_type="duplicate_rows",
        column=None,
        severity="high",
        observation=(
            "1 duplicate row found."
        ),
        suggested_action=(
            "Remove duplicate rows."
        ),
    )

    task = DataEngineeringTask(
        task_id="task-clean-001",
        title="Clean housing data",
        steps=[
            DataEngineeringTaskStep(
                step_number=1,
                title="Remove duplicate rows",
                finding=finding,
                status="completed",
            )
        ],
        current_step_number=1,
        status="completed",
    )

    database.save_data_engineering_task(
        learner_id="learner-001",
        task=task,
    )

    workspace = database.get_workspace(
        workspace_id=workspace_id,
        learner_id="learner-001",
    )

    assert workspace is not None

    workspace.current_task_id = (
        task.task_id
    )

    database.save_workspace(
        workspace
    )

    source_df = pd.DataFrame(
        [
            {
                "region": "Den Haag",
                "price": 450000,
            },
            {
                "region": "Rotterdam",
                "price": 390000,
            },
            {
                "region": "Rotterdam",
                "price": 390000,
            },
        ]
    )

    working_df = pd.DataFrame(
        [
            {
                "region": "Den Haag",
                "price": 450000,
            },
            {
                "region": "Rotterdam",
                "price": 390000,
            },
        ]
    )

    monkeypatch.setattr(
        workspace_routes,
        "load_workspace_source_dataframe",
        lambda workspace_id: source_df,
    )

    monkeypatch.setattr(
        workspace_routes,
        "load_workspace_working_dataframe",
        lambda workspace_id: working_df,
    )

    response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/validate"
        )
    )

    assert response.status_code == 200
    assert response.json()["passed"] is True

    workspace_response = client.get(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}"
        )
    )

    assert workspace_response.status_code == 200

    deliverables = {
        item["code"]: item
        for item in workspace_response.json()[
            "project_deliverables"
        ]
    }

    assert (
        deliverables["clean_dataset"]["status"]
        == "completed"
    )

    assert (
        deliverables["data_model"]["status"]
        == "in_progress"
    )

    assert (
        deliverables["analysis"]["status"]
        == "pending"
    )

    analysis_plan = (
        workspace_response.json()[
            "analysis_plan"
        ]
    )
    
    assert analysis_plan is not None
    
    assert (
        analysis_plan["measure_candidates"]
        == ["price"]
    )
    
    assert (
        analysis_plan["dimension_candidates"]
        == ["region"]
    )
    
    assert (
        analysis_plan["source"]
        == "local"
    )

def test_run_personal_analysis_completes_analysis_deliverable(
    tmp_path,
    monkeypatch,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Analysis",
            "usage_context": "personal",
            "project_type": "bi_dashboard",
            "task_brief": (
                "Analyze customer age by city."
            ),
            "desired_outcome": (
                "Create a BI dashboard."
            ),
            "workspace_type": "data_engineering",
        },
    )

    assert create_response.status_code == 200

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    workspace = database.get_workspace(
        workspace_id=workspace_id,
        learner_id="learner-001",
    )

    assert workspace is not None

    workspace.validation_result = (
        WorkspaceValidationResponse(
            passed=True,
            source_row_count=4,
            working_row_count=4,
            checks=[],
        )
    )

    workspace.analysis_plan = (
        PersonalProjectAnalysisPlan(
            measure_candidates=[
                "age",
            ],
            dimension_candidates=[
                "city",
            ],
            time_candidates=[],
            suggested_questions=[
                "How does age vary by city?",
            ],
            source="local",
        )
    )

    # Analysis is downstream of model/KPI/BI model.
    for deliverable in (
        workspace.project_deliverables
    ):
        if deliverable.code in {
            "data_profile",
            "clean_dataset",
            "data_model",
            "kpi_definitions",
            "bi_ready_dataset",
        }:
            deliverable.status = "completed"

        if deliverable.code == "analysis":
            deliverable.status = "in_progress"

    database.save_workspace(
        workspace=workspace
    )

    working_df = pd.DataFrame(
        {
            "age": [
                31.0,
                29.5,
                28.0,
                29.5,
            ],
            "city": [
                "Den Haag",
                "Rotterdam",
                "Utrecht",
                "Delft",
            ],
        }
    )

    monkeypatch.setattr(
        workspace_routes,
        "load_workspace_working_dataframe",
        lambda workspace_id: working_df,
    )

    response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/analysis/run"
        ),
        json={
            "measure": "age",
            "dimension": "city",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["measure"] == "age"
    assert body["dimension"] == "city"

    assert body["overall"] == {
        "count": 4,
        "mean": 29.5,
        "min": 28.0,
        "max": 31.0,
    }

    assert (
        len(body["grouped_results"])
        == 4
    )

    assert body["source"] == "local"

    workspace_response = client.get(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}"
        )
    )

    assert workspace_response.status_code == 200

    updated_workspace = (
        workspace_response.json()
    )

    deliverables = {
        item["code"]: item
        for item in updated_workspace[
            "project_deliverables"
        ]
    }

    assert (
        deliverables["analysis"]["status"]
        == "completed"
    )

    assert (
        deliverables[
            "dashboard"
        ]["status"]
        == "in_progress"
    )

    assert (
        updated_workspace[
            "analysis_result"
        ]["measure"]
        == "age"
    )

    assert (
        updated_workspace[
            "analysis_result"
        ]["dimension"]
        == "city"
    )

    assert (
        updated_workspace[
            "kpi_definitions"
        ]
        == []
    )

def test_select_personal_kpis_completes_kpi_deliverable(
    tmp_path,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Dashboard",
            "usage_context": "personal",
            "project_type": "bi_dashboard",
            "task_brief": (
                "Analyze customer age by city."
            ),
            "workspace_type": "data_engineering",
        },
    )

    assert create_response.status_code == 200

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    workspace = database.get_workspace(
        workspace_id=workspace_id,
        learner_id="learner-001",
    )

    assert workspace is not None

    workspace.data_model_plan = (
        PersonalProjectDataModelPlan(
            model_type="star_schema_candidate",
            base_table="fact_test_quality",
            grain=(
                "One row per validated "
                "source record."
            ),
            dimensions=[
                "city",
            ],
            time_dimension=None,
            measures=[],
            recommended_dimension_tables=[
                "dim_city",
            ],
            source="local",
        )
    )


    workspace.kpi_candidates = [
        PersonalProjectKPIDefinition(
            code="average_age",
            title="Average age",
            measure="age",
            aggregation="mean",
            dimension=None,
            description=(
                "Average age across dataset."
            ),
            source="local",
        ),
        PersonalProjectKPIDefinition(
            code="average_age_by_city",
            title="Average age by city",
            measure="age",
            aggregation="mean",
            dimension="city",
            description=(
                "Average age by city."
            ),
            source="local",
        ),
    ]

    for deliverable in (
        workspace.project_deliverables
    ):
        if deliverable.code in {
            "data_profile",
            "clean_dataset",
            "data_model",
        }:
            deliverable.status = "completed"
    
        if (
            deliverable.code
            == "kpi_definitions"
        ):
            deliverable.status = "in_progress"

    database.save_workspace(
        workspace=workspace
    )

    response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/kpis/select"
        ),
        json={
            "codes": [
                "average_age",
                "average_age_by_city",
            ]
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert [
        item["code"]
        for item in body
    ] == [
        "average_age",
        "average_age_by_city",
    ]

    workspace_response = client.get(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}"
        )
    )

    updated_workspace = (
        workspace_response.json()
    )

    deliverables = {
        item["code"]: item
        for item in updated_workspace[
            "project_deliverables"
        ]
    }

    assert (
        deliverables[
            "kpi_definitions"
        ]["status"]
        == "completed"
    )

    assert (
        deliverables[
            "bi_ready_dataset"
        ]["status"]
        == "in_progress"
    )

    assert len(
        updated_workspace[
            "kpi_definitions"
        ]
    ) == 2


def test_build_personal_data_model_completes_deliverable(
    tmp_path,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Dashboard",
            "usage_context": "personal",
            "project_type": "bi_dashboard",
            "task_brief": (
                "Analyze customer age by city."
            ),
            "workspace_type": "data_engineering",
        },
    )

    assert create_response.status_code == 200

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    workspace = database.get_workspace(
        workspace_id=workspace_id,
        learner_id="learner-001",
    )

    assert workspace is not None

    workspace.dataset_filename = (
        "test_quality.csv"
    )

    workspace.analysis_plan = (
        PersonalProjectAnalysisPlan(
            measure_candidates=[
                "age",
            ],
            dimension_candidates=[
                "city",
            ],
            time_candidates=[],
            suggested_questions=[
                "How does age vary by city?",
            ],
            source="local",
        )
    )


    for deliverable in (
        workspace.project_deliverables
    ):
        if deliverable.code in {
            "data_profile",
            "clean_dataset",
        }:
            deliverable.status = "completed"

        if deliverable.code == "data_model":
            deliverable.status = "in_progress"

    database.save_workspace(
        workspace=workspace
    )

    response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/data-model/build"
        )
    )

    assert response.status_code == 200

    body = response.json()

    assert (
        body["model_type"]
        == "star_schema_candidate"
    )

    assert (
        body["base_table"]
        == "fact_test_quality"
    )

    assert (
        body["dimensions"]
        == ["city"]
    )

    assert [
        item["code"]
        for item in body["measures"]
    ] == [
        "measure_age",
    ]

    assert (
        body["measures"][0][
            "aggregation"
        ]
        is None
    )

    assert (
        body[
            "recommended_dimension_tables"
        ]
        == ["dim_city"]
    )

    workspace_response = client.get(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}"
        )
    )

    assert workspace_response.status_code == 200

    updated_workspace = (
        workspace_response.json()
    )

    deliverables = {
        item["code"]: item
        for item in updated_workspace[
            "project_deliverables"
        ]
    }

    assert (
        deliverables[
            "data_model"
        ]["status"]
        == "completed"
    )

    assert (
        deliverables[
            "kpi_definitions"
        ]["status"]
        == "in_progress"
    )

    assert (
        updated_workspace[
            "data_model_plan"
        ]["base_table"]
        == "fact_test_quality"
    )

    studio = updated_workspace[
        "data_model_studio"
    ]

    assert studio is not None

    assert [
        table["name"]
        for table in studio["tables"]
    ] == [
        "fact_test_quality",
        "dim_city",
    ]

    assert (
        studio["tables"][0]["table_type"]
        == "fact"
    )

    assert (
        studio["tables"][1]["table_type"]
        == "dimension"
    )

    assert len(
        studio["relationships"]
    ) == 1

    assert (
        studio["relationships"][0][
            "from_table"
        ]
        == "fact_test_quality"
    )

    assert (
        studio["relationships"][0][
            "from_column"
        ]
        == "city"
    )

    assert (
        studio["relationships"][0][
            "to_table"
        ]
        == "dim_city"
    )

    assert (
        studio["relationships"][0][
            "to_column"
        ]
        == "city"
    )

def test_add_user_workbench_operation_is_persisted(
tmp_path,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Preparation",
            "usage_context": "personal",
            "project_type": "data_engineering",
            "task_brief": (
                "Prepare customer data."
            ),
            "workspace_type": "data_engineering",
        },
    )

    assert create_response.status_code == 200

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/workbench/operations"
        ),
        json={
            "title": "Split full_name",
            "goal": (
                "Create first_name and "
                "last_name columns."
            ),
            "operation_type": "transform",
            "source_columns": [
                "full_name",
            ],
            "expected_columns": [
                "first_name",
                "last_name",
            ],
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["operation_id"].startswith(
        "user-"
    )

    assert body["title"] == (
        "Split full_name"
    )

    assert body["goal"] == (
        "Create first_name and "
        "last_name columns."
    )

    assert (
        body["operation_type"]
        == "transform"
    )

    assert body["origin"] == "user"
    assert body["status"] == "active"

    assert body["source_columns"] == [
        "full_name",
    ]

    assert body["expected_columns"] == [
        "first_name",
        "last_name",
    ]

    assert body["code"] is None

    workspace_response = client.get(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}"
        )
    )

    assert workspace_response.status_code == 200

    updated_workspace = (
        workspace_response.json()
    )

    operations = updated_workspace[
        "workbench_operations"
    ]

    assert len(operations) == 1

    assert (
        operations[0]["operation_id"]
        == body["operation_id"]
    )

    assert (
        operations[0]["title"]
        == "Split full_name"
    )

    assert (
        operations[0]["origin"]
        == "user"
    )

    assert (
        operations[0]["status"]
        == "active"
    )

    assert (
        updated_workspace[
            "workbench_active_operation_id"
        ]
        == body["operation_id"]
    )

def test_profile_creates_data_quality_workbench_operations(
    tmp_path,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Quality Project",
            "usage_context": "personal",
            "project_type": "data_engineering",
            "task_brief": (
                "Prepare customer data."
            ),
            "workspace_type": "data_engineering",
        },
    )

    assert create_response.status_code == 200

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    csv_content = (
        "customer_id,name,age,city\n"
        "1,Alice,30,Den Haag\n"
        "2,Bob,,Rotterdam\n"
        "2,Bob,,Rotterdam\n"
    )

    profile_response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/data/profile"
        ),
        files={
            "file": (
                "customers.csv",
                csv_content,
                "text/csv",
            )
        },
    )

    assert profile_response.status_code == 200

    workspace_response = client.get(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}"
        )
    )

    assert workspace_response.status_code == 200

    workspace = workspace_response.json()

    operations = workspace[
        "workbench_operations"
    ]

    assert len(operations) >= 2

    quality_operations = [
        operation
        for operation in operations
        if operation["origin"] == "data_quality"
    ]

    assert len(quality_operations) >= 2

    titles = {
        operation["title"]
        for operation in quality_operations
    }

    assert "Handle duplicate rows" in titles

    assert (
        "Handle missing values in age"
        in titles
    )

    active_operations = [
        operation
        for operation in operations
        if operation["status"] == "active"
    ]

    assert len(active_operations) == 1

    assert (
        workspace[
            "workbench_active_operation_id"
        ]
        == active_operations[0][
            "operation_id"
        ]
    )

def test_workbench_custom_transformation_can_change_schema(
    tmp_path,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Customer Preparation",
            "usage_context": "personal",
            "project_type": "data_engineering",
            "task_brief": (
                "Prepare customer data."
            ),
            "workspace_type": "data_engineering",
        },
    )

    assert create_response.status_code == 200

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    profile_response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/data/profile"
        ),
        files={
            "file": (
                "customers.csv",
                (
                    "customer_id,full_name\n"
                    "1,Alice Smith\n"
                    "2,Bob Jones\n"
                ),
                "text/csv",
            )
        },
    )

    assert profile_response.status_code == 200

    first_operation_response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}"
            "/workbench/operations"
        ),
        json={
            "title": "Split full_name",
            "goal": (
                "Create first_name and "
                "last_name columns."
            ),
            "operation_type": "transform",
            "source_columns": [
                "full_name",
            ],
            "expected_columns": [
                "first_name",
                "last_name",
            ],
        },
    )

    assert (
        first_operation_response.status_code
        == 200
    )

    first_operation = (
        first_operation_response.json()
    )

    assert (
        first_operation["status"]
        == "active"
    )

    second_operation_response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}"
            "/workbench/operations"
        ),
        json={
            "title": "Create display_name",
            "goal": (
                "Create a display_name column."
            ),
            "operation_type": "custom",
            "source_columns": [
                "first_name",
                "last_name",
            ],
            "expected_columns": [
                "display_name",
            ],
        },
    )

    assert (
        second_operation_response.status_code
        == 200
    )

    second_operation = (
        second_operation_response.json()
    )

    assert (
        second_operation["status"]
        == "pending"
    )

    transform_response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}"
            "/workbench/transform"
        ),
        json={
            "operation_id": (
                first_operation[
                    "operation_id"
                ]
            ),
            "code": (
                'df[["first_name", '
                '"last_name"]] = '
                'df["full_name"].str.split('
                '" ", n=1, expand=True)'
            ),
            "after_rows": [
                {
                    "customer_id": 1,
                    "full_name": (
                        "Alice Smith"
                    ),
                    "first_name": "Alice",
                    "last_name": "Smith",
                },
                {
                    "customer_id": 2,
                    "full_name": (
                        "Bob Jones"
                    ),
                    "first_name": "Bob",
                    "last_name": "Jones",
                },
            ],
        },
    )

    assert transform_response.status_code == 200

    body = transform_response.json()

    assert body["schema_changed"] is True

    assert body["before_row_count"] == 2
    assert body["after_row_count"] == 2

    assert (
        body["operation"]["status"]
        == "completed"
    )

    assert (
        body["operation"]["code"]
        is not None
    )

    assert (
        body["active_operation_id"]
        == second_operation["operation_id"]
    )

    assert body["working_data"]["columns"] == [
        "customer_id",
        "full_name",
        "first_name",
        "last_name",
    ]

    working_response = client.get(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/data/working"
        )
    )

    assert working_response.status_code == 200

    working = working_response.json()

    assert working["row_count"] == 2

    assert "first_name" in working["columns"]
    assert "last_name" in working["columns"]

    workspace_response = client.get(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}"
        )
    )

    assert workspace_response.status_code == 200

    workspace = workspace_response.json()

    operations = workspace[
        "workbench_operations"
    ]

    completed_operation = next(
        operation
        for operation in operations
        if (
            operation["operation_id"]
            == first_operation["operation_id"]
        )
    )

    next_operation = next(
        operation
        for operation in operations
        if (
            operation["operation_id"]
            == second_operation["operation_id"]
        )
    )

    assert (
        completed_operation["status"]
        == "completed"
    )

    assert next_operation["status"] == "active"

    assert (
        workspace[
            "workbench_active_operation_id"
        ]
        == second_operation["operation_id"]
    )

def test_workbench_quality_operation_requires_real_validation(
    tmp_path,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Quality Workbench",
            "usage_context": "personal",
            "project_type": "data_quality",
            "task_brief": (
                "Resolve customer data quality "
                "problems."
            ),
            "workspace_type": "data_engineering",
        },
    )

    assert create_response.status_code == 200

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    profile_response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/data/profile"
        ),
        files={
            "file": (
                "customers.csv",
                (
                    "customer_id,name,age\n"
                    "1,Alice,30\n"
                    "2,Bob,\n"
                    "3,Carol,40\n"
                ),
                "text/csv",
            )
        },
    )

    assert profile_response.status_code == 200

    workspace_response = client.get(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}"
        )
    )

    assert workspace_response.status_code == 200

    workspace = workspace_response.json()

    quality_operation = next(
        operation
        for operation
        in workspace["workbench_operations"]
        if (
            operation["origin"]
            == "data_quality"
            and operation["source_columns"]
            == ["age"]
        )
    )

    assert (
        quality_operation["status"]
        == "active"
    )

    failed_response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}"
            "/workbench/transform"
        ),
        json={
            "operation_id": (
                quality_operation[
                    "operation_id"
                ]
            ),
            "code": (
                "# intentionally leaves "
                "missing age unchanged"
            ),
            "after_rows": [
                {
                    "customer_id": 1,
                    "name": "Alice",
                    "age": 30,
                },
                {
                    "customer_id": 2,
                    "name": "Bob",
                    "age": None,
                },
                {
                    "customer_id": 3,
                    "name": "Carol",
                    "age": 40,
                },
            ],
        },
    )

    assert failed_response.status_code == 400

    successful_response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}"
            "/workbench/transform"
        ),
        json={
            "operation_id": (
                quality_operation[
                    "operation_id"
                ]
            ),
            "code": (
                'df["age"] = '
                'df["age"].fillna('
                'df["age"].median())'
            ),
            "after_rows": [
                {
                    "customer_id": 1,
                    "name": "Alice",
                    "age": 30,
                },
                {
                    "customer_id": 2,
                    "name": "Bob",
                    "age": 35,
                },
                {
                    "customer_id": 3,
                    "name": "Carol",
                    "age": 40,
                },
            ],
        },
    )

    assert successful_response.status_code == 200

    body = successful_response.json()

    assert (
        body["operation"]["status"]
        == "completed"
    )

    assert (
        body["operation"]["origin"]
        == "data_quality"
    )

    working_response = client.get(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/data/working"
        )
    )

    assert working_response.status_code == 200

    rows = working_response.json()["rows"]

    assert all(
        row["age"] is not None
        for row in rows
    )

def test_workbench_submit_version_and_restore_flow(
    tmp_path,
):
    prepare_database(tmp_path)

    create_response = client.post(
        "/workspaces",
        json={
            "learner_id": "learner-001",
            "title": "Workbench Version Test",
            "usage_context": "personal",
            "project_type": "data_engineering",
            "task_brief": "Prepare customer data.",
            "workspace_type": "data_engineering",
        },
    )

    assert create_response.status_code == 200

    workspace_id = (
        create_response.json()["workspace_id"]
    )

    profile_response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/data/profile"
        ),
        files={
            "file": (
                "customers.csv",
                (
                    "customer_id,full_name\n"
                    "1,Alice Smith\n"
                    "2,Bob Jones\n"
                ),
                "text/csv",
            )
        },
    )

    assert profile_response.status_code == 200

    operation_response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}"
            "/workbench/operations"
        ),
        json={
            "title": "Split full_name",
            "goal": (
                "Create first_name and "
                "last_name columns."
            ),
            "operation_type": "transform",
            "source_columns": [
                "full_name",
            ],
            "expected_columns": [
                "first_name",
                "last_name",
            ],
        },
    )

    assert operation_response.status_code == 200

    operation = operation_response.json()

    assert operation["status"] == "active"

    transform_response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}"
            "/workbench/transform"
        ),
        json={
            "operation_id": (
                operation["operation_id"]
            ),
            "code": (
                'df[["first_name", '
                '"last_name"]] = '
                'df["full_name"].str.split('
                '" ", n=1, expand=True)'
            ),
            "after_rows": [
                {
                    "customer_id": 1,
                    "full_name": "Alice Smith",
                    "first_name": "Alice",
                    "last_name": "Smith",
                },
                {
                    "customer_id": 2,
                    "full_name": "Bob Jones",
                    "first_name": "Bob",
                    "last_name": "Jones",
                },
            ],
        },
    )

    assert transform_response.status_code == 200

    transformed = transform_response.json()

    assert (
        transformed["operation"]["status"]
        == "completed"
    )

    rollback_version_number = (
        transformed["operation"][
            "rollback_version_number"
        ]
    )

    assert rollback_version_number == 1

    versions_response = client.get(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/versions"
        )
    )

    assert versions_response.status_code == 200

    versions = versions_response.json()

    assert len(versions) == 1

    version = versions[0]

    assert version["version_number"] == 1

    assert (
        version["operation_id"]
        == operation["operation_id"]
    )

    assert (
        version["operation_title"]
        == "Split full_name"
    )

    assert (
        version["operation_type"]
        == "transform"
    )

    assert version["schema_changed"] is True

    working_after_transform = client.get(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/data/working"
        )
    ).json()

    assert "first_name" in (
        working_after_transform["columns"]
    )

    assert "last_name" in (
        working_after_transform["columns"]
    )

    restore_response = client.post(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/versions/"
            f"{rollback_version_number}/restore"
        )
    )

    assert restore_response.status_code == 200

    restored = restore_response.json()

    assert restored["version_number"] == 1

    assert restored["working_data"]["columns"] == [
        "customer_id",
        "full_name",
    ]

    restored_operation = next(
        item
        for item
        in restored["workbench_operations"]
        if (
            item["operation_id"]
            == operation["operation_id"]
        )
    )

    assert (
        restored_operation["status"]
        == "active"
    )

    assert restored_operation["code"] is None

    assert (
        restored[
            "workbench_active_operation_id"
        ]
        == operation["operation_id"]
    )

    working_after_restore = client.get(
        (
            f"/workspaces/learner-001/"
            f"{workspace_id}/data/working"
        )
    ).json()

    assert (
        working_after_restore["columns"]
        == [
            "customer_id",
            "full_name",
        ]
    )