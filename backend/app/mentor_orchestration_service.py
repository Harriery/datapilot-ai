from __future__ import annotations

from typing import Iterable


LEARNING_PHASES = (
    "observe",
    "reason",
    "decide",
    "implement",
    "validate",
    "explain",
)

ASSISTANCE_BY_SKILL_STATUS = {
    "new": "GUIDE",
    "learning": "GUIDE",
    "practicing": "NUDGE",
    "comfortable": "NONE",
}

EXPLICIT_HELP_MARKERS = (
    "adım adım",
    "adim adim",
    "anlamadım",
    "anlamadim",
    "bilmiyorum",
    "ne yapmam gerekiyor",
    "nasıl yapacağım",
    "nasil yapacagim",
    "öğretir misin",
    "ogretir misin",
    "step by step",
    "i don't understand",
    "i dont understand",
    "i don't know",
    "i dont know",
    "teach me",
)


def determine_assistance_level(
    *,
    skill_status: str | None,
    learner_message: str = "",
    misconceptions: Iterable[str] = (),
) -> str:
    message = learner_message.casefold()

    if any(
        marker in message
        for marker in EXPLICIT_HELP_MARKERS
    ):
        return "GUIDE"

    misconception_list = list(
        misconceptions
    )
    if len(
        misconception_list
    ) != len(
        set(misconception_list)
    ):
        return "GUIDE"

    return ASSISTANCE_BY_SKILL_STATUS.get(
        skill_status,
        "GUIDE",
    )


def determine_next_learning_phase(
    *,
    current_phase: str,
    is_evidence: bool,
    success: bool | None,
) -> str:
    if (
        not is_evidence
        or success is not True
    ):
        return current_phase

    if current_phase == "completed":
        return "completed"

    if current_phase not in LEARNING_PHASES:
        return current_phase

    current_index = LEARNING_PHASES.index(
        current_phase
    )

    if current_index == (
        len(LEARNING_PHASES) - 1
    ):
        return "completed"

    return LEARNING_PHASES[
        current_index + 1
    ]
