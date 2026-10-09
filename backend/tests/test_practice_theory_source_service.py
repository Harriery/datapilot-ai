from backend.app.practice_source_cache_service import (
    PRACTICE_SOURCE_CACHE,
)
from backend.app.practice_theory_source_service import (
    get_exercism_python_theory_concept,
    list_exercism_python_theory_concepts,
)


def test_python_theory_catalog_maps_multiple_concepts():
    result = list_exercism_python_theory_concepts(
        learner_id="learner-001",
        subtopic_id="loops",
    )

    assert result.topic_id == "python"
    assert result.subtopic_id == "loops"
    assert [
        item.concept_id
        for item in result.concepts
    ] == [
        "loops",
        "iteration",
    ]


def test_python_theory_concept_loads_on_demand_and_caches():
    PRACTICE_SOURCE_CACHE.clear()
    calls = []

    def loader(concept_id: str) -> str:
        calls.append(concept_id)
        return (
            "# Loops\n\n"
            "Python has for and while loops."
        )

    first = get_exercism_python_theory_concept(
        learner_id="learner-001",
        concept_id="loops",
        text_loader=loader,
    )

    second = get_exercism_python_theory_concept(
        learner_id="learner-002",
        concept_id="loops",
        text_loader=loader,
    )

    assert first.cached is False
    assert second.cached is True
    assert second.learner_id == "learner-002"
    assert len(first.content_hash) == 64
    assert calls == ["loops"]


def test_python_theory_rejects_unknown_concept():
    try:
        get_exercism_python_theory_concept(
            learner_id="learner-001",
            concept_id="not-real",
            text_loader=lambda _: "unused",
        )
    except ValueError as exc:
        assert (
            "Unsupported Python theory concept"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Unknown theory concept should fail."
        )



def test_incomplete_exercism_theory_uses_python_docs_fallback():
    PRACTICE_SOURCE_CACHE.clear()
    calls = []

    result = get_exercism_python_theory_concept(
        learner_id="learner-001",
        concept_id="list-comprehensions",
        text_loader=lambda _: (
            "#TODO: Add about for this concept."
        ),
        python_docs_loader=lambda concept_id: (
            calls.append(concept_id)
            or (
                "List Comprehensions\n"
                "List comprehensions provide a concise way "
                "to create lists using an expression and for clause."
            )
        ),
    )

    assert result.source_id == "python-docs"
    assert result.source_path == "datastructures.rst"
    assert "PSF-2.0" in result.attribution
    assert calls == ["list-comprehensions"]
