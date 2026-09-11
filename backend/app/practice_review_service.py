import backend.app.database as database

from backend.app.models import (
    PracticeAttemptRequest,
    PracticeAttemptReview,
)

from backend.app.practice_service import (
    validate_practice_attempt,
)

from backend.app.practice_ai_service import (
    diagnose_practice_attempt,
    generate_practice_mentor_support,
)

from backend.app.practice_policy_service import (
    choose_practice_mentor_decision,
)

from backend.app.mentor_service import (
    refresh_skill_status,
)

# ==================================================
# PRACTICE ATTEMPT ASSISTANCE
# ==================================================


def get_practice_attempt_assistance_level(
    previous_attempts,
    current_challenge_id: str,
) -> str:
    """
    Current attempt yapılmadan önce junior'ın
    ne kadar mentor desteği aldığını belirler.

    İlk deneme:
    → NONE

    Önceki aynı challenge attempt'inde mentor desteği varsa:
    → o assistance level
    """

    same_challenge_attempts = [
        record
        for record in previous_attempts
        if (
            record.attempt.challenge_id
            == current_challenge_id
        )
    ]

    if not same_challenge_attempts:
        return "NONE"

    previous_attempt = same_challenge_attempts[-1]

    if previous_attempt.mentor_decision is None:
        return "NONE"

    return (
        previous_attempt
        .mentor_decision
        .assistance_level
    )

# ==================================================
# PRACTICE LEARNING EVIDENCE
# ==================================================


PRACTICE_EVIDENCE_TYPE_MAP = {
    "code": "application",
    "sql": "application",
    "transformation": "application",
    "debug": "debugging",
    "output_prediction": "explanation",
    "explain": "explanation",
    "validation": "validation",
    "data_investigation": "validation",
}


def get_practice_evidence_type(
    challenge_type: str,
) -> str:
    """
    Practice challenge türünü mevcut
    LearningEvidence evidence_type yapısına çevirir.
    """

    return PRACTICE_EVIDENCE_TYPE_MAP.get(
        challenge_type,
        "application",
    )


def record_practice_learning_evidence(
    learner_id: str,
    skill_name: str,
    challenge_id: str,
    challenge_type: str,
    success: bool,
    assistance_level: str,
) -> str:
    """
    Deterministic practice validation sonucunu
    learner'ın kalıcı learning evidence'ına yazar.

    Burada AI kullanılmaz.
    """

    evidence_type = get_practice_evidence_type(
        challenge_type
    )

    database.record_learning_evidence(
        learner_id=learner_id,
        skill_name=skill_name,
        assistance_level=assistance_level,
        success=success,
        evidence_type=evidence_type,
        note=(
            f"Practice challenge {challenge_id} "
            f"deterministic validation sonucu: "
            f"{'success' if success else 'failure'}."
        ),
        session_id=None,
    )

    return refresh_skill_status(
        learner_id=learner_id,
        skill_name=skill_name,
    )


def review_practice_attempt(
    attempt: PracticeAttemptRequest,
) -> PracticeAttemptReview:
    """
    Practice attempt'in ana orchestration akışı.

    Akış:

    attempt
    ↓
    deterministic validation
    ↓
    başarılıysa direkt kaydet
    ↓
    başarısızsa AI diagnosis
    ↓
    skill geçmişini getir
    ↓
    adaptive assistance policy
    ↓
    attempt'i tüm bilgilerle kaydet
    """

    # --------------------------------------------------
    # 1. DETERMINISTIC VALIDATION
    # --------------------------------------------------

    validation = validate_practice_attempt(
        attempt=attempt
    )

    # --------------------------------------------------
    # 2. BAŞARILI ATTEMPT
    # --------------------------------------------------
    #
    # Junior doğru yaptıysa diagnosis veya yardım üretmeye
    # gerek yok.
    if validation.success:

        # Challenge bilgisi evidence için gerekli.
        challenge_record = database.get_practice_challenge(
            challenge_id=attempt.challenge_id,
            learner_id=attempt.learner_id,
        )

        if challenge_record is None:
            raise ValueError(
                "Practice challenge bulunamadı."
            )

        challenge = challenge_record.challenge

        # Bu attempt yapılmadan önce junior ne kadar
        # yardım almıştı?
        previous_attempts = (
            database.get_practice_attempts_by_skill(
                learner_id=attempt.learner_id,
                skill_name=challenge.skill_name,
            )
        )

        assistance_level = (
            get_practice_attempt_assistance_level(
                previous_attempts=previous_attempts,
                current_challenge_id=attempt.challenge_id,
            )
        )

        saved_record = database.save_practice_attempt(
            attempt=attempt,
            validation=validation,
            diagnosis=None,
            mentor_decision=None,
        )

        # Deterministic success artık learner progress'e yazılır.
        record_practice_learning_evidence(
            learner_id=attempt.learner_id,
            skill_name=challenge.skill_name,
            challenge_id=attempt.challenge_id,
            challenge_type=challenge.challenge_type,
            success=True,
            assistance_level=assistance_level,
        )

        return PracticeAttemptReview(
            learner_id=attempt.learner_id,
            challenge_id=attempt.challenge_id,
            attempt_id=saved_record.attempt_id,
            attempt_number=saved_record.attempt_number,
            validation=validation,
            diagnosis=None,
            mentor_decision=None,
            mentor_support=None,
        )

    # --------------------------------------------------
    # 3. CHALLENGE'I GETİR
    # --------------------------------------------------
    #
    # AI diagnosis için challenge bilgisine ihtiyacımız var.
    challenge_record = database.get_practice_challenge(
        challenge_id=attempt.challenge_id,
        learner_id=attempt.learner_id,
    )

    if challenge_record is None:
        raise ValueError(
            "Practice challenge bulunamadı."
        )

    challenge = challenge_record.challenge

    # --------------------------------------------------
    # 4. AI DIAGNOSIS
    # --------------------------------------------------

    diagnosis = diagnose_practice_attempt(
        challenge=challenge,
        attempt=attempt,
        validation=validation,
    )

    # --------------------------------------------------
    # 5. AYNI SKILL'İN GEÇMİŞİNİ GETİR
    # --------------------------------------------------

    previous_attempts = database.get_practice_attempts_by_skill(
        learner_id=attempt.learner_id,
        skill_name=challenge.skill_name,
    )

    # --------------------------------------------------
    # 6. SKILL STATUS
    # --------------------------------------------------

    skill_state = database.get_skill_state(
        attempt.learner_id,
        challenge.skill_name,
    )

    if skill_state is None:
        skill_status = "new"
    else:
        skill_status = skill_state["status"]

    

    # --------------------------------------------------
    # 7. ADAPTIVE ASSISTANCE POLICY
    # --------------------------------------------------

    mentor_decision = choose_practice_mentor_decision(
        skill_status=skill_status,
        diagnosis=diagnosis,
        previous_attempts=previous_attempts,
        current_challenge_id=attempt.challenge_id,
    )

        # --------------------------------------------------
    # LEARNER LANGUAGE
    # --------------------------------------------------

    learner_profile = database.get_learner_profile_by_id(
        attempt.learner_id
    )

    if learner_profile is None:
        raise ValueError(
            "Learner profile bulunamadı."
        )

    preferred_language = (
        learner_profile["preferred_language"]
        or "auto"
    )
    # --------------------------------------------------
# . JUNIOR'A GÖSTERİLECEK MENTOR DESTEĞİ
# --------------------------------------------------
#
# Backend yardım seviyesini zaten belirledi.
# AI yalnızca bu sınırlar içinde mesaj üretir.

    mentor_support = generate_practice_mentor_support(
        challenge=challenge,
        attempt=attempt,
        diagnosis=diagnosis,
        mentor_decision=mentor_decision,
        preferred_language=preferred_language,
    )

    # --------------------------------------------------
    # 8. ATTEMPT'İ KAYDET
    # --------------------------------------------------

    saved_record = database.save_practice_attempt(
        attempt=attempt,
        validation=validation,
        diagnosis=diagnosis,
        mentor_decision=mentor_decision,
        mentor_support=mentor_support,
    )


        # --------------------------------------------------
    # 9. LEARNING EVIDENCE
    # --------------------------------------------------
    #
    # Burada current mentor_decision kullanılmaz.
    # O karar junior'ın bu başarısız attempt'inden SONRA
    # verilecek yardım seviyesidir.
    #
    # Evidence için attempt yapılmadan ÖNCE alınan
    # assistance seviyesi kullanılır.

    assistance_level = (
        get_practice_attempt_assistance_level(
            previous_attempts=previous_attempts,
            current_challenge_id=attempt.challenge_id,
        )
    )

    record_practice_learning_evidence(
        learner_id=attempt.learner_id,
        skill_name=challenge.skill_name,
        challenge_id=attempt.challenge_id,
        challenge_type=challenge.challenge_type,
        success=False,
        assistance_level=assistance_level,
    )

    # --------------------------------------------------
    # 10. REVIEW DÖNDÜR
    # --------------------------------------------------

    return PracticeAttemptReview(
        learner_id=attempt.learner_id,
        challenge_id=attempt.challenge_id,
        attempt_id=saved_record.attempt_id,
        attempt_number=saved_record.attempt_number,
        validation=validation,
        diagnosis=diagnosis,
        mentor_decision=mentor_decision,
        mentor_support=mentor_support,
    )