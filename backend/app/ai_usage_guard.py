import json
import os
from types import SimpleNamespace
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
    breakdown = (
        database.get_ai_usage_breakdown_today()
    )

    current_provider = os.getenv(
        "AI_MENTOR_PROVIDER",
        "openai",
    ).strip() or "openai"

    current_model = os.getenv(
        "AI_MENTOR_MODEL",
        "gpt-5-mini",
    ).strip() or "gpt-5-mini"

    normalized_provider = current_provider.casefold()
    if normalized_provider == "ollama":
        current_model = os.getenv("AI_OLLAMA_MODEL", "qwen3:4b").strip() or "qwen3:4b"
    elif normalized_provider == "groq":
        current_model = os.getenv("AI_GROQ_MENTOR_MODEL", "openai/gpt-oss-120b").strip() or "openai/gpt-oss-120b"
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
        # Character-based estimate for observability only. It is not provider
        # billing/quota truth because tokenization differs by model/content.
        "estimated_daily_input_tokens":
            round(
                usage["daily_input_chars"]
                / 4
            ),
        "estimated_monthly_input_tokens":
            round(
                usage["monthly_input_chars"]
                / 4
            ),
        "today_by_model_purpose": [
            {
                **item,
                "estimated_input_tokens":
                    round(
                        item["input_chars"]
                        / 4
                    ),
                "estimated_max_input_tokens":
                    round(
                        item["max_input_chars"]
                        / 4
                    ),
            }
            for item in breakdown
        ],
        "token_estimate_method":
            "input_chars_divided_by_4",
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

    if provider.casefold() == "ollama":
        # No external billing/quota: local inference still respects the same
        # maximum input size and the explicit FREE_ONLY allowlist.
        return {**limits, "input_chars": input_chars, "local_inference": True}

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
    if provider.casefold() == "ollama":
        # Preserve the Responses API used across DataPilot. Local Ollama
        # supports this endpoint; never expose model reasoning in the UI.
        kwargs.setdefault("extra_body", {"think": False})
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

    if provider.casefold() == "ollama":
        # Ollama's OpenAI-compatible Responses API does not promise the
        # text.format schema field sent by the SDK's responses.parse().
        # Chat Completions DOES support JSON Schema / Pydantic parsing.
        # Adapt locally to DataPilot's existing .output_parsed interface,
        # without adding another Mentor/router or a second network request.
        response_format = kwargs.pop("text_format")
        instructions = kwargs.pop("instructions", "")
        model = kwargs.pop("model")
        source_input = kwargs.pop("input")
        max_tokens = kwargs.pop("max_output_tokens", None)
        kwargs.pop("reasoning", None)  # Local Qwen replies should not think aloud.
        if isinstance(source_input, str):
            messages = [{"role": "user", "content": source_input}]
        elif isinstance(source_input, list):
            messages = list(source_input)
        else:
            raise TypeError("Unsupported Ollama structured input type.")
        if instructions:
            messages.insert(0, {"role": "system", "content": instructions})
        allowed = {"temperature", "top_p"}
        if set(kwargs) - allowed:
            raise TypeError("Unsupported Ollama structured request options.")
        chat = client.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=response_format,
            max_tokens=max_tokens,
            extra_body={"think": False},
            **kwargs,
        )
        if not chat.choices or chat.choices[0].message.parsed is None:
            raise ValueError("Ollama did not return a valid structured response.")
        usage = getattr(chat, "usage", None)
        return SimpleNamespace(
            status="completed" if chat.choices[0].finish_reason == "stop" else "incomplete",
            output_parsed=chat.choices[0].message.parsed,
            usage=SimpleNamespace(
                input_tokens=getattr(usage, "prompt_tokens", None),
                output_tokens=getattr(usage, "completion_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
            ),
            incomplete_details=None,
        )

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

    if provider.casefold() == "ollama":
        kwargs.setdefault("extra_body", {"think": False})

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
