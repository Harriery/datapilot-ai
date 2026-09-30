import json
import os
from typing import Any

import backend.app.database as database


class AIUsageLimitError(RuntimeError):
    pass


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    value = int(raw)
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")
    return value


def get_ai_usage_limits() -> dict:
    return {
        "daily_request_limit": _env_int("AI_DAILY_REQUEST_LIMIT", 120),
        "monthly_request_limit": _env_int("AI_MONTHLY_REQUEST_LIMIT", 1500),
        "max_input_chars_per_request": _env_int("AI_MAX_INPUT_CHARS_PER_REQUEST", 200000),
        "max_output_tokens_per_request": _env_int("AI_MAX_OUTPUT_TOKENS_PER_REQUEST", 1500),
    }


def _input_chars(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return len(value)
    return len(json.dumps(value, ensure_ascii=False, default=str))


def get_ai_usage_status() -> dict:
    limits = get_ai_usage_limits()
    usage = database.get_ai_usage_counts()
    return {
        **usage,
        **limits,
        "daily_remaining": max(limits["daily_request_limit"] - usage["daily_requests"], 0),
        "monthly_remaining": max(limits["monthly_request_limit"] - usage["monthly_requests"], 0),
    }


def reserve_ai_request(*, provider: str, model: str, purpose: str, input_value: Any) -> dict:
    limits = get_ai_usage_limits()
    input_chars = _input_chars(input_value)
    if input_chars > limits["max_input_chars_per_request"]:
        raise AIUsageLimitError(
            "AI request blocked locally: input is larger than AI_MAX_INPUT_CHARS_PER_REQUEST."
        )

    try:
        usage = database.reserve_ai_usage_event(
            provider=provider,
            model=model,
            purpose=purpose,
            input_chars=input_chars,
            daily_limit=limits["daily_request_limit"],
            monthly_limit=limits["monthly_request_limit"],
        )
    except RuntimeError as exc:
        raise AIUsageLimitError(str(exc)) from exc

    return {**usage, **limits, "input_chars": input_chars}


def guarded_responses_create(client, *, provider: str = "openai", purpose: str, **kwargs):
    reserve_ai_request(
        provider=provider,
        model=str(kwargs.get("model", "unknown")),
        purpose=purpose,
        input_value={"instructions": kwargs.get("instructions"), "input": kwargs.get("input")},
    )
    max_output_tokens = get_ai_usage_limits()["max_output_tokens_per_request"]
    if max_output_tokens > 0 and "max_output_tokens" not in kwargs:
        kwargs["max_output_tokens"] = max_output_tokens
    return client.responses.create(**kwargs)


def guarded_responses_parse(client, *, provider: str = "openai", purpose: str, **kwargs):
    reserve_ai_request(
        provider=provider,
        model=str(kwargs.get("model", "unknown")),
        purpose=purpose,
        input_value={"instructions": kwargs.get("instructions"), "input": kwargs.get("input")},
    )
    max_output_tokens = get_ai_usage_limits()["max_output_tokens_per_request"]
    if max_output_tokens > 0 and "max_output_tokens" not in kwargs:
        kwargs["max_output_tokens"] = max_output_tokens
    return client.responses.parse(**kwargs)


def guarded_embeddings_create(client, *, provider: str = "openai", purpose: str = "embedding", **kwargs):
    reserve_ai_request(
        provider=provider,
        model=str(kwargs.get("model", "unknown")),
        purpose=purpose,
        input_value=kwargs.get("input"),
    )
    return client.embeddings.create(**kwargs)
