import pytest

from backend.app.practice_exercism_adapter import (
    list_exercism_python_exercises,
    map_exercism_difficulty,
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
