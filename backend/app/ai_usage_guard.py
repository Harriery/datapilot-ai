import json
import os
from typing import Any

import backend.app.database as database


class AIUsageLimitError(RuntimeError):
    pass


class AIBillingPolicyError(RuntimeError):
    pass


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().casefold() in {
        "1", "true", "yes", "on"
    }


def _env_csv(name: str) -> set[str]:
    raw = os.getenv(name, "")
    return {
        item.strip().casefold()
        for item in raw.split(",")
        if item.strip()
    }


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    value = int(raw)
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")
    return value


def get_ai_billing_policy() -> dict:
    free_only = _env_bool(
        "AI_FREE_ONLY",
        True,
    )
    allowed_free_providers = _env_csv(
        "AI_FREE_PROVIDER_ALLOWLIST"
    )
    allow_paid_provider = _env_bool(
        "AI_ALLOW_PAID_PROVIDER",
        False,
    )

    return {
        "free_only": free_only,
        "allowed_free_providers":
            sorted(allowed_free_providers),
        "allow_paid_provider":
            allow_paid_provider,
    }


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
    billing_policy = get_ai_billing_policy()
    usage = database.get_ai_usage_counts()

    current_provider = os.getenv(
        "AI_MENTOR_PROVIDER",
        "openai",
    ).strip() or "openai"

    current_model = os.getenv(
        "AI_MENTOR_MODEL",
        "gpt-5-mini",
    ).strip() or "gpt-5-mini"

    normalized_provider = current_provider.casefold()
    allowed_free_providers = set(
        billing_policy["allowed_free_providers"]
    )

    current_provider_allowed = (
        not billing_policy["free_only"]
        or normalized_provider in allowed_free_providers
        or (
            billing_policy["allow_paid_provider"]
            and normalized_provider == "openai"
        )
    )

    return {
        **billing_policy,
        "current_provider": current_provider,
        "current_model": current_model,
        "current_provider_allowed":
            current_provider_allowed,
        "usage_scope": "local_safety_budget",
        "provider_quota_known": False,
        **usage,
        **limits,
        "daily_remaining": max(limits["daily_request_limit"] - usage["daily_requests"], 0),
        "monthly_remaining": max(limits["monthly_request_limit"] - usage["monthly_requests"], 0),
    }


def _enforce_billing_policy(
    *,
    provider: str,
) -> None:
    policy = get_ai_billing_policy()
    normalized_provider = provider.casefold()

    if not policy["free_only"]:
        return

    if (
        policy["allow_paid_provider"]
        and normalized_provider == "openai"
    ):
        return

    if (
        normalized_provider
        not in set(policy["allowed_free_providers"])
    ):
        raise AIBillingPolicyError(
            "AI request blocked locally by FREE_ONLY policy. "
            f"Provider '{provider}' is not in the free-provider allowlist."
        )


def reserve_ai_request(*, provider: str, model: str, purpose: str, input_value: Any) -> dict:
    _enforce_billing_policy(
        provider=provider,
    )

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


def guarded_chat_completions_create(
    client,
    *,
    provider: str = "openai",
    purpose: str,
    **kwargs,
):
    reserve_ai_request(
        provider=provider,
        model=str(
            kwargs.get(
                "model",
                "unknown",
            )
        ),
        purpose=purpose,
        input_value=kwargs.get(
            "messages"
        ),
    )

    max_output_tokens = (
        get_ai_usage_limits()[
            "max_output_tokens_per_request"
        ]
    )

    if max_output_tokens > 0:
        if "max_completion_tokens" in kwargs:
            kwargs["max_completion_tokens"] = min(
                int(kwargs["max_completion_tokens"]),
                max_output_tokens,
            )
        elif "max_tokens" in kwargs:
            kwargs["max_tokens"] = min(
                int(kwargs["max_tokens"]),
                max_output_tokens,
            )
        else:
            kwargs["max_completion_tokens"] = (
                max_output_tokens
            )

    return (
        client.chat.completions.create(
            **kwargs
        )
    )


def guarded_embeddings_create(client, *, provider: str = "openai", purpose: str = "embedding", **kwargs):
    reserve_ai_request(
        provider=provider,
        model=str(kwargs.get("model", "unknown")),
        purpose=purpose,
        input_value=kwargs.get("input"),
    )
    return client.embeddings.create(**kwargs)
