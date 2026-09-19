import backend.app.database as database

from backend.app.local_data_quality_mentor_service import (
    build_local_mentor_response,
    get_local_assistance_level,
    review_task_transformation_locally,
)

import pandas as pd

from backend.app.models import (
    DataQualityFinding,
    DataEngineeringTask,
    DataEngineeringTaskStep,
)

def test_new_skill_uses_guide():

    result = get_local_assistance_level(
        "new"
    )

    assert result == "GUIDE"


def test_practicing_skill_uses_nudge():

    result = get_local_assistance_level(
        "practicing"
    )

    assert result == "NUDGE"


def test_missing_values_guidance_uses_column():

    finding = DataQualityFinding(
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

    response = build_local_mentor_response(
        finding=finding,
        skill_status="new",
    )

    assert "age" in response

    assert (
        "İlk adım:"
        in response
    )


def test_duplicate_guidance_is_local_and_specific():

    finding = DataQualityFinding(
        issue_type="duplicate_rows",
        column=None,
        severity="medium",
        observation=(
            "3 duplicate rows found."
        ),
        suggested_action=(
            "Inspect duplicate rows."
        ),
    )

    response = build_local_mentor_response(
        finding=finding,
        skill_status="learning",
    )

    assert "duplicate" in response.lower()

    assert (
        "doğrula"
        in response
    )


def test_suspicious_values_do_not_claim_error():

    finding = DataQualityFinding(
        issue_type="suspicious_values",
        column="age",
        severity="low",
        observation=(
            "Possible outlier values detected."
        ),
        suggested_action=(
            "Review suspicious values."
        ),
    )

    response = build_local_mentor_response(
        finding=finding,
        skill_status="practicing",
    )

    assert "İpucu:" in response

    assert (
        "business rule"
        in response
    )

def test_local_task_transformation_does_not_need_ai(
    tmp_path,
    monkeypatch,
):

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

    finding = DataQualityFinding(
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

    task = DataEngineeringTask(
        task_id="task-local-001",
        title="Local Data Quality Plan",
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

    before_df = pd.DataFrame(
        {
            "age": [
                20,
                None,
                None,
            ]
        }
    )

    after_df = pd.DataFrame(
        {
            "age": [
                20,
                21,
                None,
            ]
        }
    )

    result = (
        review_task_transformation_locally(
            learner_id="learner-001",
            task=task,
            before_df=before_df,
            after_df=after_df,
        )
    )

    assert (
        result.validation.success
        is True
    )

    assert (
        result.validation.before_null_count
        == 2
    )

    assert (
        result.validation.after_null_count
        == 1
    )

    assert result.evidence.success is True

    assert (
        result.skill_name
        == "null_analysis"
    )

    assert (
        result.task.status
        == "completed"
    )