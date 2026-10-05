from __future__ import annotations

from collections.abc import Callable

from backend.app.ai_provider_service import (
    AIRuntime,
    get_ai_runtime,
)
from backend.app.ai_usage_guard import (
    guarded_chat_completions_create,
)
from backend.app.models import (
    PracticeTranslationRequest,
    PracticeTranslationResponse,
)
from backend.app.practice_source_cache_service import (
    PRACTICE_SOURCE_CACHE,
)


LANGUAGE_LABELS = {
    "tr": "Turkish",
    "nl": "Dutch",
}


def _response_text(response) -> str:
    choices = getattr(
        response,
        "choices",
        None,
    )

    if (
        not choices
        or getattr(
            choices[0],
            "message",
            None,
        ) is None
    ):
        raise ValueError(
            "Translation response did not contain text."
        )

    value = getattr(
        choices[0].message,
        "content",
        None,
    )

    if isinstance(value, str):
        return value.strip()

    raise ValueError(
        "Translation response did not contain text."
    )


def translate_practice_instructions(
    *,
    request: PracticeTranslationRequest,
    runtime_loader: Callable[
        [],
        AIRuntime,
    ] = lambda: get_ai_runtime(
        "translator"
    ),
) -> PracticeTranslationResponse:
    cache_key = (
        "practice-translation:"
        f"{request.source_id}:"
        f"{request.source_exercise_id}:"
        f"{request.content_hash}:"
        f"{request.target_language}"
    )

    cached = PRACTICE_SOURCE_CACHE.get(
        cache_key
    )

    if isinstance(
        cached,
        PracticeTranslationResponse,
    ):
        return cached.model_copy(
            update={
                "learner_id": request.learner_id,
                "cached": True,
            }
        )

    runtime = runtime_loader()

    target_label = LANGUAGE_LABELS[
        request.target_language
    ]

    instructions = (
        "Translate the exercise instructions into "
        f"{target_label}. "
        "Preserve Python identifiers, function names, "
        "variable names, code snippets, numbers, and "
        "mathematical operators exactly. "
        "Keep important technical terms in English on "
        "first use, followed by a concise translation in "
        "parentheses when useful. "
        "Do not add hints, solutions, explanations, or "
        "new requirements. "
        "Preserve the original structure, paragraphs, "
        "bullets, and emphasis as plain Markdown."
    )

    response = guarded_chat_completions_create(
        runtime.client,
        provider=runtime.provider,
        purpose="practice_translation",
        model=runtime.model,
        messages=[
            {
                "role": "system",
                "content": instructions,
            },
            {
                "role": "user",
                "content": request.source_text,
            },
        ],
        max_tokens=1800,
        temperature=0,
    )

    translated_text = _response_text(
        response
    )

    result = PracticeTranslationResponse(
        learner_id=request.learner_id,
        source_id=request.source_id,
        source_exercise_id=(
            request.source_exercise_id
        ),
        content_hash=request.content_hash,
        target_language=(
            request.target_language
        ),
        translated_text=translated_text,
        provider=runtime.provider,
        model=runtime.model,
        cached=False,
    )

    PRACTICE_SOURCE_CACHE.put(
        key=cache_key,
        value=result,
        size_bytes=len(
            translated_text.encode("utf-8")
        ),
    )

    return result
