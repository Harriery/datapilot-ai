from __future__ import annotations

from collections import defaultdict

import backend.app.database as database

from backend.app.models import (
    PracticeExerciseProgressState,
    PracticeExerciseSourceItem,
    PracticeNextExerciseResponse,
)


def choose_next_external_exercise(
    *,
    learner_id: str,
    topic_id: str,
    subtopic_id: str,
    practice_mode: str,
    difficulty: str,
    source_id: str,
    exercises: list[
        PracticeExerciseSourceItem
    ],
) -> PracticeNextExerciseResponse:
    rows = (
        database
        .list_external_practice_validation_events_for_path(
            learner_id=learner_id,
            source_id=source_id,
            topic_id=topic_id,
            subtopic_id=subtopic_id,
            practice_mode=practice_mode,
            difficulty=difficulty,
        )
    )

    history: dict[
        str,
        list[bool],
    ] = defaultdict(list)

    for row in rows:
        exercise_id = row[
            "source_exercise_id"
        ]
        history[exercise_id].append(
            bool(
                row[
                    "client_reported_success"
                ]
            )
        )

    progress = []
    completed_ids = set()

    for exercise in exercises:
        outcomes = history.get(
            exercise.source_exercise_id,
            [],
        )

        client_passes = sum(
            1
            for outcome in outcomes
            if outcome
        )

        client_failures = sum(
            1
            for outcome in outcomes
            if not outcome
        )

        if client_passes > 0:
            completed_ids.add(
                exercise.source_exercise_id
            )

        progress.append(
            PracticeExerciseProgressState(
                source_exercise_id=(
                    exercise.source_exercise_id
                ),
                attempts=len(outcomes),
                client_passes=client_passes,
                client_failures=client_failures,
                last_client_success=(
                    outcomes[-1]
                    if outcomes
                    else None
                ),
            )
        )

    by_id = {
        exercise.source_exercise_id:
            exercise
        for exercise in exercises
    }

    # Resume the most recently attempted exercise
    # when the latest client-side validation failed.
    for row in reversed(rows):
        exercise_id = row[
            "source_exercise_id"
        ]

        if exercise_id not in by_id:
            continue

        if not bool(
            row["client_reported_success"]
        ):
            return PracticeNextExerciseResponse(
                learner_id=learner_id,
                topic_id=topic_id,
                subtopic_id=subtopic_id,
                practice_mode=practice_mode,
                difficulty=difficulty,
                source_id=source_id,
                status="resume",
                exercise=by_id[
                    exercise_id
                ],
                progress=progress,
                completed_exercise_count=len(
                    completed_ids
                ),
                available_exercise_count=len(
                    exercises
                ),
            )

        break

    # Otherwise move to the first exercise that has
    # not yet had a successful client validation.
    for exercise in exercises:
        if (
            exercise.source_exercise_id
            not in completed_ids
        ):
            had_attempts = bool(
                history.get(
                    exercise.source_exercise_id
                )
            )

            return PracticeNextExerciseResponse(
                learner_id=learner_id,
                topic_id=topic_id,
                subtopic_id=subtopic_id,
                practice_mode=practice_mode,
                difficulty=difficulty,
                source_id=source_id,
                status=(
                    "next"
                    if had_attempts
                    or completed_ids
                    else "new"
                ),
                exercise=exercise,
                progress=progress,
                completed_exercise_count=len(
                    completed_ids
                ),
                available_exercise_count=len(
                    exercises
                ),
            )

    return PracticeNextExerciseResponse(
        learner_id=learner_id,
        topic_id=topic_id,
        subtopic_id=subtopic_id,
        practice_mode=practice_mode,
        difficulty=difficulty,
        source_id=source_id,
        status="cycle_complete",
        exercise=None,
        progress=progress,
        completed_exercise_count=len(
            completed_ids
        ),
        available_exercise_count=len(
            exercises
        ),
    )
