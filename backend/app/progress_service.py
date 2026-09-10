import backend.app.database as database

from backend.app.models import (
    LearnerProgressResponse,
    LearnerSkillProgress,
)



# ==================================================
# INDEPENDENCE TREND
# ==================================================
#
# Daha yüksek skor = daha az yardım = daha fazla bağımsızlık.
#
# DEMONSTRATE → en fazla yardım
# NONE        → hiç yardım yok
ASSISTANCE_INDEPENDENCE_SCORE = {
    "DEMONSTRATE": 0,
    "TEACH": 1,
    "GUIDE": 2,
    "NUDGE": 3,
    "NONE": 4,
}


def calculate_independence_trend(
    evidence,
) -> str:

    # Tek evidence ile "gelişiyor mu?" diyemeyiz.
    if len(evidence) < 2:
        return "insufficient_data"

    first_assistance = evidence[0]["assistance_level"]
    last_assistance = evidence[-1]["assistance_level"]

    first_score = ASSISTANCE_INDEPENDENCE_SCORE[
        first_assistance
    ]
    last_score = ASSISTANCE_INDEPENDENCE_SCORE[
        last_assistance
    ]

    if last_score > first_score:
        return "improving"

    if last_score < first_score:
        return "declining"

    return "stable"



# ==================================================
# LEARNER PROGRESS SERVICE
# ==================================================
#
# DB'deki ham skill state + learning evidence verilerini
# frontend'in kolay kullanabileceği bir progress modeline dönüştürür.
#
# Akış:
#
# learner_id
# ↓
# skill_states
# ↓
# her skill için learning_evidence
# ↓
# success rate + son assistance level
# ↓
# LearnerProgressResponse


def get_learner_progress(
    learner_id: str,
) -> LearnerProgressResponse:

    skill_states = database.get_skill_states_by_learner(
        learner_id
    )

    skill_progress_list = []

    for skill_state in skill_states:

        skill_name = skill_state["skill_name"]

        evidence = database.get_learning_evidence_by_skill(
            learner_id=learner_id,
            skill_name=skill_name,
        )

        attempts = skill_state["attempts"]
        successful_attempts = skill_state[
            "successful_attempts"
        ]

        # Henüz attempt yoksa 0'a bölme hatası olmaması için
        # success rate = 0.0 kabul ediyoruz.
        if attempts == 0:
            success_rate = 0.0
        else:
            success_rate = round(
                successful_attempts / attempts,
                2,
            )

        # Evidence varsa en son kaydın assistance level'ını al.
        # Evidence yoksa None.
        if evidence:
            last_assistance_level = evidence[-1][
                "assistance_level"
            ]
        else:
            last_assistance_level = None

        independence_trend = calculate_independence_trend(
                evidence
        )

        practice_priority = calculate_practice_priority(
            status=skill_state["status"],
            success_rate=success_rate,
            independence_trend=independence_trend,
        )
        
        skill_progress = LearnerSkillProgress(
            skill_name=skill_name,
            status=skill_state["status"],
            attempts=attempts,
            successful_attempts=successful_attempts,
            success_rate=success_rate,
            last_assistance_level=last_assistance_level,
            independence_trend=independence_trend,
            practice_priority=practice_priority,
        )

        skill_progress_list.append(
            skill_progress
        )

    return LearnerProgressResponse(
        learner_id=learner_id,
        skills=skill_progress_list,
    )

def calculate_practice_priority(
    status: str,
    success_rate: float,
    independence_trend: str,
) -> str:

    # Skill henüz yeni ise Practice önceliği yüksektir.
    if status == "new":
        return "high"

    # Learning aşamasında ve başarı düşükse
    # daha fazla pratik gerekir.
    if status == "learning":
        if success_rate < 0.7:
            return "high"

        return "medium"

    # Practicing aşamasında ama bağımsızlık geriliyorsa
    # Practice tekrar önemli hale gelir.
    if status == "practicing":
        if independence_trend == "declining":
            return "medium"

        return "low"

    # Comfortable seviyesinde ekstra Practice
    # şu anda öncelikli değildir.
    if status == "comfortable":
        return "none"

    return "none"