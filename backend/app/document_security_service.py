from backend.app.data_security_service import (
    evaluate_external_ai_policy,
)


def evaluate_document_ai_policy(
    usage_context: str,
    data_sensitivity: str,
    organization_id: str | None = None,
    organization_ai_allowed: bool | None = None,
):
    """
    Backward-compatible wrapper.

    Yeni kod generic evaluate_external_ai_policy()
    kullanmalıdır.
    """
    return evaluate_external_ai_policy(
        usage_context=usage_context,
        data_sensitivity=data_sensitivity,
        organization_id=organization_id,
        organization_ai_allowed=(
            organization_ai_allowed
        ),
    )