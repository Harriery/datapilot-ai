import backend.app.database as database

from backend.app.models import (
    LearnerProgressResponse,
    LearnerSkillProgress,
    MentorDependencyPoint,
    OverallReadiness,
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

def assistance_level_to_percent(
    assistance_level: str | None,
) -> int:

    if assistance_level is None:
        return 0

    score = ASSISTANCE_INDEPENDENCE_SCORE[
        assistance_level
    ]

    return round(
        score
        / max(ASSISTANCE_INDEPENDENCE_SCORE.values())
        * 100
    )


def get_evidence_value(
    evidence_item,
    key: str,
    default=None,
):
    try:
        return evidence_item[key]

    except (
        KeyError,
        IndexError,
        TypeError,
    ):
        return default


def build_mentor_dependency_history(
    evidence_items,
) -> list[MentorDependencyPoint]:

    sorted_evidence = sorted(
        evidence_items,
        key=lambda item: (
            item["id"] is None,
            (
                item["id"]
                if item["id"] is not None
                else item["sequence"]
            ),
        ),
    )

    history = []

    for attempt_number, item in enumerate(
        sorted_evidence,
        start=1,
    ):
        assistance_level = item[
            "assistance_level"
        ]

        history.append(
            MentorDependencyPoint(
                attempt_number=attempt_number,
                skill_name=item["skill_name"],
                assistance_level=assistance_level,
                independence_percent=(
                    assistance_level_to_percent(
                        assistance_level
                    )
                ),
                created_at=item["created_at"],
            )
        )

    return history


def calculate_overall_readiness(
    skills: list[LearnerSkillProgress],
) -> OverallReadiness:

    total_skills = len(skills)

    total_attempts = sum(
        skill.attempts
        for skill in skills
    )

    successful_attempts = sum(
        skill.successful_attempts
        for skill in skills
    )

    if total_attempts == 0:
        knowledge_score = 0
    else:
        knowledge_score = round(
            successful_attempts
            / total_attempts
            * 100
        )

    covered_skills = sum(
        1
        for skill in skills
        if skill.attempts > 0
    )

    if total_skills == 0:
        skill_coverage = 0
    else:
        skill_coverage = round(
            covered_skills
            / total_skills
            * 100
        )

    independence_scores = [
        assistance_level_to_percent(
            skill.last_assistance_level
        )
        for skill in skills
        if skill.last_assistance_level
        is not None
    ]

    if independence_scores:
        independence_score = round(
            sum(independence_scores)
            / len(independence_scores)
        )
    else:
        independence_score = 0

    score = round(
        knowledge_score * 0.40
        + independence_score * 0.40
        + skill_coverage * 0.20
    )

    if (
        score >= 80
        and knowledge_score >= 70
        and independence_score >= 75
        and skill_coverage >= 60
    ):
        level = "INDEPENDENT"

    elif score >= 55:
        level = "NUDGE"

    else:
        level = "GUIDE"

    return OverallReadiness(
        level=level,
        score=score,
        knowledge_score=knowledge_score,
        independence_score=independence_score,
        skill_coverage=skill_coverage,
        covered_skills=covered_skills,
        total_skills=total_skills,
        total_attempts=total_attempts,
    )

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

    all_evidence = []
    evidence_sequence = 0

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

        for evidence_item in evidence:

            evidence_sequence += 1

            all_evidence.append(
                {
                    "id": get_evidence_value(
                        evidence_item,
                        "id",
                    ),
                    "sequence": evidence_sequence,
                    "skill_name": skill_name,
                    "assistance_level": (
                        evidence_item[
                            "assistance_level"
                        ]
                    ),
                    "created_at": (
                        get_evidence_value(
                            evidence_item,
                            "created_at",
                        )
                    ),
                }
            )


    mentor_dependency_history = (
        build_mentor_dependency_history(
            all_evidence
        )
    )

    overall_readiness = (
        calculate_overall_readiness(
            skill_progress_list
        )
    )

    return LearnerProgressResponse(
        learner_id=learner_id,
        skills=skill_progress_list,
        mentor_dependency_history=(
            mentor_dependency_history
        ),
        overall_readiness=(
            overall_readiness
        ),
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