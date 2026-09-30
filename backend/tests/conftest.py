import pytest


@pytest.fixture(autouse=True)
def disable_external_billing_policy_for_mocked_tests(
    monkeypatch,
    request,
):
    """
    Most AI tests mock the provider client and verify application logic.
    They should not be blocked by the production FREE_ONLY policy.

    test_ai_usage_guard.py explicitly tests the real policy and sets its
    own environment values, so leave that module untouched.
    """
    if request.module.__name__.endswith(
        "test_ai_usage_guard"
    ):
        return

    monkeypatch.setenv(
        "AI_FREE_ONLY",
        "false",
    )
