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

PYTHON_DOCS_RAW_ROOT = (
    "https://raw.githubusercontent.com/"
    "python/cpython/main/Doc/tutorial"
)

PYTHON_DOCS_ATTRIBUTION = (
    "Source: Python Documentation (PSF-2.0 License)"
)

PYTHON_DOCS_CONCEPT_PATHS = {
    "list-comprehensions": "datastructures.rst",
    "raising-and-handling-errors": "errors.rst",
}

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


def _source_is_placeholder(
    source_text: str,
) -> bool:
    normalized = (
        source_text
        .strip()
        .casefold()
    )

    return (
        len(normalized) < 200
        and "todo" in normalized
    )


def _extract_python_docs_section(
    *,
    concept_id: str,
    source_text: str,
) -> str:
    if concept_id == "list-comprehensions":
        start_marker = "List Comprehensions\n-------------------"
        end_marker = "Nested List Comprehensions\n--------------------------"
    elif concept_id == "raising-and-handling-errors":
        start_marker = "Handling Exceptions\n==================="
        end_marker = "User-defined Exceptions\n======================="
    else:
        return source_text

    start = source_text.find(
        start_marker
    )

    if start < 0:
        raise ValueError(
            "Required Python documentation section was not found."
        )

    end = source_text.find(
        end_marker,
        start + len(start_marker),
    )

    if end < 0:
        end = len(source_text)

    return source_text[
        start:end
    ].strip()


def _load_python_docs_text(
    concept_id: str,
) -> str:
    path = PYTHON_DOCS_CONCEPT_PATHS.get(
        concept_id
    )

    if path is None:
        raise ValueError(
            "No official Python documentation fallback "
            "is configured for this concept."
        )

    request = Request(
        f"{PYTHON_DOCS_RAW_ROOT}/{path}",
        headers={
            "User-Agent":
                "DataPilot-Practice-Adapter/1.0"
        },
    )

    with urlopen(
        request,
        timeout=10,
    ) as response:
        source_text = (
            response.read().decode(
                "utf-8"
            )
        )

    return _extract_python_docs_section(
        concept_id=concept_id,
        source_text=source_text,
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
                source_id=(
                    "python-docs"
                    if concept_id
                    in PYTHON_DOCS_CONCEPT_PATHS
                    else "exercism-python"
                ),
                concept_id=concept_id,
                title=_title_from_concept_id(
                    concept_id
                ),
                source_path=(
                    PYTHON_DOCS_CONCEPT_PATHS[
                        concept_id
                    ]
                    if concept_id
                    in PYTHON_DOCS_CONCEPT_PATHS
                    else _concept_path(
                        concept_id
                    )
                ),
                attribution=(
                    PYTHON_DOCS_ATTRIBUTION
                    if concept_id
                    in PYTHON_DOCS_CONCEPT_PATHS
                    else EXERCISM_ATTRIBUTION
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
    python_docs_loader: Callable[
        [str],
        str,
    ] = _load_python_docs_text,
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

    source_id = "exercism-python"
    source_path = _concept_path(
        concept_id
    )
    attribution = (
        EXERCISM_ATTRIBUTION
    )

    if _source_is_placeholder(
        source_text
    ):
        if (
            concept_id
            not in PYTHON_DOCS_CONCEPT_PATHS
        ):
            raise ValueError(
                "Theory source content is incomplete."
            )

        source_text = (
            python_docs_loader(
                concept_id
            )
        )
        source_id = "python-docs"
        source_path = (
            PYTHON_DOCS_CONCEPT_PATHS[
                concept_id
            ]
        )
        attribution = (
            PYTHON_DOCS_ATTRIBUTION
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
        source_id=source_id,
        concept_id=concept_id,
        title=_title_from_concept_id(
            concept_id
        ),
        source_path=source_path,
        source_text=source_text,
        attribution=attribution,
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
