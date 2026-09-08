from backend.app.models import (
    MentorDecision,
     DataQualityFinding,
    DataEngineeringTaskStep,
    DataEngineeringTask,
    )
import pytest
from pydantic import ValidationError

# ==================================================
# TEST - GEÇERLİ MENTOR KARARI
# ==================================================
# Amaç:
# İzin verilen bir assistance_level ile
# MentorDecision modelinin oluşturulabildiğini doğrular.
def test_mentor_decision_accepts_valid_assistance_level():
    decision = MentorDecision(
        skill_name="python_dict",
        assistance_level="GUIDE",
        reason="Kullanıcı yönlendirmeye ihtiyaç duyuyor.",
    )

    assert decision.skill_name == "python_dict"
    assert decision.assistance_level == "GUIDE"


# ==================================================
# TEST - GEÇERSİZ MENTOR YARDIM SEVİYESİ REDDEDİLİYOR
# ==================================================
# Amaç:
# Literal içinde tanımlanmayan bir assistance_level verilirse
# Pydantic'in validation hatası verdiğini doğrular.
def test_mentor_decision_rejects_invalid_assistance_level():
    with pytest.raises(ValidationError):
        MentorDecision(
            skill_name="python_dict",
            assistance_level="SUPER_HELP",
            reason="Geçersiz yardım seviyesi testi.",
        )


def test_data_engineering_task_step_defaults_to_pending():

    finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="age kolonunda eksik değer var.",
        suggested_action="Eksik değerleri inceleyin.",
    )

    step = DataEngineeringTaskStep(
        step_number=1,
        title="Eksik değerleri incele",
        finding=finding,
    )

    assert step.step_number == 1
    assert step.title == "Eksik değerleri incele"
    assert step.finding.issue_type == "missing_values"
    assert step.status == "pending"

def test_data_engineering_task_contains_multiple_steps():

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
    )

    task = DataEngineeringTask(
        task_id="task-001",
        title="Dataset data quality problemlerini çöz",
        steps=[
            first_step,
            second_step,
        ],
        status="active",
    )

    assert task.task_id == "task-001"
    assert len(task.steps) == 2

    assert task.current_step_number == 1
    assert task.status == "active"

    assert task.steps[0].status == "active"
    assert task.steps[1].status == "pending"

    assert task.steps[0].finding.issue_type == "missing_values"
    assert task.steps[1].finding.issue_type == "duplicate_rows"