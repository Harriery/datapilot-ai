from backend.app.models import (
    PracticeDiagnosis,
    PracticeAttemptRecord,
    PracticeMentorDecision,
)



def choose_practice_mentor_decision(
    skill_status: str,
    diagnosis: PracticeDiagnosis,
    previous_attempts: list[PracticeAttemptRecord],
    current_challenge_id: str,
) -> PracticeMentorDecision:
    """
    Junior'ın mevcut diagnosis'ı ve geçmiş practice attempt'lerine
    göre ne kadar ve nasıl yardım verilmesi gerektiğine karar verir.

    İki farklı geçmiş kullanılır:

    1. Same challenge history
       → yardım escalation için

    2. Cross-challenge skill history
       → recall / geçmiş öğrenme sinyali için
    """

    current_primary_gap = (
        diagnosis.primary_missing_concept_id
    )

    # ==================================================
    # 1. AYNI CHALLENGE İÇİNDE AYNI PROBLEM TEKRARLADI MI?
    # ==================================================

    same_challenge_gap_attempts = []

    if current_primary_gap is not None:

        for previous_attempt in previous_attempts:

            # Başka challenge'lar escalation yapmamalı.
            if (
                previous_attempt.attempt.challenge_id
                != current_challenge_id
            ):
                continue

            previous_diagnosis = (
                previous_attempt.diagnosis
            )

            if previous_diagnosis is None:
                continue

            if (
                previous_diagnosis.primary_missing_concept_id
                == current_primary_gap
            ):
                same_challenge_gap_attempts.append(
                    previous_attempt
                )

    # ==================================================
    # 2. BAŞKA CHALLENGE'LARDA BU SKILL'DE BAŞARILI MIYDI?
    # ==================================================

    cross_challenge_success_count = sum(
        1
        for attempt in previous_attempts
        if (
            attempt.attempt.challenge_id
            != current_challenge_id
            and attempt.validation.success
        )
    )

    # ==================================================
    # 3. AYNI CHALLENGE'DA AYNI BLOCKER TEKRAR EDİYOR
    # → ESCALATE
    # ==================================================

    if same_challenge_gap_attempts:

        last_attempt = (
            same_challenge_gap_attempts[-1]
        )

        previous_decision = (
            last_attempt.mentor_decision
        )

        if previous_decision is not None:

            previous_level = (
                previous_decision.assistance_level
            )

            if previous_level in {
                "NONE",
                "NUDGE",
            }:
                return PracticeMentorDecision(
                    assistance_level="GUIDE",
                    support_strategy="focus",
                    reason=(
                        f"Junior {current_primary_gap} "
                        "kavramında aynı challenge içinde "
                        "tekrar zorlandı. Hafif destek "
                        "yeterli olmadı."
                    ),
                    needs_micro_check=False,
                )

            if previous_level == "GUIDE":
                return PracticeMentorDecision(
                    assistance_level="TEACH",
                    support_strategy=(
                        "concept_explanation"
                    ),
                    reason=(
                        f"Junior {current_primary_gap} "
                        "kavramında aynı challenge içinde "
                        "GUIDE desteğinden sonra "
                        "tekrar zorlandı."
                    ),
                    needs_micro_check=True,
                )

            if previous_level in {
                "TEACH",
                "DEMONSTRATE",
            }:
                return PracticeMentorDecision(
                    assistance_level="DEMONSTRATE",
                    support_strategy="worked_example",
                    reason=(
                        f"Junior {current_primary_gap} "
                        "kavramında aynı challenge içinde "
                        "öğretim desteğinden sonra "
                        "hâlâ zorlanıyor."
                    ),
                    needs_micro_check=True,
                )

        return PracticeMentorDecision(
            assistance_level="GUIDE",
            support_strategy="focus",
            reason=(
                f"Junior {current_primary_gap} "
                "kavramında aynı challenge içinde "
                "daha önce de zorlanmış."
            ),
            needs_micro_check=False,
        )

    # ==================================================
    # 4. YENİ CHALLENGE AMA SKILL GEÇMİŞTE BAŞARILI
    # → RECALL
    # ==================================================

    if (
        cross_challenge_success_count > 0
        and skill_status != "new"
    ):
        return PracticeMentorDecision(
            assistance_level="NUDGE",
            support_strategy="recall",
            reason=(
                "Junior bu skill'i başka challenge'larda "
                "daha önce başarıyla kullandı. "
                "Önce hafif bir hatırlatma yeterli olabilir."
            ),
            needs_micro_check=False,
        )

    # ==================================================
    # 5. YENİ / EKSİK KAVRAM
    # → TEACH
    # ==================================================

    if diagnosis.needs_concept_teaching:
        return PracticeMentorDecision(
            assistance_level="TEACH",
            support_strategy="concept_explanation",
            reason=(
                "Diagnosis junior'ın gerekli kavramı "
                "henüz yeterince anlamadığını gösteriyor."
            ),
            needs_micro_check=True,
        )

    # ==================================================
    # 6. DEFAULT
    # ==================================================

    return PracticeMentorDecision(
        assistance_level="GUIDE",
        support_strategy="focus",
        reason=(
            "Junior'ın doğru bölgeye yönlendirilmesi gerekiyor."
        ),
        needs_micro_check=False,
    )