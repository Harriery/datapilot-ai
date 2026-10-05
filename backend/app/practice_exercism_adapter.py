from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from urllib.request import Request, urlopen

from backend.app.models import (
    PracticeExerciseContentResponse,
    PracticeExerciseSourceItem,
    PracticeExerciseSourceResponse,
    PracticeExerciseValidationBundle,
    PracticeValidationSourceFile,
)
from backend.app.practice_source_cache_service import (
    PRACTICE_SOURCE_CACHE,
)


EXERCISM_RAW_ROOT = (
    "https://raw.githubusercontent.com/"
    "exercism/python/main"
)

EXERCISM_CONFIG_URL = (
    f"{EXERCISM_RAW_ROOT}/config.json"
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



def _load_text_url(
    url: str,
) -> str:
    request = Request(
        url,
        headers={
            "User-Agent":
                "DataPilot-Practice-Adapter/1.0"
        },
    )

    with urlopen(
        request,
        timeout=10,
    ) as response:
        return response.read().decode(
            "utf-8"
        )


def _load_exercise_file(
    exercise_id: str,
    relative_path: str,
) -> str:
    return _load_text_url(
        (
            f"{EXERCISM_RAW_ROOT}/"
            f"exercises/practice/{exercise_id}/"
            f"{relative_path}"
        )
    )


def get_exercism_python_exercise_content(
    *,
    learner_id: str,
    exercise_id: str,
    title: str,
    source_revision: str | None = None,
    text_loader: Callable[
        [str, str],
        str,
    ] = _load_exercise_file,
) -> PracticeExerciseContentResponse:
    cache_key = (
        "exercism-python:"
        f"{exercise_id}:"
        f"{source_revision or 'main'}"
    )

    cached_value = (
        PRACTICE_SOURCE_CACHE.get(
            cache_key
        )
    )

    if isinstance(
        cached_value,
        PracticeExerciseContentResponse,
    ):
        return cached_value.model_copy(
            update={
                "learner_id": learner_id,
                "cached": True,
            }
        )

    instructions = text_loader(
        exercise_id,
        ".docs/instructions.md",
    )

    meta_raw = text_loader(
        exercise_id,
        ".meta/config.json",
    )

    try:
        meta = json.loads(meta_raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Exercism exercise metadata is invalid."
        ) from exc

    if not isinstance(meta, dict):
        raise ValueError(
            "Exercism exercise metadata is invalid."
        )

    files = meta.get(
        "files",
        {},
    )

    if not isinstance(files, dict):
        files = {}

    solution_files = files.get(
        "solution",
        [],
    )

    solution_filename = (
        str(solution_files[0])
        if (
            isinstance(solution_files, list)
            and solution_files
        )
        else None
    )

    # Do not fetch .meta/example.py here.
    # A worked solution is intentionally excluded from
    # normal exercise loading.
    starter_code = None

    content_hash = hashlib.sha256(
        (
            instructions
            + "\n"
            + meta_raw
        ).encode("utf-8")
    ).hexdigest()

    result = PracticeExerciseContentResponse(
        learner_id=learner_id,
        source_id="exercism-python",
        source_exercise_id=exercise_id,
        title=title,
        instructions=instructions,
        solution_filename=solution_filename,
        starter_code=starter_code,
        attribution=EXERCISM_ATTRIBUTION,
        source_revision=source_revision,
        content_hash=content_hash,
        cached=False,
    )

    PRACTICE_SOURCE_CACHE.put(
        key=cache_key,
        value=result,
        size_bytes=len(
            (
                instructions
                + meta_raw
            ).encode("utf-8")
        ),
    )

    return result



def _safe_source_path(path: str) -> bool:
    return (
        bool(path)
        and not path.startswith("/")
        and ".." not in path.split("/")
        and "\\" not in path
    )


def get_exercism_python_validation_bundle(
    *,
    learner_id: str,
    exercise_id: str,
    source_revision: str | None = None,
    text_loader: Callable[
        [str, str],
        str,
    ] = _load_exercise_file,
) -> PracticeExerciseValidationBundle:
    cache_key = (
        "exercism-python-validation:"
        f"{exercise_id}:"
        f"{source_revision or 'main'}"
    )

    cached_value = (
        PRACTICE_SOURCE_CACHE.get(
            cache_key
        )
    )

    if isinstance(
        cached_value,
        PracticeExerciseValidationBundle,
    ):
        return cached_value.model_copy(
            update={
                "learner_id": learner_id,
                "cached": True,
            }
        )

    meta_raw = text_loader(
        exercise_id,
        ".meta/config.json",
    )

    try:
        meta = json.loads(meta_raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Exercism exercise metadata is invalid."
        ) from exc

    if not isinstance(meta, dict):
        raise ValueError(
            "Exercism exercise metadata is invalid."
        )

    files = meta.get(
        "files",
        {},
    )

    if not isinstance(files, dict):
        raise ValueError(
            "Exercism exercise file metadata is invalid."
        )

    solution_files = files.get(
        "solution",
        [],
    )
    test_files = files.get(
        "test",
        [],
    )

    if (
        not isinstance(solution_files, list)
        or not solution_files
        or not isinstance(test_files, list)
        or not test_files
    ):
        raise ValueError(
            "Exercism validation files are missing."
        )

    solution_filename = str(
        solution_files[0]
    )

    if not _safe_source_path(
        solution_filename
    ):
        raise ValueError(
            "Unsafe Exercism solution path."
        )

    if len(test_files) > 8:
        raise ValueError(
            "Too many Exercism test files."
        )

    validation_files = []
    total_bytes = len(
        meta_raw.encode("utf-8")
    )

    for raw_path in test_files:
        path = str(raw_path)

        if not _safe_source_path(path):
            raise ValueError(
                "Unsafe Exercism test path."
            )

        content = text_loader(
            exercise_id,
            path,
        )

        file_bytes = len(
            content.encode("utf-8")
        )
        total_bytes += file_bytes

        if file_bytes > 262144:
            raise ValueError(
                "Exercism test file is too large."
            )

        validation_files.append(
            PracticeValidationSourceFile(
                path=path,
                content=content,
            )
        )

    if total_bytes > 1048576:
        raise ValueError(
            "Exercism validation bundle is too large."
        )

    content_hash = hashlib.sha256(
        (
            meta_raw
            + "\n"
            + "\n".join(
                file.content
                for file in validation_files
            )
        ).encode("utf-8")
    ).hexdigest()

    result = PracticeExerciseValidationBundle(
        learner_id=learner_id,
        source_id="exercism-python",
        source_exercise_id=exercise_id,
        solution_filename=solution_filename,
        test_files=validation_files,
        attribution=EXERCISM_ATTRIBUTION,
        source_revision=source_revision,
        content_hash=content_hash,
        cached=False,
    )

    PRACTICE_SOURCE_CACHE.put(
        key=cache_key,
        value=result,
        size_bytes=total_bytes,
    )

    return result
