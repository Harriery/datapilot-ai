import os

from backend.app.ai_provider_service import (
    get_ai_runtime_config,
)


def _configure_free_groq(monkeypatch):
    monkeypatch.setenv("AI_FREE_ONLY", "true")
    monkeypatch.setenv(
        "AI_FREE_PROVIDER_ALLOWLIST",
        "groq",
    )
    monkeypatch.setenv(
        "AI_ALLOW_PAID_PROVIDER",
        "false",
    )
    monkeypatch.setenv(
        "AI_MENTOR_PROVIDER",
        "groq",
    )
    monkeypatch.setenv(
        "AI_CLASSIFIER_PROVIDER",
        "groq",
    )


def test_groq_classifier_defaults_to_120b(monkeypatch):
    _configure_free_groq(monkeypatch)
    monkeypatch.delenv(
        "AI_GROQ_CLASSIFIER_MODEL",
        raising=False,
    )

    runtime = get_ai_runtime_config(
        "classifier"
    )

    assert runtime.provider == "groq"
    assert (
        runtime.model
        == "openai/gpt-oss-120b"
    )


def test_groq_translator_default_stays_20b(monkeypatch):
    _configure_free_groq(monkeypatch)
    monkeypatch.delenv(
        "AI_GROQ_TRANSLATOR_MODEL",
        raising=False,
    )
    monkeypatch.setenv(
        "AI_GROQ_CLASSIFIER_MODEL",
        "openai/gpt-oss-120b",
    )

    runtime = get_ai_runtime_config(
        "translator"
    )

    assert runtime.model == "openai/gpt-oss-20b"


def test_groq_practice_generator_default_stays_20b(monkeypatch):
    _configure_free_groq(monkeypatch)
    monkeypatch.delenv(
        "AI_GROQ_PRACTICE_GENERATOR_MODEL",
        raising=False,
    )
    monkeypatch.setenv(
        "AI_GROQ_CLASSIFIER_MODEL",
        "openai/gpt-oss-120b",
    )

    runtime = get_ai_runtime_config(
        "practice_generator"
    )

    assert runtime.model == "openai/gpt-oss-20b"



def test_groq_guided_learning_defaults_to_20b(monkeypatch):
    _configure_free_groq(monkeypatch)
    monkeypatch.delenv(
        "AI_GROQ_GUIDED_EVALUATOR_MODEL",
        raising=False,
    )
    monkeypatch.delenv(
        "AI_GROQ_GUIDED_TUTOR_MODEL",
        raising=False,
    )

    evaluator = get_ai_runtime_config(
        "guided_evaluator"
    )
    tutor = get_ai_runtime_config(
        "guided_tutor"
    )

    assert evaluator.provider == "groq"
    assert evaluator.model == "openai/gpt-oss-20b"
    assert tutor.provider == "groq"
    assert tutor.model == "openai/gpt-oss-20b"
