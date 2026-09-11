from backend.app.models import (
    MentorDecision,
     DataQualityFinding,
    DataEngineeringTaskStep,
    DataEngineeringTask,
    PracticeAttemptRequest,
    PracticeDiagnosis,
    PracticeMentorDecision,
    PracticeAttemptRecord,
    PracticeAttemptValidation,
    PracticeAttemptReview,
    PracticeMentorSupport,
    PracticeValidationSpec,
    PracticeChallenge
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


def test_practice_attempt_request():

    attempt = PracticeAttemptRequest(
        learner_id="learner-001",
        challenge_id="challenge-001",
        answer="print(2)",
        execution_output="2",
        execution_error=None,
    )

    assert attempt.learner_id == "learner-001"
    assert attempt.challenge_id == "challenge-001"
    assert attempt.answer == "print(2)"
    assert attempt.execution_output == "2"
    assert attempt.execution_error is None

def test_practice_diagnosis():

    diagnosis = PracticeDiagnosis(
        understood_concept_ids=[
            "iteration",
            "conditional_logic",
        ],
        missing_concept_ids=[
            "dictionary_key_access",
        ],
        primary_missing_concept_id=(
            "dictionary_key_access"
        ),
        understands=[
            "for loop",
            "iteration",
        ],
        missing_concepts=[
            "dictionary key access",
        ],
        misconception=(
            "Dictionary değerine object attribute "
            "gibi erişmeye çalışıyor."
        ),
        needs_concept_teaching=True,
        confidence="high",
    )

    assert "iteration" in (
        diagnosis.understood_concept_ids
    )

    assert "dictionary_key_access" in (
        diagnosis.missing_concept_ids
    )

    assert (
        diagnosis.primary_missing_concept_id
        == "dictionary_key_access"
    )

    assert diagnosis.needs_concept_teaching is True
    assert diagnosis.confidence == "high"

def test_practice_mentor_decision():

    decision = PracticeMentorDecision(
        assistance_level="TEACH",
        support_strategy="concept_explanation",
        reason=(
            "Junior dictionary key access "
            "kavramında zorlanıyor."
        ),
        needs_micro_check=True,
    )

    assert decision.assistance_level == "TEACH"
    assert (
        decision.support_strategy
        == "concept_explanation"
    )
    assert decision.needs_micro_check is True


def test_practice_attempt_record():

    attempt = PracticeAttemptRequest(
        learner_id="learner-001",
        challenge_id="challenge-001",
        answer="print(record.city)",
        execution_output=None,
        execution_error=(
            "AttributeError: 'dict' object "
            "has no attribute 'city'"
        ),
    )

    validation = PracticeAttemptValidation(
        success=False,
        feedback="Kod çalışırken bir hata oluştu.",
    )

    diagnosis = PracticeDiagnosis(
        understands=[
            "iteration",
        ],
        missing_concepts=[
            "dictionary key access",
        ],
        misconception=(
            "Dictionary değerine object attribute "
            "gibi erişmeye çalışıyor."
        ),
        needs_concept_teaching=True,
        confidence="high",
    )

    mentor_decision = PracticeMentorDecision(
        assistance_level="GUIDE",
        support_strategy="focus",
        reason=(
            "Junior dictionary access konusunda "
            "yönlendirmeye ihtiyaç duyuyor."
        ),
        needs_micro_check=False,
    )

    record = PracticeAttemptRecord(
        attempt_id="attempt-001",
        attempt_number=2,
        attempt=attempt,
        validation=validation,
        diagnosis=diagnosis,
        mentor_decision=mentor_decision,
    )

    assert record.attempt_id == "attempt-001"
    assert record.attempt_number == 2
    assert record.validation.success is False

    assert (
        "dictionary key access"
        in record.diagnosis.missing_concepts
    )

    assert (
        record.mentor_decision.assistance_level
        == "GUIDE"
    )

def test_practice_attempt_review():

    validation = PracticeAttemptValidation(
        success=True,
        feedback="Challenge başarıyla tamamlandı.",
    )

    review = PracticeAttemptReview(
        learner_id="learner-001",
        challenge_id="challenge-001",
        attempt_id="attempt-001",
        attempt_number=1,
        validation=validation,
        diagnosis=None,
        mentor_decision=None,
    )

    assert review.learner_id == "learner-001"
    assert review.attempt_number == 1
    assert review.validation.success is True
    assert review.diagnosis is None
    assert review.mentor_decision is None

def test_practice_mentor_support():

    support = PracticeMentorSupport(
        message=(
            "record değişkeninin veri yapısına tekrar bak. "
            "Benzer bir çalışmada key kullanmıştık."
        ),
        micro_check=None,
    )

    assert "key" in support.message
    assert support.micro_check is None

def test_practice_validation_spec_exact_output():

    spec = PracticeValidationSpec(
        validation_type="exact_output",
        expected_output="2",
    )

    assert spec.validation_type == "exact_output"
    assert spec.expected_output == "2"
    assert spec.column is None

def test_practice_transformation_challenge_data_flow():

    challenge = PracticeChallenge(
        challenge_id="challenge-001",
        skill_name="null_analysis",
        difficulty="easy",
        challenge_type="transformation",
        title="Eksik age değerlerini düzelt",
        instructions="Null değerleri azalt.",
        input_rows=[
            {
                "name": "Ali",
                "age": 30,
            },
            {
                "name": "Ayse",
                "age": None,
            },
        ],
    )

    attempt = PracticeAttemptRequest(
        learner_id="learner-001",
        challenge_id="challenge-001",
        answer="Eksik age değerini doldurdum.",
        result_rows=[
            {
                "name": "Ali",
                "age": 30,
            },
            {
                "name": "Ayse",
                "age": 25,
            },
        ],
    )

    assert challenge.input_rows is not None
    assert challenge.input_rows[1]["age"] is None

    assert attempt.result_rows is not None
    assert attempt.result_rows[1]["age"] == 25