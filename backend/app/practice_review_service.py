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

        saved_record = database.save_practice_attempt(
            attempt=attempt,
            validation=validation,
            diagnosis=None,
            mentor_decision=None,
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
    # 9. REVIEW DÖNDÜR
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