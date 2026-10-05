from __future__ import annotations

from collections import Counter

import backend.app.database as database

from backend.app.models import (
    PracticeMasterySignalState,
    PracticeMasterySummary,
)
from backend.app.progress_service import (
    get_evidence_value,
    parse_evidence_context,
)


REQUIRED_MASTERY_SIGNALS = (
    "concept_coverage",
    "correct_application",
    "transfer_to_new_context",
    "independent_completion",
)


def _matches_path(
    context: dict,
    *,
    topic_id: str,
    subtopic_id: str,
    practice_mode: str,
    difficulty: str,
) -> bool:
    return (
        context.get("stage") == "practice"
        and context.get("topic_id") == topic_id
        and context.get("subtopic_id") == subtopic_id
        and context.get("practice_mode") == practice_mode
        and context.get("difficulty") == difficulty
    )


def calculate_practice_mastery(
    *,
    learner_id: str,
    topic_id: str,
    subtopic_id: str,
    practice_mode: str,
    difficulty: str,
) -> PracticeMasterySummary:
    evidence_rows = (
        database.get_learning_evidence_by_learner(
            learner_id
        )
    )

    matching_rows = []

    for row in evidence_rows:
        context = parse_evidence_context(
            row
        )

        if _matches_path(
            context,
            topic_id=topic_id,
            subtopic_id=subtopic_id,
            practice_mode=practice_mode,
            difficulty=difficulty,
        ):
            matching_rows.append(
                (row, context)
            )

    signal_counts: Counter[str] = Counter()
    successful_evidence_count = 0
    independent_success_count = 0

    for row, context in matching_rows:
        success = bool(
            get_evidence_value(
                row,
                "success",
                False,
            )
        )

        if not success:
            continue

        successful_evidence_count += 1

        raw_signals = context.get(
            "mastery_signals",
            [],
        )

        if isinstance(raw_signals, list):
            for signal in raw_signals:
                if signal in REQUIRED_MASTERY_SIGNALS:
                    signal_counts[signal] += 1

        if (
            get_evidence_value(
                row,
                "assistance_level",
            )
            == "NONE"
        ):
            signal_counts[
                "independent_completion"
            ] += 1
            independent_success_count += 1

    signals = [
        PracticeMasterySignalState(
            signal=signal,
            demonstrated=(
                signal_counts[signal] > 0
            ),
            evidence_count=signal_counts[
                signal
            ],
        )
        for signal in REQUIRED_MASTERY_SIGNALS
    ]

    if not matching_rows:
        status = "not_started"
    elif all(
        signal.demonstrated
        for signal in signals
    ):
        status = "demonstrated"
    else:
        status = "building"

    return PracticeMasterySummary(
        learner_id=learner_id,
        topic_id=topic_id,
        subtopic_id=subtopic_id,
        practice_mode=practice_mode,
        difficulty=difficulty,
        status=status,
        signals=signals,
        successful_evidence_count=(
            successful_evidence_count
        ),
        independent_success_count=(
            independent_success_count
        ),
    )
