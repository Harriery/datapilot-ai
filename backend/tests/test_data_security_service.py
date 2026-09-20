from backend.app.data_security_service import (
    evaluate_external_ai_policy,
)

from backend.app.models import (
    ExternalAIProcessingDecision,
    DocumentSecurityDecision,
)

def test_confidential_work_data_is_blocked():

    decision = evaluate_external_ai_policy(
        usage_context="work",
        data_sensitivity="confidential",
        organization_id="company-001",
    )

    assert decision.external_ai_allowed is False

    assert (
        decision.ai_processing_status
        == "blocked"
    )

    assert (
        decision.reason_code
        == "sensitive_data_blocked"
    )

def test_security_decision_uses_generic_model():

    decision = evaluate_external_ai_policy(
        usage_context="personal",
        data_sensitivity="public",
    )

    assert isinstance(
        decision,
        ExternalAIProcessingDecision,
    )

    # Eski isim de compatibility için
    # aynı modeli göstermeye devam etmeli.
    assert isinstance(
        decision,
        DocumentSecurityDecision,
    )