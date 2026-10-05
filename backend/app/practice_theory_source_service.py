from __future__ import annotations

import hashlib
from collections.abc import Callable
from urllib.request import Request, urlopen

from backend.app.models import (
    PracticeTheoryConceptContent,
    PracticeTheoryConceptItem,
    PracticeTheoryConceptResponse,
)
from backend.app.practice_source_cache_service import (
    PRACTICE_SOURCE_CACHE,
)


EXERCISM_RAW_ROOT = (
    "https://raw.githubusercontent.com/"
    "exercism/python/main"
)

EXERCISM_ATTRIBUTION = (
    "Source: Exercism Python Track (MIT License)"
)

PYTHON_THEORY_CONCEPTS: dict[
    str,
    tuple[str, ...],
] = {
    "variables_types": (
        "basics",
        "bools",
        "numbers",
        "strings",
    ),
    "conditionals": (
        "conditionals",
        "bools",
        "comparisons",
    ),
    "loops": (
        "loops",
        "iteration",
    ),
    "lists_dictionaries": (
        "lists",
        "dicts",
    ),
    "functions": (
        "functions",
        "function-arguments",
    ),
    "comprehensions": (
        "list-comprehensions",
        "generator-expressions",
    ),
    "exceptions": (
        "raising-and-handling-errors",
        "user-defined-errors",
    ),
}


def _concept_path(
    concept_id: str,
) -> str:
    return (
        f"concepts/{concept_id}/about.md"
    )


def _load_concept_text(
    concept_id: str,
) -> str:
    path = _concept_path(
        concept_id
    )

    request = Request(
        f"{EXERCISM_RAW_ROOT}/{path}",
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


def _title_from_concept_id(
    concept_id: str,
) -> str:
    return (
        concept_id
        .replace("-", " ")
        .title()
    )


def list_exercism_python_theory_concepts(
    *,
    learner_id: str,
    subtopic_id: str,
) -> PracticeTheoryConceptResponse:
    concept_ids = (
        PYTHON_THEORY_CONCEPTS.get(
            subtopic_id
        )
    )

    if not concept_ids:
        raise ValueError(
            "Unsupported Python theory subtopic."
        )

    return PracticeTheoryConceptResponse(
        learner_id=learner_id,
        topic_id="python",
        subtopic_id=subtopic_id,
        source_id="exercism-python",
        concepts=[
            PracticeTheoryConceptItem(
                source_id="exercism-python",
                concept_id=concept_id,
                title=_title_from_concept_id(
                    concept_id
                ),
                source_path=_concept_path(
                    concept_id
                ),
                attribution=(
                    EXERCISM_ATTRIBUTION
                ),
            )
            for concept_id in concept_ids
        ],
    )


def get_exercism_python_theory_concept(
    *,
    learner_id: str,
    concept_id: str,
    text_loader: Callable[
        [str],
        str,
    ] = _load_concept_text,
) -> PracticeTheoryConceptContent:
    supported_ids = {
        concept_id_value
        for concept_ids
        in PYTHON_THEORY_CONCEPTS.values()
        for concept_id_value
        in concept_ids
    }

    if concept_id not in supported_ids:
        raise ValueError(
            "Unsupported Python theory concept."
        )

    cache_key = (
        "exercism-python-theory:"
        f"{concept_id}"
    )

    cached = PRACTICE_SOURCE_CACHE.get(
        cache_key
    )

    if isinstance(
        cached,
        PracticeTheoryConceptContent,
    ):
        return cached.model_copy(
            update={
                "learner_id": learner_id,
                "cached": True,
            }
        )

    source_text = text_loader(
        concept_id
    )

    if len(
        source_text.encode("utf-8")
    ) > 524288:
        raise ValueError(
            "Theory concept source is too large."
        )

    content_hash = hashlib.sha256(
        source_text.encode("utf-8")
    ).hexdigest()

    result = PracticeTheoryConceptContent(
        learner_id=learner_id,
        source_id="exercism-python",
        concept_id=concept_id,
        title=_title_from_concept_id(
            concept_id
        ),
        source_path=_concept_path(
            concept_id
        ),
        source_text=source_text,
        attribution=EXERCISM_ATTRIBUTION,
        content_hash=content_hash,
        cached=False,
    )

    PRACTICE_SOURCE_CACHE.put(
        key=cache_key,
        value=result,
        size_bytes=len(
            source_text.encode("utf-8")
        ),
    )

    return result
