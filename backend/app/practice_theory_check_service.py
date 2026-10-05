from __future__ import annotations

import json
import re
from collections.abc import Callable
from uuid import uuid4

import backend.app.database as database

from backend.app.ai_provider_service import (
    AIRuntime,
    get_ai_runtime,
)
from backend.app.ai_usage_guard import (
    guarded_chat_completions_create,
)
from backend.app.models import (
    PracticeAttemptRequest,
    PracticeChallenge,
    PracticeChallengeRecord,
    PracticeTheoryAnswerRequest,
    PracticeTheoryAnswerResponse,
    PracticeTheoryCheckCreateRequest,
    PracticeTheoryCheckGenerated,
    PracticeTheoryCheckResponse,
    PracticeValidationSpec,
)
from backend.app.practice_mastery_service import (
    calculate_practice_mastery,
)
from backend.app.practice_service import (
    validate_practice_attempt,
)
from backend.app.practice_source_cache_service import (
    PRACTICE_SOURCE_CACHE,
)
from backend.app.practice_theory_source_service import (
    PYTHON_THEORY_CONCEPTS,
    get_exercism_python_theory_concept,
)


LANGUAGE_LABELS = {
    "en": "English",
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
            "Theory generator response did not contain text."
        )

    value = getattr(
        choices[0].message,
        "content",
        None,
    )

    if not isinstance(value, str):
        raise ValueError(
            "Theory generator response did not contain text."
        )

    return value.strip()


def _parse_generated_json(
    raw_text: str,
) -> PracticeTheoryCheckGenerated:
    text = raw_text.strip()

    if text.startswith("```"):
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Theory generator returned invalid JSON."
        ) from exc

    generated = (
        PracticeTheoryCheckGenerated
        .model_validate(payload)
    )

    if generated.correct_index >= len(
        generated.options
    ):
        raise ValueError(
            "Theory generator returned invalid correct_index."
        )

    normalized_options = [
        option.strip()
        for option in generated.options
    ]

    if (
        any(not option for option in normalized_options)
        or len(set(normalized_options))
        != len(normalized_options)
    ):
        raise ValueError(
            "Theory generator returned invalid options."
        )

    return generated.model_copy(
        update={
            "options": normalized_options,
            "question": generated.question.strip(),
            "explanation": (
                generated.explanation.strip()
            ),
        }
    )


def _generate_with_ai(
    *,
    source_text: str,
    concept_id: str,
    difficulty: str,
    language: str,
    runtime_loader: Callable[
        [],
        AIRuntime,
    ] = lambda: get_ai_runtime(
        "practice_generator"
    ),
) -> PracticeTheoryCheckGenerated:
    runtime = runtime_loader()

    target_language = (
        LANGUAGE_LABELS[language]
    )

    instructions = f"""
Create ONE multiple-choice theory check for a junior Data Engineer learning Python.

Rules:
- Use ONLY the supplied source text.
- Target concept: {concept_id}.
- Difficulty: {difficulty}.
- Write the question and options in {target_language}.
- Preserve important Python and technical terms in English when appropriate.
- Paraphrase the source; do not copy long source sentences.
- Do not ask trivia, version history, or details irrelevant to practical Python understanding.
- Exactly one option must be correct.
- Return 4 concise options.
- The explanation must explain why the correct option is correct using only the source.
- Do not include hints or extra commentary.

Return ONLY this JSON object:
{{
  "question": "...",
  "options": ["...", "...", "...", "..."],
  "correct_index": 0,
  "explanation": "..."
}}
""".strip()

    bounded_source = source_text[:18000]

    response = guarded_chat_completions_create(
        runtime.client,
        provider=runtime.provider,
        purpose="practice_theory_generation",
        model=runtime.model,
        messages=[
            {
                "role": "system",
                "content": instructions,
            },
            {
                "role": "user",
                "content": bounded_source,
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "practice_theory_check",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                        },
                        "options": {
                            "type": "array",
                            "items": {
                                "type": "string",
                            },
                            "minItems": 4,
                            "maxItems": 4,
                        },
                        "correct_index": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 3,
                        },
                        "explanation": {
                            "type": "string",
                        },
                    },
                    "required": [
                        "question",
                        "options",
                        "correct_index",
                        "explanation",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        max_completion_tokens=900,
        reasoning_format="hidden",
        reasoning_effort="low",
        temperature=0.2,
    )

    return _parse_generated_json(
        _response_text(response)
    )


def create_python_theory_check(
    *,
    request: PracticeTheoryCheckCreateRequest,
    generator: Callable[..., PracticeTheoryCheckGenerated]
    = _generate_with_ai,
) -> PracticeTheoryCheckResponse:
    concept_ids = PYTHON_THEORY_CONCEPTS.get(
        request.subtopic_id
    )

    if (
        not concept_ids
        or request.concept_id not in concept_ids
    ):
        raise ValueError(
            "Concept does not belong to the selected Python subtopic."
        )

    source = get_exercism_python_theory_concept(
        learner_id=request.learner_id,
        concept_id=request.concept_id,
    )

    cache_key = (
        "practice-theory-check:"
        f"{source.content_hash}:"
        f"{request.difficulty}:"
        f"{request.language}"
    )

    generated = PRACTICE_SOURCE_CACHE.get(
        cache_key
    )

    if not isinstance(
        generated,
        PracticeTheoryCheckGenerated,
    ):
        generated = generator(
            source_text=source.source_text,
            concept_id=request.concept_id,
            difficulty=request.difficulty,
            language=request.language,
        )

        PRACTICE_SOURCE_CACHE.put(
            key=cache_key,
            value=generated,
            size_bytes=len(
                generated.model_dump_json()
                .encode("utf-8")
            ),
        )

    correct_answer = generated.options[
        generated.correct_index
    ]

    challenge = PracticeChallenge(
        challenge_id=str(uuid4()),
        skill_name=(
            "practice_python_"
            f"{request.subtopic_id}"
        ),
        topic_id="python",
        subtopic_id=request.subtopic_id,
        practice_mode="theory",
        source_id=source.source_id,
        source_exercise_id=(
            request.concept_id
        ),
        mastery_signals=[
            "concept_coverage",
        ],
        difficulty=request.difficulty,
        challenge_type="multiple_choice",
        title=source.title,
        instructions=generated.question,
        options=generated.options,
        starter_code=None,
    )

    record = PracticeChallengeRecord(
        challenge=challenge,
        validation_spec=PracticeValidationSpec(
            validation_type="exact_answer",
            expected_answer=correct_answer,
        ),
        support_spec=None,
        expected_outcome=generated.explanation,
    )

    database.save_practice_challenge(
        learner_id=request.learner_id,
        record=record,
    )

    return PracticeTheoryCheckResponse(
        learner_id=request.learner_id,
        topic_id="python",
        subtopic_id=request.subtopic_id,
        difficulty=request.difficulty,
        concept_id=request.concept_id,
        challenge=challenge,
        attribution=source.attribution,
    )


def review_python_theory_answer(
    *,
    request: PracticeTheoryAnswerRequest,
) -> PracticeTheoryAnswerResponse:
    record = database.get_practice_challenge(
        challenge_id=request.challenge_id,
        learner_id=request.learner_id,
    )

    if record is None:
        raise ValueError(
            "Practice theory challenge not found."
        )

    challenge = record.challenge

    if (
        challenge.topic_id != "python"
        or challenge.practice_mode != "theory"
        or challenge.challenge_type
        != "multiple_choice"
        or challenge.source_exercise_id is None
        or challenge.subtopic_id is None
    ):
        raise ValueError(
            "Challenge is not a Python theory check."
        )

    attempt = PracticeAttemptRequest(
        learner_id=request.learner_id,
        challenge_id=request.challenge_id,
        answer=request.answer,
    )

    validation = validate_practice_attempt(
        attempt=attempt
    )

    database.save_practice_attempt(
        attempt=attempt,
        validation=validation,
        diagnosis=None,
        mentor_decision=None,
        mentor_support=None,
    )

    context = {
        "stage": "practice",
        "task_type": "practice_theory_check",
        "topic_id": "python",
        "subtopic_id": challenge.subtopic_id,
        "practice_mode": "theory",
        "difficulty": challenge.difficulty,
        "source_id": challenge.source_id,
        "source_exercise_id": (
            challenge.source_exercise_id
        ),
        "mastery_signals": (
            challenge.mastery_signals
        ),
        "challenge_id": challenge.challenge_id,
        "challenge_type": challenge.challenge_type,
        "deterministic_validation": True,
    }

    database.record_practice_mastery_evidence(
        learner_id=request.learner_id,
        skill_name=challenge.skill_name,
        assistance_level="NONE",
        success=validation.success,
        evidence_type="explanation",
        note=(
            "Practice theory check deterministic "
            f"validation: {'success' if validation.success else 'failure'}."
        ),
        context=context,
    )

    mastery = calculate_practice_mastery(
        learner_id=request.learner_id,
        topic_id="python",
        subtopic_id=challenge.subtopic_id,
        practice_mode="theory",
        difficulty=challenge.difficulty,
    )

    explanation = (
        record.expected_outcome or ""
    ).strip()

    if validation.success:
        feedback = (
            "Correct."
            + (
                f" {explanation}"
                if explanation
                else ""
            )
        )
    else:
        expected = (
            record.validation_spec
            .expected_answer
            if record.validation_spec
            is not None
            else None
        )

        feedback = "Not quite."

        if expected:
            feedback += (
                f" Correct answer: {expected}."
            )

        if explanation:
            feedback += (
                f" {explanation}"
            )

    return PracticeTheoryAnswerResponse(
        learner_id=request.learner_id,
        challenge_id=request.challenge_id,
        concept_id=(
            challenge.source_exercise_id
        ),
        success=validation.success,
        feedback=feedback,
        mastery=mastery,
    )
