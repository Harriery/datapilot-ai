from backend.app.models import (
    DataEngineeringTask,
    DataEngineeringTaskStep,
    DataQualityFinding,
    MissingValuesValidationResult,
    DuplicateRowsValidationResult,
)

from backend.app.task_service import (
    get_current_task_step,
    complete_current_task_step,
    apply_validation_result_to_task,
    review_current_task_transformation,
)


import pandas as pd

def test_get_current_task_step_returns_correct_step():

    first_finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="age kolonunda eksik değer var.",
        suggested_action="Eksik değerleri inceleyin.",
    )

    second_finding = DataQualityFinding(
        issue_type="duplicate_rows",
        column=None,
        severity="medium",
        observation="Duplicate satırlar var.",
        suggested_action="Duplicate satırları inceleyin.",
    )

    first_step = DataEngineeringTaskStep(
        step_number=1,
        title="Missing values problemini çöz",
        finding=first_finding,
        status="completed",
    )

    second_step = DataEngineeringTaskStep(
        step_number=2,
        title="Duplicate rows problemini çöz",
        finding=second_finding,
        status="active",
    )

    task = DataEngineeringTask(
        task_id="task-001",
        title="Dataset problemlerini çöz",
        steps=[
            first_step,
            second_step,
        ],
        current_step_number=2,
        status="active",
    )

    result = get_current_task_step(task)

    assert result is not None
    assert result.step_number == 2
    assert result.status == "active"
    assert result.finding.issue_type == "duplicate_rows"

def test_get_current_task_step_returns_none_when_task_completed():

    finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="age kolonunda eksik değer var.",
        suggested_action="Eksik değerleri inceleyin.",
    )

    step = DataEngineeringTaskStep(
        step_number=1,
        title="Missing values problemini çöz",
        finding=finding,
        status="completed",
    )

    task = DataEngineeringTask(
        task_id="task-001",
        title="Dataset problemlerini çöz",
        steps=[step],
        current_step_number=1,
        status="completed",
    )

    result = get_current_task_step(task)

    assert result is None

def test_complete_current_task_step_activates_next_step():

    first_finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="age kolonunda eksik değer var.",
        suggested_action="Eksik değerleri inceleyin.",
    )

    second_finding = DataQualityFinding(
        issue_type="duplicate_rows",
        column=None,
        severity="medium",
        observation="Duplicate satırlar var.",
        suggested_action="Duplicate satırları inceleyin.",
    )

    first_step = DataEngineeringTaskStep(
        step_number=1,
        title="Missing values problemini çöz",
        finding=first_finding,
        status="active",
    )

    second_step = DataEngineeringTaskStep(
        step_number=2,
        title="Duplicate rows problemini çöz",
        finding=second_finding,
        status="pending",
    )

    task = DataEngineeringTask(
        task_id="task-001",
        title="Dataset problemlerini çöz",
        steps=[
            first_step,
            second_step,
        ],
        current_step_number=1,
        status="active",
    )

    result = complete_current_task_step(task)

    assert result.steps[0].status == "completed"
    assert result.steps[1].status == "active"

    assert result.current_step_number == 2
    assert result.status == "active"

def test_complete_current_task_step_completes_task_when_no_next_step():

    finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="age kolonunda eksik değer var.",
        suggested_action="Eksik değerleri inceleyin.",
    )

    step = DataEngineeringTaskStep(
        step_number=1,
        title="Missing values problemini çöz",
        finding=finding,
        status="active",
    )

    task = DataEngineeringTask(
        task_id="task-001",
        title="Dataset problemlerini çöz",
        steps=[step],
        current_step_number=1,
        status="active",
    )

    result = complete_current_task_step(task)

    assert result.steps[0].status == "completed"
    assert result.status == "completed"


    #Başarılı validation testi

def test_successful_validation_advances_task_to_next_step():

    first_finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="age kolonunda eksik değer var.",
        suggested_action="Eksik değerleri inceleyin.",
    )

    second_finding = DataQualityFinding(
        issue_type="duplicate_rows",
        column=None,
        severity="medium",
        observation="Duplicate satırlar var.",
        suggested_action="Duplicate satırları inceleyin.",
    )

    first_step = DataEngineeringTaskStep(
        step_number=1,
        title="Missing values problemini çöz",
        finding=first_finding,
        status="active",
    )

    second_step = DataEngineeringTaskStep(
        step_number=2,
        title="Duplicate rows problemini çöz",
        finding=second_finding,
        status="pending",
    )

    task = DataEngineeringTask(
        task_id="task-001",
        title="Dataset problemlerini çöz",
        steps=[
            first_step,
            second_step,
        ],
        current_step_number=1,
        status="active",
    )

    validation = MissingValuesValidationResult(
        column="age",
        before_null_count=3,
        after_null_count=1,
        success=True,
    )

    result = apply_validation_result_to_task(
        task=task,
        validation=validation,
    )

    assert result.steps[0].status == "completed"
    assert result.steps[1].status == "active"
    assert result.current_step_number == 2

# Başarısız validation testi

def test_failed_validation_keeps_task_on_current_step():

    finding = DataQualityFinding(
        issue_type="duplicate_rows",
        column=None,
        severity="medium",
        observation="Duplicate satırlar var.",
        suggested_action="Duplicate satırları inceleyin.",
    )

    step = DataEngineeringTaskStep(
        step_number=1,
        title="Duplicate rows problemini çöz",
        finding=finding,
        status="active",
    )

    task = DataEngineeringTask(
        task_id="task-001",
        title="Dataset problemlerini çöz",
        steps=[step],
        current_step_number=1,
        status="active",
    )

    validation = DuplicateRowsValidationResult(
        before_duplicate_count=2,
        after_duplicate_count=2,
        success=False,
    )

    result = apply_validation_result_to_task(
        task=task,
        validation=validation,
    )

    assert result.steps[0].status == "active"
    assert result.current_step_number == 1
    assert result.status == "active"


def test_review_current_task_transformation_advances_after_real_validation():

    first_finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="age kolonunda eksik değer var.",
        suggested_action="Eksik değerleri inceleyin.",
    )

    second_finding = DataQualityFinding(
        issue_type="duplicate_rows",
        column=None,
        severity="medium",
        observation="Duplicate satırlar var.",
        suggested_action="Duplicate satırları inceleyin.",
    )

    first_step = DataEngineeringTaskStep(
        step_number=1,
        title="Missing values problemini çöz",
        finding=first_finding,
        status="active",
    )

    second_step = DataEngineeringTaskStep(
        step_number=2,
        title="Duplicate rows problemini çöz",
        finding=second_finding,
        status="pending",
    )

    task = DataEngineeringTask(
        task_id="task-001",
        title="Dataset problemlerini çöz",
        steps=[
            first_step,
            second_step,
        ],
        current_step_number=1,
        status="active",
    )

    before_df = pd.DataFrame(
        {
            "age": [20, None, None],
        }
    )

    after_df = pd.DataFrame(
        {
            "age": [20, 25, None],
        }
    )

    result = review_current_task_transformation(
        task=task,
        before_df=before_df,
        after_df=after_df,
    )

    assert result.steps[0].status == "completed"
    assert result.steps[1].status == "active"
    assert result.current_step_number == 2