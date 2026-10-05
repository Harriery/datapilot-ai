import backend.app.database as database

from backend.app.models import (
    PracticeTheoryAnswerRequest,
    PracticeTheoryCheckCreateRequest,
    PracticeTheoryCheckGenerated,
    PracticeTheoryConceptContent,
)
from backend.app.practice_source_cache_service import (
    PRACTICE_SOURCE_CACHE,
)
from backend.app.practice_theory_check_service import (
    create_python_theory_check,
    review_python_theory_answer,
)


def _seed(tmp_path):
    database.DATABASE_PATH = (
        tmp_path / "practice_theory_check.db"
    )
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-theory",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
        preferred_language="en",
    )


def _source(
    learner_id: str,
) -> PracticeTheoryConceptContent:
    return PracticeTheoryConceptContent(
        learner_id=learner_id,
        source_id="exercism-python",
        concept_id="loops",
        title="Loops",
        source_path="concepts/loops/about.md",
        source_text=(
            "# Loops\n\n"
            "A for loop iterates over items in an iterable. "
            "A while loop repeats while its condition is true."
        ),
        attribution=(
            "Source: Exercism Python Track (MIT License)"
        ),
        content_hash="source-hash-loops",
        cached=False,
    )


def _generated():
    return PracticeTheoryCheckGenerated(
        question=(
            "Which statement best describes a Python for loop?"
        ),
        options=[
            "It iterates over items in an iterable.",
            "It only runs while a Boolean condition is true.",
            "It creates a dictionary automatically.",
            "It can only iterate over numbers.",
        ],
        correct_index=0,
        explanation=(
            "A for loop iterates over items in an iterable."
        ),
    )


def _request():
    return PracticeTheoryCheckCreateRequest(
        learner_id="learner-theory",
        subtopic_id="loops",
        concept_id="loops",
        difficulty="easy",
        language="en",
    )


def test_theory_check_keeps_correct_answer_private(
    tmp_path,
    monkeypatch,
):
    _seed(tmp_path)
    PRACTICE_SOURCE_CACHE.clear()

    monkeypatch.setattr(
        "backend.app.practice_theory_check_service."
        "get_exercism_python_theory_concept",
        lambda learner_id, concept_id: (
            _source(learner_id)
        ),
    )

    result = create_python_theory_check(
        request=_request(),
        generator=lambda **kwargs: _generated(),
    )

    public_payload = result.model_dump()

    assert result.challenge.challenge_type == (
        "multiple_choice"
    )
    assert result.challenge.options == (
        _generated().options
    )
    assert "correct_index" not in str(
        public_payload
    )
    assert "expected_answer" not in str(
        public_payload
    )

    record = database.get_practice_challenge(
        challenge_id=(
            result.challenge.challenge_id
        ),
        learner_id="learner-theory",
    )

    assert record is not None
    assert record.validation_spec is not None
    assert (
        record.validation_spec.expected_answer
        == _generated().options[0]
    )


def test_theory_check_generation_is_cached(
    tmp_path,
    monkeypatch,
):
    _seed(tmp_path)
    PRACTICE_SOURCE_CACHE.clear()
    calls = []

    monkeypatch.setattr(
        "backend.app.practice_theory_check_service."
        "get_exercism_python_theory_concept",
        lambda learner_id, concept_id: (
            _source(learner_id)
        ),
    )

    def generator(**kwargs):
        calls.append(kwargs)
        return _generated()

    create_python_theory_check(
        request=_request(),
        generator=generator,
    )
    create_python_theory_check(
        request=_request(),
        generator=generator,
    )

    assert len(calls) == 1


def test_correct_theory_answer_records_practice_mastery_only(
    tmp_path,
    monkeypatch,
):
    _seed(tmp_path)
    PRACTICE_SOURCE_CACHE.clear()

    monkeypatch.setattr(
        "backend.app.practice_theory_check_service."
        "get_exercism_python_theory_concept",
        lambda learner_id, concept_id: (
            _source(learner_id)
        ),
    )

    challenge = create_python_theory_check(
        request=_request(),
        generator=lambda **kwargs: _generated(),
    )

    result = review_python_theory_answer(
        request=PracticeTheoryAnswerRequest(
            learner_id="learner-theory",
            challenge_id=(
                challenge.challenge.challenge_id
            ),
            answer=_generated().options[0],
        )
    )

    assert result.success is True
    assert result.mastery.status == "building"

    signals = {
        item.signal: item
        for item in result.mastery.signals
    }

    assert signals[
        "concept_coverage"
    ].demonstrated is True
    assert signals[
        "independent_completion"
    ].demonstrated is True
    assert signals[
        "correct_application"
    ].demonstrated is False

    assert database.get_skill_state(
        "learner-theory",
        "practice_python_loops",
    ) is None


def test_wrong_theory_answer_does_not_demonstrate_concept(
    tmp_path,
    monkeypatch,
):
    _seed(tmp_path)
    PRACTICE_SOURCE_CACHE.clear()

    monkeypatch.setattr(
        "backend.app.practice_theory_check_service."
        "get_exercism_python_theory_concept",
        lambda learner_id, concept_id: (
            _source(learner_id)
        ),
    )

    challenge = create_python_theory_check(
        request=_request(),
        generator=lambda **kwargs: _generated(),
    )

    result = review_python_theory_answer(
        request=PracticeTheoryAnswerRequest(
            learner_id="learner-theory",
            challenge_id=(
                challenge.challenge.challenge_id
            ),
            answer=_generated().options[1],
        )
    )

    assert result.success is False

    signals = {
        item.signal: item
        for item in result.mastery.signals
    }

    assert signals[
        "concept_coverage"
    ].demonstrated is False
    assert signals[
        "independent_completion"
    ].demonstrated is False
