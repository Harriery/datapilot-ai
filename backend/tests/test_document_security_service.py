from backend.app.document_security_service import (
    evaluate_document_ai_policy,
)


def test_unknown_context_is_blocked():

    decision = evaluate_document_ai_policy(
        usage_context="unknown",
        data_sensitivity="public",
    )

    assert decision.external_ai_allowed is False
    assert decision.ai_processing_status == "blocked"
    assert decision.reason_code == "unknown_context"


def test_unknown_sensitivity_is_blocked():

    decision = evaluate_document_ai_policy(
        usage_context="personal",
        data_sensitivity="unknown",
    )

    assert decision.external_ai_allowed is False
    assert decision.ai_processing_status == "blocked"
    assert decision.reason_code == "unknown_sensitivity"


def test_confidential_document_is_blocked():

    decision = evaluate_document_ai_policy(
        usage_context="personal",
        data_sensitivity="confidential",
    )

    assert decision.external_ai_allowed is False
    assert decision.ai_processing_status == "blocked"
    assert decision.reason_code == (
        "sensitive_data_blocked"
    )


def test_restricted_document_is_blocked():

    decision = evaluate_document_ai_policy(
        usage_context="work",
        data_sensitivity="restricted",
        organization_id="company-001",
    )

    assert decision.external_ai_allowed is False
    assert decision.ai_processing_status == "blocked"


def test_work_document_requires_organization():

    decision = evaluate_document_ai_policy(
        usage_context="work",
        data_sensitivity="public",
    )

    assert decision.external_ai_allowed is False
    assert decision.reason_code == (
        "organization_required"
    )


def test_public_work_document_is_allowed():

    decision = evaluate_document_ai_policy(
        usage_context="work",
        data_sensitivity="public",
        organization_id="company-001",
    )

    assert decision.external_ai_allowed is True
    assert decision.ai_processing_status == "allowed"
    assert decision.reason_code == "allowed_public"


def test_internal_work_document_requires_policy():

    decision = evaluate_document_ai_policy(
        usage_context="work",
        data_sensitivity="internal",
        organization_id="company-001",
    )

    assert decision.external_ai_allowed is False
    assert decision.ai_processing_status == "pending"
    assert decision.reason_code == (
        "organization_policy_required"
    )


def test_internal_work_document_can_be_blocked_by_policy():

    decision = evaluate_document_ai_policy(
        usage_context="work",
        data_sensitivity="internal",
        organization_id="company-001",
        organization_ai_allowed=False,
    )

    assert decision.external_ai_allowed is False
    assert decision.ai_processing_status == "blocked"
    assert decision.reason_code == (
        "organization_policy_blocked"
    )


def test_internal_work_document_can_be_allowed_by_policy():

    decision = evaluate_document_ai_policy(
        usage_context="work",
        data_sensitivity="internal",
        organization_id="company-001",
        organization_ai_allowed=True,
    )

    assert decision.external_ai_allowed is True
    assert decision.ai_processing_status == "allowed"
    assert decision.reason_code == (
        "allowed_organization_internal"
    )


def test_personal_public_document_is_allowed():

    decision = evaluate_document_ai_policy(
        usage_context="personal",
        data_sensitivity="public",
    )

    assert decision.external_ai_allowed is True
    assert decision.ai_processing_status == "allowed"


def test_personal_internal_document_is_allowed():

    decision = evaluate_document_ai_policy(
        usage_context="personal",
        data_sensitivity="internal",
    )

    assert decision.external_ai_allowed is True
    assert decision.ai_processing_status == "allowed"
    assert decision.reason_code == (
        "allowed_personal_internal"
    )