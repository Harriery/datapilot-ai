from backend.app.models import (
    PracticeDiagnosis,
    PracticeAttemptRecord,
    PracticeMentorDecision,
)


def choose_practice_mentor_decision(
    skill_status: str,
    diagnosis: PracticeDiagnosis,
    previous_attempts: list[PracticeAttemptRecord],
) -> PracticeMentorDecision:
    """
    Junior'ın mevcut diagnosis'ı ve geçmiş practice attempt'lerine
    göre ne kadar ve nasıl yardım verilmesi gerektiğine karar verir.

    Aynı kavramı takip etmek için natural-language açıklamalar değil,
    stable concept ID kullanılır.
    """

    current_primary_gap = (
        diagnosis.primary_missing_concept_id
    )

    # --------------------------------------------------
    # AYNI ANA KAVRAMDA DAHA ÖNCE TAKILDI MI?
    # --------------------------------------------------

    same_gap_attempts = []

    if current_primary_gap is not None:

        for previous_attempt in previous_attempts:

            previous_diagnosis = (
                previous_attempt.diagnosis
            )

            if previous_diagnosis is None:
                continue

            if (
                previous_diagnosis.primary_missing_concept_id
                == current_primary_gap
            ):
                same_gap_attempts.append(
                    previous_attempt
                )

    # --------------------------------------------------
    # BU SKILL'DE DAHA ÖNCE BAŞARILI OLDU MU?
    # --------------------------------------------------

    previous_success_count = sum(
        1
        for attempt in previous_attempts
        if attempt.validation.success
    )

    # --------------------------------------------------
    # AYNI PROBLEM TEKRAR EDİYOR
    # → DESTEĞİ KADEMELİ ARTIR
    # --------------------------------------------------

    if same_gap_attempts:

        last_attempt = same_gap_attempts[-1]

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
                        "kavramında tekrar zorlandı ve "
                        "hafif destek yeterli olmadı."
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
                        "kavramında GUIDE desteğinden "
                        "sonra tekrar zorlandı."
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
                        "kavramında öğretim desteğinden "
                        "sonra hâlâ zorlanıyor."
                    ),
                    needs_micro_check=True,
                )

        return PracticeMentorDecision(
            assistance_level="GUIDE",
            support_strategy="focus",
            reason=(
                f"Junior {current_primary_gap} "
                "kavramında daha önce de zorlanmış."
            ),
            needs_micro_check=False,
        )

    # --------------------------------------------------
    # DAHA ÖNCE YAPABİLİYORDU
    # → ÖNCE RECALL
    # --------------------------------------------------

    if (
        previous_success_count > 0
        and skill_status != "new"
    ):
        return PracticeMentorDecision(
            assistance_level="NUDGE",
            support_strategy="recall",
            reason=(
                "Junior bu skill'de daha önce başarılı oldu. "
                "Önce hafif bir hatırlatma yeterli olabilir."
            ),
            needs_micro_check=False,
        )

    # --------------------------------------------------
    # KAVRAM YENİ / EKSİK
    # → TEACH
    # --------------------------------------------------

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

    # --------------------------------------------------
    # DEFAULT
    # --------------------------------------------------

    return PracticeMentorDecision(
        assistance_level="GUIDE",
        support_strategy="focus",
        reason=(
            "Junior'ın doğru bölgeye yönlendirilmesi gerekiyor."
        ),
        needs_micro_check=False,
    )