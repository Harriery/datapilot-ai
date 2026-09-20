import pandas as pd

import backend.app.database as database

from backend.app.models import (
    DataQualityFinding,
    DataQualityAttemptResponse,
    DataEngineeringTask,
    DataEngineeringTaskTransformationResponse,
    LearningEvidenceDecision,
    MissingValuesValidationResult,
    DuplicateRowsValidationResult,
    DataQualityTransformationResponse,
)

from backend.app.transformation_validation_service import (
    validate_transformation_for_finding,
)

from backend.app.task_service import (
    get_current_task_step,
    apply_validation_result_to_task,
)

from backend.app.mentor_service import (
    get_skill_for_data_quality_issue,
    refresh_skill_status,
)


LOCAL_ASSISTANCE_BY_SKILL_STATUS = {
    "new": "GUIDE",
    "learning": "GUIDE",
    "practicing": "NUDGE",
    "comfortable": "NONE",
}


def get_local_assistance_level(
    skill_status: str,
) -> str:

    return LOCAL_ASSISTANCE_BY_SKILL_STATUS.get(
        skill_status,
        "GUIDE",
    )


def build_local_next_step(
    finding: DataQualityFinding,
) -> str:

    column = finding.column

    if finding.issue_type == "missing_values":

        if column:
            return (
                f"Önce {column} kolonunda eksik değer "
                "bulunan kayıtları ayır ve eksikliğin "
                "hangi satırlarda oluştuğunu incele."
            )

        return (
            "Önce eksik değer bulunan kayıtları ayır "
            "ve eksikliğin hangi alanlarda oluştuğunu incele."
        )

    if finding.issue_type == "duplicate_rows":

        return (
            "Önce duplicate satırları ayrı görüntüle "
            "ve gerçekten aynı kaydı temsil edip "
            "etmediklerini doğrula."
        )

    if finding.issue_type == "data_type_issue":

        if column:
            return (
                f"Önce {column} kolonunun mevcut veri tipini "
                "ve bu tipe uymayan değerleri kontrol et."
            )

        return (
            "Önce problemli kolonun mevcut veri tipini "
            "ve bu tipe uymayan değerleri kontrol et."
        )

    if finding.issue_type == "schema_issue":

        return (
            "Önce mevcut şemayı kontrol et ve eksik, "
            "fazla veya tekrarlanan kolonları belirle."
        )

    if finding.issue_type == "suspicious_values":

        if column:
            return (
                f"Önce {column} kolonundaki şüpheli değerleri "
                "ayrı incele ve bunları geçerli business "
                "rule ile karşılaştır."
            )

        return (
            "Önce şüpheli değerleri ayrı incele ve "
            "geçerli business rule ile karşılaştır."
        )

    return finding.suggested_action


def build_local_mentor_response(
    finding: DataQualityFinding,
    skill_status: str,
) -> str:

    assistance_level = (
        get_local_assistance_level(
            skill_status
        )
    )

    next_step = build_local_next_step(
        finding
    )

    if assistance_level == "NONE":
        return (
            f"{finding.observation} "
            f"{next_step}"
        )

    if assistance_level == "NUDGE":
        return (
            f"İpucu: {next_step}"
        )

    return (
        f"{finding.observation} "
        f"İlk adım: {next_step}"
    )

def get_local_mentor_response_for_data_quality_finding(
    learner_id: str,
    finding: DataQualityFinding,
) -> str | None:

    skill_name = (
        get_skill_for_data_quality_issue(
            finding.issue_type
        )
    )

    if skill_name is None:
        return None

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

    return build_local_mentor_response(
        finding=finding,
        skill_status=skill_status,
    )


def review_data_quality_attempt_locally(
    learner_id: str,
    finding: DataQualityFinding,
    attempt: str,
) -> DataQualityAttemptResponse | None:

    if not attempt.strip():
        raise ValueError(
            "Attempt boş olamaz."
        )

    skill_name = (
        get_skill_for_data_quality_issue(
            finding.issue_type
        )
    )

    if skill_name is None:
        return None

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

    guidance = build_local_mentor_response(
        finding=finding,
        skill_status=skill_status,
    )

    # Free-text'i deterministic olarak
    # doğru/yanlış diye tahmin etmiyoruz.
    #
    # Gerçek success evidence'ı daha sonra
    # before/after transformation validation'dan gelir.
    evidence = LearningEvidenceDecision(
        is_evidence=False,
        evidence_type=None,
        success=None,
        note=(
            "Free-text attempt local mode'da "
            "otomatik learning evidence olarak "
            "değerlendirilmedi."
        ),
    )

    mentor_response = (
        "Bu açıklamayı local mode'da "
        "doğru veya yanlış diye puanlamıyorum. "
        f"{guidance}"
    )

    return DataQualityAttemptResponse(
        mentor_response=mentor_response,
        skill_name=skill_name,
        skill_status=skill_status,
        evidence=evidence,
    )

def build_local_learning_evidence(
    validation: (
        MissingValuesValidationResult
        | DuplicateRowsValidationResult
    ),
) -> LearningEvidenceDecision:

    if isinstance(
        validation,
        MissingValuesValidationResult,
    ):
        note = (
            f"{validation.column} kolonundaki null sayısı "
            f"{validation.before_null_count} değerinden "
            f"{validation.after_null_count} değerine değişti."
        )

    elif isinstance(
        validation,
        DuplicateRowsValidationResult,
    ):
        note = (
            "Duplicate row sayısı "
            f"{validation.before_duplicate_count} değerinden "
            f"{validation.after_duplicate_count} değerine değişti."
        )

    else:
        raise ValueError(
            "Desteklenmeyen local validation sonucu."
        )

    return LearningEvidenceDecision(
        is_evidence=True,
        evidence_type="application",
        success=validation.success,
        note=note,
    )


def review_data_quality_transformation_locally(
    learner_id: str,
    finding: DataQualityFinding,
    before_df: pd.DataFrame,
    after_df: pd.DataFrame,
) -> DataQualityTransformationResponse | None:

    skill_name = (
        get_skill_for_data_quality_issue(
            finding.issue_type
        )
    )

    if skill_name is None:
        return None

    # ==================================================
    # LOCAL SKILL STATE
    # ==================================================

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

        skill_status_before = "new"

    else:
        skill_status_before = (
            skill_state["status"]
        )

    assistance_level = (
        get_local_assistance_level(
            skill_status_before
        )
    )

    # ==================================================
    # DETERMINISTIC VALIDATION
    # ==================================================

    validation = (
        validate_transformation_for_finding(
            before_df=before_df,
            after_df=after_df,
            finding=finding,
        )
    )

    if validation is None:
        return None

    # ==================================================
    # LOCAL LEARNING EVIDENCE
    # ==================================================

    evidence = build_local_learning_evidence(
        validation
    )

    database.record_learning_evidence(
        learner_id=learner_id,
        skill_name=skill_name,
        assistance_level=assistance_level,
        success=evidence.success,
        evidence_type=evidence.evidence_type,
        note=evidence.note,
        session_id=None,
    )

    skill_status = refresh_skill_status(
        learner_id=learner_id,
        skill_name=skill_name,
    )

    return DataQualityTransformationResponse(
        skill_name=skill_name,
        skill_status=skill_status,
        validation=validation,
        evidence=evidence,
    )

def review_task_transformation_locally(
    learner_id: str,
    task: DataEngineeringTask,
    before_df: pd.DataFrame,
    after_df: pd.DataFrame,
) -> DataEngineeringTaskTransformationResponse:

    current_step = get_current_task_step(
        task
    )

    if current_step is None:
        raise ValueError(
            "Current task step bulunamadı."
        )

    finding = current_step.finding

    skill_name = (
        get_skill_for_data_quality_issue(
            finding.issue_type
        )
    )

    if skill_name is None:
        raise ValueError(
            "Bu finding için uygun skill bulunamadı."
        )

    # ==================================================
    # LOCAL SKILL STATE
    # ==================================================

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

        skill_state = database.get_skill_state(
            learner_id,
            skill_name,
        )

    skill_status_before = (
        skill_state["status"]
    )

    assistance_level = (
        get_local_assistance_level(
            skill_status_before
        )
    )

    # ==================================================
    # DETERMINISTIC VALIDATION
    # ==================================================

    validation = (
        validate_transformation_for_finding(
            before_df=before_df,
            after_df=after_df,
            finding=finding,
        )
    )

    if validation is None:
        raise ValueError(
            "Bu task step için local "
            "transformation validation desteklenmiyor."
        )

    # ==================================================
    # LOCAL LEARNING EVIDENCE
    # ==================================================

    evidence = build_local_learning_evidence(
        validation
    )

    database.record_learning_evidence(
        learner_id=learner_id,
        skill_name=skill_name,
        assistance_level=assistance_level,
        success=evidence.success,
        evidence_type=evidence.evidence_type,
        note=evidence.note,
        session_id=None,
    )

    skill_status = refresh_skill_status(
        learner_id=learner_id,
        skill_name=skill_name,
    )

    # ==================================================
    # TASK PROGRESSION
    # ==================================================

    updated_task = (
        apply_validation_result_to_task(
            task=task,
            validation=validation,
        )
    )

    database.save_data_engineering_task(
        learner_id=learner_id,
        task=updated_task,
    )

    return DataEngineeringTaskTransformationResponse(
        task=updated_task,
        skill_name=skill_name,
        skill_status=skill_status,
        validation=validation,
        evidence=evidence,
    )