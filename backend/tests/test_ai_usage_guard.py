from unittest.mock import MagicMock

import pytest

import backend.app.database as database
from backend.app.ai_usage_guard import (
    AIBillingPolicyError,
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
    monkeypatch.setenv("AI_FREE_ONLY", "true")
    monkeypatch.setenv("AI_FREE_PROVIDER_ALLOWLIST", "test-free")
    monkeypatch.setenv("AI_ALLOW_PAID_PROVIDER", "false")


def test_guard_counts_usage_and_caps_output():
    client = MagicMock()
    client.responses.create.return_value = "ok"

    result = guarded_responses_create(
        client,
        provider="test-free",
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
            provider="test-free",
            purpose="mentor",
            model="test-model",
            input="hello",
        )

    with pytest.raises(AIUsageLimitError):
        guarded_responses_create(
            client,
            provider="test-free",
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
            provider="test-free",
            purpose="mentor",
            model="test-model",
            input="x" * 1001,
        )

    client.responses.create.assert_not_called()
    assert get_ai_usage_status()["daily_requests"] == 0



def test_free_only_blocks_provider_not_in_allowlist():
    client = MagicMock()

    with pytest.raises(AIBillingPolicyError):
        guarded_responses_create(
            client,
            provider="openai",
            purpose="mentor",
            model="test-model",
            input="hello",
        )

    client.responses.create.assert_not_called()


def test_usage_status_exposes_free_only_policy():
    status = get_ai_usage_status()

    assert status["free_only"] is True
    assert status["allow_paid_provider"] is False
    assert status["allowed_free_providers"] == ["test-free"]



def test_usage_status_marks_unconfigured_current_provider_as_blocked(
    monkeypatch,
):
    monkeypatch.setenv(
        "AI_MENTOR_PROVIDER",
        "openai",
    )

    status = get_ai_usage_status()

    assert status["current_provider_allowed"] is False
    assert status["usage_scope"] == "local_safety_budget"
    assert status["provider_quota_known"] is False



def test_usage_status_reports_input_size_and_breakdown():
    client = MagicMock()
    client.responses.create.return_value = "ok"

    guarded_responses_create(
        client,
        provider="test-free",
        purpose="mentor_learning_phase",
        model="small-model",
        input="abcd" * 10,
    )
    guarded_responses_create(
        client,
        provider="test-free",
        purpose="mentor_learning_reply",
        model="small-model",
        input="xy" * 10,
    )

    status = get_ai_usage_status()

    assert status["daily_requests"] == 2
    assert status["daily_input_chars"] > 0
    assert status["estimated_daily_input_tokens"] > 0
    assert (
        status["token_estimate_method"]
        == "input_chars_divided_by_4"
    )

    breakdown = status["today_by_model_purpose"]
    assert len(breakdown) == 2
    assert {
        item["purpose"]
        for item in breakdown
    } == {
        "mentor_learning_phase",
        "mentor_learning_reply",
    }
    assert all(
        item["model"] == "small-model"
        for item in breakdown
    )
    assert all(
        item["estimated_input_tokens"] > 0
        for item in breakdown
    )


def test_usage_breakdown_does_not_store_prompt_content():
    client = MagicMock()
    client.responses.create.return_value = "ok"

    secret_text = "do-not-expose-this-prompt"
    guarded_responses_create(
        client,
        provider="test-free",
        purpose="mentor",
        model="test-model",
        input=secret_text,
    )

    status = get_ai_usage_status()
    serialized = __import__("json").dumps(
        status,
        ensure_ascii=False,
    )

    assert secret_text not in serialized
