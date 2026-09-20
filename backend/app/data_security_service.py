from backend.app.models import (
    ExternalAIProcessingDecision,
)


def evaluate_external_ai_policy(
    usage_context: str,
    data_sensitivity: str,
    organization_id: str | None = None,
    organization_ai_allowed: bool | None = None,
) -> ExternalAIProcessingDecision:

    # Unknown context -> default deny.
    if usage_context not in {
        "personal",
        "work",
    }:
        return ExternalAIProcessingDecision(
            ai_processing_status="blocked",
            external_ai_allowed=False,
            reason_code="unknown_context",
            reason=(
                "Data usage context is unknown. "
                "External AI processing is blocked."
            ),
        )

    # Unknown sensitivity -> default deny.
    if data_sensitivity == "unknown":
        return ExternalAIProcessingDecision(
            ai_processing_status="blocked",
            external_ai_allowed=False,
            reason_code="unknown_sensitivity",
            reason=(
                "Data sensitivity is unknown. "
                "External AI processing is blocked."
            ),
        )

    # Confidential / restricted data never leaves
    # the local environment in V1.
    if data_sensitivity in {
        "confidential",
        "restricted",
    }:
        return ExternalAIProcessingDecision(
            ai_processing_status="blocked",
            external_ai_allowed=False,
            reason_code="sensitive_data_blocked",
            reason=(
                "Confidential or restricted data "
                "cannot be processed by external AI."
            ),
        )

    # Work data must belong to an organization.
    if (
        usage_context == "work"
        and not organization_id
    ):
        return ExternalAIProcessingDecision(
            ai_processing_status="blocked",
            external_ai_allowed=False,
            reason_code="organization_required",
            reason=(
                "Work data requires an organization "
                "before external AI processing "
                "can be considered."
            ),
        )

    # Public data may use external AI.
    if data_sensitivity == "public":
        return ExternalAIProcessingDecision(
            ai_processing_status="allowed",
            external_ai_allowed=True,
            reason_code="allowed_public",
            reason=(
                "Public data processing is allowed."
            ),
        )

    # Personal internal data.
    if (
        usage_context == "personal"
        and data_sensitivity == "internal"
    ):
        return ExternalAIProcessingDecision(
            ai_processing_status="allowed",
            external_ai_allowed=True,
            reason_code="allowed_personal_internal",
            reason=(
                "Personal internal data processing "
                "is allowed."
            ),
        )

    # Work internal data requires explicit
    # organization policy.
    if (
        usage_context == "work"
        and data_sensitivity == "internal"
    ):

        if organization_ai_allowed is None:
            return ExternalAIProcessingDecision(
                ai_processing_status="pending",
                external_ai_allowed=False,
                reason_code=(
                    "organization_policy_required"
                ),
                reason=(
                    "Organization AI policy must "
                    "explicitly allow external processing."
                ),
            )

        if organization_ai_allowed is False:
            return ExternalAIProcessingDecision(
                ai_processing_status="blocked",
                external_ai_allowed=False,
                reason_code=(
                    "organization_policy_blocked"
                ),
                reason=(
                    "Organization policy blocks "
                    "external AI processing."
                ),
            )

        return ExternalAIProcessingDecision(
            ai_processing_status="allowed",
            external_ai_allowed=True,
            reason_code=(
                "allowed_organization_internal"
            ),
            reason=(
                "Organization policy allows external "
                "AI processing for internal data."
            ),
        )

    # Default deny.
    return ExternalAIProcessingDecision(
        ai_processing_status="blocked",
        external_ai_allowed=False,
        reason_code="unknown_sensitivity",
        reason=(
            "No security policy allows this data "
            "to use external AI processing."
        ),
    )