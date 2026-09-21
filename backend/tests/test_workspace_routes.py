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

    assert "clean_dataset" in deliverable_codes
    assert "kpi_definitions" in deliverable_codes
    assert "data_model" in deliverable_codes
    assert "bi_ready_dataset" in deliverable_codes
    assert "dashboard" in deliverable_codes

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
        deliverables["analysis"]["status"]
        == "in_progress"
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

    # Analysis aşamasını aktif duruma getiriyoruz.
    for deliverable in (
        workspace.project_deliverables
    ):
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

    kpi_candidates = (
        updated_workspace[
            "kpi_candidates"
        ]
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
            "kpi_definitions"
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

    assert len(kpi_candidates) == 5

    assert [
        item["code"]
        for item in kpi_candidates
    ] == [
        "average_age",
        "count_age",
        "minimum_age",
        "maximum_age",
        "average_age_by_city",
    ]

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

    workspace.analysis_result = (
        PersonalProjectAnalysisResult(
            measure="age",
            dimension="city",
            overall={
                "count": 4,
                "mean": 29.5,
                "min": 28.0,
                "max": 31.0,
            },
            grouped_results=[],
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
        if deliverable.code == "analysis":
            deliverable.status = "completed"

        if deliverable.code == "kpi_definitions":
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
            "data_model"
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

    workspace.kpi_definitions = [
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
            "analysis",
            "kpi_definitions",
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
        "average_age",
        "average_age_by_city",
    ]

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
            "bi_ready_dataset"
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