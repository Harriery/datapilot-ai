from __future__ import annotations

import json
from collections.abc import Callable
from urllib.request import Request, urlopen

from backend.app.models import (
    PracticeExerciseSourceItem,
    PracticeExerciseSourceResponse,
)


EXERCISM_CONFIG_URL = (
    "https://raw.githubusercontent.com/"
    "exercism/python/main/config.json"
)

EXERCISM_ATTRIBUTION = (
    "Source: Exercism Python Track (MIT License)"
)

PYTHON_SUBTOPIC_TAGS: dict[str, set[str]] = {
    "variables_types": {
        "basics",
        "numbers",
        "strings",
        "bools",
    },
    "conditionals": {
        "conditionals",
        "comparisons",
        "bools",
    },
    "loops": {
        "loops",
        "iteration",
    },
    "lists_dictionaries": {
        "lists",
        "list-methods",
        "dicts",
        "dict-methods",
    },
    "functions": {
        "functions",
        "function-arguments",
        "higher-order-functions",
    },
    "comprehensions": {
        "list-comprehensions",
        "generator-expressions",
    },
    "exceptions": {
        "raising-and-handling-errors",
        "user-defined-errors",
    },
}

EXERCISM_DIFFICULTY_BANDS: dict[str, set[int]] = {
    "easy": {1},
    "medium": {2, 3},
    "hard": {4, 5},
}


def _load_exercism_python_config() -> dict:
    request = Request(
        EXERCISM_CONFIG_URL,
        headers={
            "User-Agent":
                "DataPilot-Practice-Adapter/1.0"
        },
    )

    with urlopen(
        request,
        timeout=10,
    ) as response:
        payload = response.read().decode(
            "utf-8"
        )

    value = json.loads(payload)

    if not isinstance(value, dict):
        raise ValueError(
            "Exercism config response is invalid."
        )

    return value


def map_exercism_difficulty(
    source_difficulty: int,
) -> str | None:
    for difficulty, values in (
        EXERCISM_DIFFICULTY_BANDS.items()
    ):
        if source_difficulty in values:
            return difficulty

    return None


def _exercise_matches_subtopic(
    exercise: dict,
    *,
    subtopic_id: str,
) -> bool:
    target_tags = PYTHON_SUBTOPIC_TAGS.get(
        subtopic_id
    )

    if not target_tags:
        return False

    practices = exercise.get(
        "practices",
        [],
    )

    if not isinstance(practices, list):
        return False

    return bool(
        target_tags.intersection(
            str(item)
            for item in practices
        )
    )


def list_exercism_python_exercises(
    *,
    learner_id: str,
    subtopic_id: str,
    difficulty: str,
    config_loader: Callable[
        [],
        dict,
    ] = _load_exercism_python_config,
) -> PracticeExerciseSourceResponse:
    if subtopic_id not in PYTHON_SUBTOPIC_TAGS:
        raise ValueError(
            "Unsupported Python practice subtopic."
        )

    if difficulty not in EXERCISM_DIFFICULTY_BANDS:
        raise ValueError(
            "Unsupported Practice difficulty."
        )

    config = config_loader()

    exercises = (
        config.get(
            "exercises",
            {},
        )
        .get(
            "practice",
            [],
        )
    )

    if not isinstance(exercises, list):
        raise ValueError(
            "Exercism practice exercise list is invalid."
        )

    items: list[
        PracticeExerciseSourceItem
    ] = []

    for exercise in exercises:
        if not isinstance(
            exercise,
            dict,
        ):
            continue

        if not _exercise_matches_subtopic(
            exercise,
            subtopic_id=subtopic_id,
        ):
            continue

        source_difficulty = exercise.get(
            "difficulty"
        )

        if not isinstance(
            source_difficulty,
            int,
        ):
            continue

        mapped_difficulty = (
            map_exercism_difficulty(
                source_difficulty
            )
        )

        if mapped_difficulty != difficulty:
            continue

        slug = exercise.get(
            "slug"
        )
        name = exercise.get(
            "name"
        )

        if (
            not isinstance(slug, str)
            or not isinstance(name, str)
        ):
            continue

        practices = exercise.get(
            "practices",
            [],
        )
        prerequisites = exercise.get(
            "prerequisites",
            [],
        )

        items.append(
            PracticeExerciseSourceItem(
                source_id="exercism-python",
                source_exercise_id=slug,
                title=name,
                source_difficulty=(
                    source_difficulty
                ),
                difficulty=difficulty,
                practices=[
                    str(item)
                    for item in practices
                ],
                prerequisites=[
                    str(item)
                    for item in prerequisites
                ],
                mastery_signals=[
                    "correct_application"
                ],
                attribution=(
                    EXERCISM_ATTRIBUTION
                ),
            )
        )

    return PracticeExerciseSourceResponse(
        learner_id=learner_id,
        topic_id="python",
        subtopic_id=subtopic_id,
        practice_mode="code",
        difficulty=difficulty,
        source_id="exercism-python",
        exercises=items,
    )
