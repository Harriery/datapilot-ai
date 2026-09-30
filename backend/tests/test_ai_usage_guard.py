from unittest.mock import MagicMock

import pytest

import backend.app.database as database
from backend.app.ai_usage_guard import (
    AIUsageLimitError,
    get_ai_usage_status,
    guarded_responses_create,
)


@pytest.fixture(autouse=True)
def setup_test_database(tmp_path, monkeypatch):
    database.DATABASE_PATH = tmp_path / "test.db"
    database.init_db()
    monkeypatch.setenv("AI_DAILY_REQUEST_LIMIT", "2")
    monkeypatch.setenv("AI_MONTHLY_REQUEST_LIMIT", "3")
    monkeypatch.setenv("AI_MAX_INPUT_CHARS_PER_REQUEST", "1000")
    monkeypatch.setenv("AI_MAX_OUTPUT_TOKENS_PER_REQUEST", "321")


def test_guard_counts_usage_and_caps_output():
    client = MagicMock()
    client.responses.create.return_value = "ok"

    result = guarded_responses_create(
        client,
        purpose="mentor",
        model="test-model",
        input="hello",
    )

    assert result == "ok"
    assert client.responses.create.call_args.kwargs["max_output_tokens"] == 321
    status = get_ai_usage_status()
    assert status["daily_requests"] == 1
    assert status["daily_remaining"] == 1


def test_guard_blocks_before_third_provider_call():
    client = MagicMock()

    for _ in range(2):
        guarded_responses_create(
            client,
            purpose="mentor",
            model="test-model",
            input="hello",
        )

    with pytest.raises(AIUsageLimitError):
        guarded_responses_create(
            client,
            purpose="mentor",
            model="test-model",
            input="third",
        )

    assert client.responses.create.call_count == 2


def test_guard_blocks_oversized_input_without_counting_request():
    client = MagicMock()

    with pytest.raises(AIUsageLimitError):
        guarded_responses_create(
            client,
            purpose="mentor",
            model="test-model",
            input="x" * 1001,
        )

    client.responses.create.assert_not_called()
    assert get_ai_usage_status()["daily_requests"] == 0
