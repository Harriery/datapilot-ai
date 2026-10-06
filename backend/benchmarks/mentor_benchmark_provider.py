from __future__ import annotations

import os
import re
from time import sleep
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.app.ai_provider_service import (
    AIProviderConfigurationError,
)
from backend.app.ai_usage_guard import (
    get_ai_usage_limits,
    guarded_responses_parse,
    reserve_ai_request,
)


load_dotenv()


StructuredModel = TypeVar(
    "StructuredModel",
    bound=BaseModel,
)


def _is_structured_output_failure(
    exc: Exception,
) -> bool:
    if getattr(exc, "status_code", None) != 400:
        return False

    supported_codes = {
        "output_parse_failed",
        "json_validate_failed",
    }

    body = getattr(exc, "body", None)

    if isinstance(body, dict):
        error = body.get("error", body)
        if isinstance(error, dict):
            return error.get("code") in supported_codes

    message = str(exc)
    return any(
        code in message
        for code in supported_codes
    )


def _is_transient_rate_limit(
    exc: Exception,
) -> bool:
    if getattr(exc, "status_code", None) != 429:
        return False

    message = str(exc).casefold()

    return (
        "rate_limit_exceeded" in message
        or "rate limit reached" in message
    )


def _rate_limit_retry_seconds(
    exc: Exception,
) -> float:
    message = str(exc)

    match = re.search(
        r"try again in\s+([0-9]+(?:\.[0-9]+)?)s",
        message,
        flags=re.IGNORECASE,
    )

    if match is None:
        return 2.0

    return min(
        max(
            float(match.group(1)) + 0.25,
            0.5,
        ),
        5.0,
    )


def _required_env(
    name: str,
) -> str:
    value = os.getenv(
        name,
        "",
    ).strip()

    if not value:
        raise AIProviderConfigurationError(
            f"{name} is required for benchmark provider."
        )

    return value


def _openai_compatible_client(
    provider: str,
) -> OpenAI:
    if provider == "groq":
        return OpenAI(
            api_key=_required_env(
                "GROQ_API_KEY"
            ),
            base_url=(
                "https://api.groq.com/openai/v1"
            ),
        )

    if provider == "openai":
        return OpenAI(
            api_key=_required_env(
                "OPENAI_API_KEY"
            ),
        )

    raise AIProviderConfigurationError(
        f"Provider '{provider}' is not supported by the OpenAI-compatible adapter."
    )


def _generate_openai_compatible_structured(
    *,
    provider: str,
    model: str,
    purpose: str,
    instructions: str,
    input_text: str,
    text_format: type[StructuredModel],
    request_kwargs: dict | None = None,
) -> StructuredModel:
    client = _openai_compatible_client(
        provider
    )

    request_kwargs = request_kwargs or {}

    try:
        response = guarded_responses_parse(
            client,
            provider=provider,
            purpose=purpose,
            model=model,
            instructions=instructions,
            input=input_text,
            text_format=text_format,
            **request_kwargs,
        )
    except Exception as exc:
        if (
            provider == "groq"
            and _is_transient_rate_limit(exc)
        ):
            sleep(
                _rate_limit_retry_seconds(exc)
            )

            response = guarded_responses_parse(
                client,
                provider=provider,
                purpose=purpose + "_rate_limit_retry",
                model=model,
                instructions=instructions,
                input=input_text,
                text_format=text_format,
                **request_kwargs,
            )
        elif (
            provider == "groq"
            and _is_structured_output_failure(exc)
        ):
            retry_instructions = (
                instructions
                + "\n\nSTRICT STRUCTURED OUTPUT RETRY:\n"
                + "- Return only the structured JSON required by the schema.\n"
                + "- Do not include analysis, reasoning, commentary, markdown, "
                  "or text before/after the JSON.\n"
                + "- Populate every required field."
            )

            response = guarded_responses_parse(
                client,
                provider=provider,
                purpose=purpose + "_parse_retry",
                model=model,
                instructions=retry_instructions,
                input=input_text,
                text_format=text_format,
                **request_kwargs,
            )
        else:
            raise

    return response.output_parsed


def _generate_gemini_structured(
    *,
    model: str,
    purpose: str,
    instructions: str,
    input_text: str,
    text_format: type[StructuredModel],
) -> StructuredModel:
    try:
        from google import genai
    except ImportError as exc:
        raise AIProviderConfigurationError(
            "Gemini benchmark support requires the google-genai package."
        ) from exc

    api_key = _required_env(
        "GEMINI_API_KEY"
    )

    limits = get_ai_usage_limits()

    reserve_ai_request(
        provider="google",
        model=model,
        purpose=purpose,
        input_value={
            "instructions":
                instructions,
            "input":
                input_text,
        },
    )

    client = genai.Client(
        api_key=api_key
    )

    interaction = (
        client.interactions.create(
            model=model,
            input=input_text,
            system_instruction=(
                instructions
            ),
            store=False,
            response_format={
                "type":
                    "text",
                "mime_type":
                    "application/json",
                "schema":
                    text_format
                    .model_json_schema(),
            },
            generation_config={
                "max_output_tokens":
                    limits[
                        "max_output_tokens_per_request"
                    ],
            },
        )
    )

    output_text = getattr(
        interaction,
        "output_text",
        None,
    )

    if (
        not isinstance(
            output_text,
            str,
        )
        or not output_text.strip()
    ):
        raise AIProviderConfigurationError(
            "Gemini benchmark response did not contain structured output text."
        )

    return text_format.model_validate_json(
        output_text
    )


def generate_benchmark_structured(
    *,
    provider: str,
    model: str,
    purpose: str,
    instructions: str,
    input_text: str,
    text_format: type[StructuredModel],
    request_kwargs: dict | None = None,
) -> StructuredModel:
    normalized_provider = (
        provider.strip().casefold()
    )

    if normalized_provider in {
        "groq",
        "openai",
    }:
        return (
            _generate_openai_compatible_structured(
                provider=(
                    normalized_provider
                ),
                model=model,
                purpose=purpose,
                instructions=instructions,
                input_text=input_text,
                text_format=text_format,
                request_kwargs=request_kwargs,
            )
        )

    if normalized_provider in {
        "google",
        "gemini",
    }:
        return (
            _generate_gemini_structured(
                model=model,
                purpose=purpose,
                instructions=instructions,
                input_text=input_text,
                text_format=text_format,
            )
        )

    raise AIProviderConfigurationError(
        "Unsupported benchmark provider: "
        f"{provider}. Supported providers are groq, google, and openai."
    )
