import backend.app.database as database

from backend.app.models import (
    PracticeMicroCheckRequest,
    PracticeMicroCheckResponse,
)

from backend.app.practice_ai_service import (
    evaluate_practice_micro_check,
    generate_practice_micro_check_support,
)


def review_practice_micro_check(
    request: PracticeMicroCheckRequest,
) -> PracticeMicroCheckResponse:
    """
    Junior'ın micro-check cevabını değerlendirir.

    Akış:

    attempt_id
    ↓
    original practice attempt
    ↓
    mentor_support.micro_check
    ↓
    primary concept
    ↓
    AI micro-check evaluation
    ↓
    doğruysa original challenge'a dön
    yanlışsa daha fazla destek
    """

    # --------------------------------------------------
    # 1. ORIGINAL ATTEMPT
    # --------------------------------------------------

    attempt_record = database.get_practice_attempt_by_id(
        attempt_id=request.attempt_id,
        learner_id=request.learner_id,
    )

    if attempt_record is None:
        raise ValueError(
            "Practice attempt bulunamadı."
        )

    # --------------------------------------------------
    # 2. MICRO-CHECK VAR MI?
    # --------------------------------------------------

    mentor_support = attempt_record.mentor_support

    if (
        mentor_support is None
        or mentor_support.micro_check is None
    ):
        raise ValueError(
            "Bu attempt için micro-check bulunamadı."
        )

    # --------------------------------------------------
    # 3. PRIMARY CONCEPT
    # --------------------------------------------------

    diagnosis = attempt_record.diagnosis

    if (
        diagnosis is None
        or diagnosis.primary_missing_concept_id is None
    ):
        raise ValueError(
            "Micro-check için primary concept bulunamadı."
        )

    primary_concept_id = (
        diagnosis.primary_missing_concept_id
    )

    # --------------------------------------------------
    # 4. LEARNER LANGUAGE
    # --------------------------------------------------

    learner_profile = database.get_learner_profile_by_id(
        request.learner_id
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
    # 5. MICRO-CHECK EVALUATION
    # --------------------------------------------------

    validation = evaluate_practice_micro_check(
        question=mentor_support.micro_check,
        answer=request.answer,
        primary_concept_id=primary_concept_id,
        preferred_language=preferred_language,
    )

     # --------------------------------------------------
    # 6. SAVE MICRO-CHECK ATTEMPT
    # --------------------------------------------------

    saved_micro_check_attempt = (
        database.save_practice_micro_check_attempt(
            learner_id=request.learner_id,
            attempt_id=request.attempt_id,
            answer=request.answer,
            validation=validation,
        )
    )

    # --------------------------------------------------
    # 7. NEXT ACTION
    # --------------------------------------------------

    if validation.success:

        next_action = "return_to_challenge"
        additional_support = None

    else:

        next_action = "more_support"

        additional_support = (
            generate_practice_micro_check_support(
                question=mentor_support.micro_check,
                answer=request.answer,
                primary_concept_id=primary_concept_id,
                micro_check_attempt_number=(
                    saved_micro_check_attempt
                    .micro_check_attempt_number
                ),
                preferred_language=preferred_language,
            )
        )

    # --------------------------------------------------
    # 8. RESPONSE
    # --------------------------------------------------

    return PracticeMicroCheckResponse(
        learner_id=request.learner_id,
        attempt_id=request.attempt_id,
        validation=validation,
        next_action=next_action,
        additional_support=additional_support,
    )