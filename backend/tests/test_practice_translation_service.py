from types import SimpleNamespace

from backend.app.ai_provider_service import (
    AIRuntime,
)
from backend.app.models import (
    PracticeTranslationRequest,
)
from backend.app.practice_source_cache_service import (
    PRACTICE_SOURCE_CACHE,
)
from backend.app.practice_translation_service import (
    translate_practice_instructions,
)


class FakeChatCompletions:
    def __init__(self):
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1

        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            "Görevin, verilen bir yılın "
                            "leap year (artık yıl) olup "
                            "olmadığını belirlemektir."
                        )
                    )
                )
            ]
        )


class FakeChat:
    def __init__(self):
        self.completions = (
            FakeChatCompletions()
        )


class FakeClient:
    def __init__(self):
        self.chat = FakeChat()


def _request():
    return PracticeTranslationRequest(
        learner_id="learner-001",
        source_id="exercism-python",
        source_exercise_id="leap",
        content_hash="hash-123",
        target_language="tr",
        source_text=(
            "Your task is to determine whether a "
            "given year is a leap year."
        ),
    )


def test_practice_translation_uses_free_runtime_and_returns_text(
    monkeypatch,
):
    PRACTICE_SOURCE_CACHE.clear()
    client = FakeClient()

    monkeypatch.setattr(
        "backend.app.practice_translation_service."
        "guarded_chat_completions_create",
        lambda client_arg, **kwargs: (
            client.chat.completions.create(
                **kwargs
            )
        ),
    )

    result = translate_practice_instructions(
        request=_request(),
        runtime_loader=lambda: AIRuntime(
            provider="groq",
            model="openai/gpt-oss-20b",
            client=client,
        ),
    )

    assert result.provider == "groq"
    assert result.model == "openai/gpt-oss-20b"
    assert "leap year" in result.translated_text
    assert result.cached is False
    assert client.chat.completions.calls == 1


def test_practice_translation_is_cached_by_content_hash_and_language(
    monkeypatch,
):
    PRACTICE_SOURCE_CACHE.clear()
    client = FakeClient()

    monkeypatch.setattr(
        "backend.app.practice_translation_service."
        "guarded_responses_create",
        lambda client_arg, **kwargs: (
            client.responses.create(**kwargs)
        ),
    )

    first = translate_practice_instructions(
        request=_request(),
        runtime_loader=lambda: AIRuntime(
            provider="groq",
            model="openai/gpt-oss-20b",
            client=client,
        ),
    )

    second = translate_practice_instructions(
        request=_request().model_copy(
            update={
                "learner_id": "learner-002",
            }
        ),
        runtime_loader=lambda: AIRuntime(
            provider="groq",
            model="openai/gpt-oss-20b",
            client=client,
        ),
    )

    assert first.cached is False
    assert second.cached is True
    assert second.learner_id == "learner-002"
    assert client.chat.completions.calls == 1


def test_practice_translation_cache_changes_when_content_hash_changes(
    monkeypatch,
):
    PRACTICE_SOURCE_CACHE.clear()
    client = FakeClient()

    monkeypatch.setattr(
        "backend.app.practice_translation_service."
        "guarded_responses_create",
        lambda client_arg, **kwargs: (
            client.responses.create(**kwargs)
        ),
    )

    translate_practice_instructions(
        request=_request(),
        runtime_loader=lambda: AIRuntime(
            provider="groq",
            model="openai/gpt-oss-20b",
            client=client,
        ),
    )

    translate_practice_instructions(
        request=_request().model_copy(
            update={
                "content_hash": "hash-456",
            }
        ),
        runtime_loader=lambda: AIRuntime(
            provider="groq",
            model="openai/gpt-oss-20b",
            client=client,
        ),
    )

    assert client.chat.completions.calls == 2
