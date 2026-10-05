from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from openai import OpenAI

from backend.app.ai_usage_guard import (
    get_ai_billing_policy,
)


AIRole = Literal[
    "mentor",
    "classifier",
    "translator",
    "practice_generator",
]


class AIProviderConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class AIRuntimeConfig:
    provider: str
    model: str


@dataclass(frozen=True)
class AIRuntime:
    provider: str
    model: str
    client: OpenAI


def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise AIProviderConfigurationError(
            f"{name} is required for the selected AI provider."
        )

    return value


def _configured_provider(
    role: AIRole,
) -> str:
    if role == "classifier":
        value = os.getenv(
            "AI_CLASSIFIER_PROVIDER",
            os.getenv(
                "AI_MENTOR_PROVIDER",
                "groq",
            ),
        )
    elif role in {
        "translator",
        "practice_generator",
    }:
        env_name = (
            "AI_TRANSLATOR_PROVIDER"
            if role == "translator"
            else "AI_PRACTICE_GENERATOR_PROVIDER"
        )
        value = os.getenv(
            env_name,
            os.getenv(
                "AI_CLASSIFIER_PROVIDER",
                os.getenv(
                    "AI_MENTOR_PROVIDER",
                    "groq",
                ),
            ),
        )
    else:
        value = os.getenv(
            "AI_MENTOR_PROVIDER",
            "groq",
        )

    return value.strip().casefold() or "groq"


def _configured_model(
    *,
    provider: str,
    role: AIRole,
) -> str:
    if provider == "groq":
        if role == "classifier":
            return (
                os.getenv(
                    "AI_GROQ_CLASSIFIER_MODEL",
                    "openai/gpt-oss-20b",
                ).strip()
                or "openai/gpt-oss-20b"
            )

        if role in {
            "translator",
            "practice_generator",
        }:
            env_name = (
                "AI_GROQ_TRANSLATOR_MODEL"
                if role == "translator"
                else "AI_GROQ_PRACTICE_GENERATOR_MODEL"
            )
            return (
                os.getenv(
                    env_name,
                    os.getenv(
                        "AI_GROQ_CLASSIFIER_MODEL",
                        "openai/gpt-oss-20b",
                    ),
                ).strip()
                or "openai/gpt-oss-20b"
            )

        return (
            os.getenv(
                "AI_GROQ_MENTOR_MODEL",
                "openai/gpt-oss-120b",
            ).strip()
            or "openai/gpt-oss-120b"
        )

    if role == "classifier":
        return (
            os.getenv(
                "AI_CLASSIFIER_MODEL",
                os.getenv(
                    "AI_MENTOR_MODEL",
                    "gpt-5-mini",
                ),
            ).strip()
            or "gpt-5-mini"
        )

    return (
        os.getenv(
            "AI_MENTOR_MODEL",
            "gpt-5-mini",
        ).strip()
        or "gpt-5-mini"
    )


def _provider_has_credentials(
    provider: str,
) -> bool:
    if provider == "groq":
        return bool(
            os.getenv(
                "GROQ_API_KEY",
                "",
            ).strip()
        )

    if provider == "openai":
        return bool(
            os.getenv(
                "OPENAI_API_KEY",
                "",
            ).strip()
        )

    return False


def _resolve_provider(
    role: AIRole,
) -> str:
    configured = _configured_provider(
        role
    )

    policy = get_ai_billing_policy()

    if not policy["free_only"]:
        return configured

    allowed = set(
        policy[
            "allowed_free_providers"
        ]
    )

    if configured in allowed:
        return configured

    # FREE_ONLY may reject the configured paid baseline.
    # A credentialed provider from the explicit free-provider
    # allowlist can be selected without opening a paid fallback.
    for candidate in (
        "groq",
    ):
        if (
            candidate in allowed
            and _provider_has_credentials(
                candidate
            )
        ):
            return candidate

    raise AIProviderConfigurationError(
        "No usable FREE_ONLY AI provider is configured. "
        "Set AI_MENTOR_PROVIDER to an allowed provider and "
        "provide its API key. Paid OpenAI fallback remains disabled."
    )


def get_ai_runtime_config(
    role: AIRole = "mentor",
) -> AIRuntimeConfig:
    provider = _resolve_provider(
        role
    )
    model = _configured_model(
        provider=provider,
        role=role,
    )
    return AIRuntimeConfig(
        provider=provider,
        model=model,
    )


def get_ai_runtime(
    role: AIRole = "mentor",
) -> AIRuntime:
    runtime_config = get_ai_runtime_config(
        role
    )
    provider = runtime_config.provider
    model = runtime_config.model

    if provider == "groq":
        return AIRuntime(
            provider="groq",
            model=model,
            client=OpenAI(
                api_key=_get_required_env(
                    "GROQ_API_KEY"
                ),
                base_url=(
                    "https://api.groq.com/openai/v1"
                ),
            ),
        )

    if provider == "openai":
        return AIRuntime(
            provider="openai",
            model=model,
            client=OpenAI(
                api_key=_get_required_env(
                    "OPENAI_API_KEY"
                ),
            ),
        )

    raise AIProviderConfigurationError(
        f"AI provider '{provider}' is allowed by policy but "
        "does not have a runtime adapter yet."
    )
