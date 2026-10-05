import pytest

from backend.app.practice_exercism_adapter import (
    get_exercism_python_exercise_content,
    get_exercism_python_validation_bundle,
    list_exercism_python_exercises,
    map_exercism_difficulty,
)
from backend.app.practice_source_cache_service import (
    PRACTICE_SOURCE_CACHE,
)


def _config():
    return {
        "exercises": {
            "practice": [
                {
                    "slug": "binary-search",
                    "name": "Binary Search",
                    "practices": ["loops"],
                    "prerequisites": ["lists", "loops"],
                    "difficulty": 1,
                },
                {
                    "slug": "eliuds-eggs",
                    "name": "Eliud's Eggs",
                    "practices": ["loops"],
                    "prerequisites": ["loops"],
                    "difficulty": 2,
                },
                {
                    "slug": "saddle-points",
                    "name": "Saddle Points",
                    "practices": ["loops"],
                    "prerequisites": ["loops"],
                    "difficulty": 3,
                },
                {
                    "slug": "change",
                    "name": "Change",
                    "practices": ["loops"],
                    "prerequisites": ["loops"],
                    "difficulty": 4,
                },
                {
                    "slug": "word-count",
                    "name": "Word Count",
                    "practices": ["dicts"],
                    "prerequisites": ["dicts"],
                    "difficulty": 2,
                },
            ]
        }
    }


def test_exercism_difficulty_bands_are_deterministic():
    assert map_exercism_difficulty(1) == "easy"
    assert map_exercism_difficulty(2) == "medium"
    assert map_exercism_difficulty(3) == "medium"
    assert map_exercism_difficulty(4) == "hard"
    assert map_exercism_difficulty(5) == "hard"
    assert map_exercism_difficulty(6) is None


def test_exercism_adapter_filters_by_subtopic_and_difficulty():
    result = list_exercism_python_exercises(
        learner_id="learner-001",
        subtopic_id="loops",
        difficulty="medium",
        config_loader=_config,
    )

    assert result.topic_id == "python"
    assert result.subtopic_id == "loops"
    assert result.practice_mode == "code"
    assert result.difficulty == "medium"

    ids = [
        item.source_exercise_id
        for item in result.exercises
    ]

    assert ids == [
        "eliuds-eggs",
        "saddle-points",
    ]

    assert all(
        item.mastery_signals
        == ["correct_application"]
        for item in result.exercises
    )


def test_exercism_adapter_maps_lists_and_dictionaries():
    result = list_exercism_python_exercises(
        learner_id="learner-001",
        subtopic_id="lists_dictionaries",
        difficulty="medium",
        config_loader=_config,
    )

    assert [
        item.source_exercise_id
        for item in result.exercises
    ] == ["word-count"]


def test_exercism_adapter_rejects_unknown_subtopic():
    with pytest.raises(
        ValueError,
        match="Unsupported Python practice subtopic",
    ):
        list_exercism_python_exercises(
            learner_id="learner-001",
            subtopic_id="unknown",
            difficulty="easy",
            config_loader=_config,
        )


def test_exercism_adapter_keeps_attribution():
    result = list_exercism_python_exercises(
        learner_id="learner-001",
        subtopic_id="loops",
        difficulty="easy",
        config_loader=_config,
    )

    assert result.exercises
    assert all(
        "Exercism Python Track"
        in item.attribution
        for item in result.exercises
    )



def _exercise_file_loader(
    exercise_id: str,
    relative_path: str,
) -> str:
    assert exercise_id == "binary-search"

    if relative_path == ".docs/instructions.md":
        return "Implement binary search."

    if relative_path == ".meta/config.json":
        return (
            '{"files":{"solution":["binary_search.py"],'
            '"test":["binary_search_test.py"],'
            '"example":[".meta/example.py"]},'
            '"blurb":"Implement binary search."}'
        )

    raise AssertionError(
        f"Unexpected file request: {relative_path}"
    )


def test_exercism_content_loads_only_public_bundle():
    PRACTICE_SOURCE_CACHE.clear()

    result = (
        get_exercism_python_exercise_content(
            learner_id="learner-001",
            exercise_id="binary-search",
            title="Binary Search",
            text_loader=_exercise_file_loader,
        )
    )

    assert result.instructions == (
        "Implement binary search."
    )
    assert result.solution_filename == (
        "binary_search.py"
    )
    assert result.starter_code is None
    assert result.cached is False
    assert len(result.content_hash) == 64


def test_exercism_content_uses_disposable_cache():
    PRACTICE_SOURCE_CACHE.clear()
    calls = []

    def loader(
        exercise_id: str,
        relative_path: str,
    ) -> str:
        calls.append(relative_path)
        return _exercise_file_loader(
            exercise_id,
            relative_path,
        )

    first = (
        get_exercism_python_exercise_content(
            learner_id="learner-001",
            exercise_id="binary-search",
            title="Binary Search",
            text_loader=loader,
        )
    )

    second = (
        get_exercism_python_exercise_content(
            learner_id="learner-002",
            exercise_id="binary-search",
            title="Binary Search",
            text_loader=loader,
        )
    )

    assert first.cached is False
    assert second.cached is True
    assert second.learner_id == "learner-002"
    assert calls == [
        ".docs/instructions.md",
        ".meta/config.json",
    ]


def test_exercism_content_does_not_fetch_example_solution():
    PRACTICE_SOURCE_CACHE.clear()
    requested_paths = []

    def loader(
        exercise_id: str,
        relative_path: str,
    ) -> str:
        requested_paths.append(relative_path)
        return _exercise_file_loader(
            exercise_id,
            relative_path,
        )

    get_exercism_python_exercise_content(
        learner_id="learner-001",
        exercise_id="binary-search",
        title="Binary Search",
        text_loader=loader,
    )

    assert ".meta/example.py" not in requested_paths
    assert "binary_search_test.py" not in requested_paths



def _validation_file_loader(
    exercise_id: str,
    relative_path: str,
) -> str:
    assert exercise_id == "binary-search"

    if relative_path == ".meta/config.json":
        return (
            '{"files":{"solution":["binary_search.py"],'
            '"test":["binary_search_test.py"],'
            '"example":[".meta/example.py"]}}'
        )

    if relative_path == "binary_search_test.py":
        return (
            "import unittest\n"
            "from binary_search import find\n"
            "\n"
            "class BinarySearchTest(unittest.TestCase):\n"
            "    def test_one(self):\n"
            "        self.assertEqual(find([1], 1), 0)\n"
        )

    raise AssertionError(
        f"Unexpected validation file: {relative_path}"
    )


def test_exercism_validation_bundle_loads_only_tests():
    PRACTICE_SOURCE_CACHE.clear()

    result = get_exercism_python_validation_bundle(
        learner_id="learner-001",
        exercise_id="binary-search",
        text_loader=_validation_file_loader,
    )

    assert result.solution_filename == (
        "binary_search.py"
    )
    assert len(result.test_files) == 1
    assert result.test_files[0].path == (
        "binary_search_test.py"
    )
    assert ".meta/example.py" not in [
        item.path
        for item in result.test_files
    ]
    assert len(result.content_hash) == 64


def test_exercism_validation_bundle_uses_cache():
    PRACTICE_SOURCE_CACHE.clear()
    calls = []

    def loader(
        exercise_id: str,
        relative_path: str,
    ) -> str:
        calls.append(relative_path)
        return _validation_file_loader(
            exercise_id,
            relative_path,
        )

    first = get_exercism_python_validation_bundle(
        learner_id="learner-001",
        exercise_id="binary-search",
        text_loader=loader,
    )
    second = get_exercism_python_validation_bundle(
        learner_id="learner-002",
        exercise_id="binary-search",
        text_loader=loader,
    )

    assert first.cached is False
    assert second.cached is True
    assert second.learner_id == "learner-002"
    assert calls == [
        ".meta/config.json",
        "binary_search_test.py",
    ]


def test_exercism_validation_bundle_rejects_unsafe_paths():
    PRACTICE_SOURCE_CACHE.clear()

    def loader(
        exercise_id: str,
        relative_path: str,
    ) -> str:
        if relative_path == ".meta/config.json":
            return (
                '{"files":{"solution":["binary_search.py"],'
                '"test":["../escape.py"]}}'
            )

        raise AssertionError(
            "Unsafe test path should not be loaded."
        )

    with pytest.raises(
        ValueError,
        match="Unsafe Exercism test path",
    ):
        get_exercism_python_validation_bundle(
            learner_id="learner-001",
            exercise_id="binary-search",
            text_loader=loader,
        )
