from backend.app.models import (
    DocumentAccessDecision,
)


def evaluate_document_access(
    document,
    requester_learner_id: str,
    usage_context: str,
    organization_id: str | None = None,
) -> DocumentAccessDecision:

    document_learner_id = document[
        "learner_id"
    ]

    document_usage_context = document[
        "usage_context"
    ]

    document_organization_id = document[
        "organization_id"
    ]

    # ==================================================
    # OWNER
    # ==================================================

    if not document_learner_id:
        return DocumentAccessDecision(
            allowed=False,
            reason_code="unknown_owner",
            reason=(
                "Document owner is unknown."
            ),
        )

    if (
        document_learner_id
        != requester_learner_id
    ):
        return DocumentAccessDecision(
            allowed=False,
            reason_code="owner_mismatch",
            reason=(
                "Document belongs to another learner."
            ),
        )

    # ==================================================
    # CONTEXT
    # ==================================================

    if document_usage_context not in {
        "personal",
        "work",
    }:
        return DocumentAccessDecision(
            allowed=False,
            reason_code="unknown_context",
            reason=(
                "Document access context is unknown."
            ),
        )

    if (
        document_usage_context
        != usage_context
    ):
        return DocumentAccessDecision(
            allowed=False,
            reason_code="context_mismatch",
            reason=(
                "Requested context does not match "
                "the document context."
            ),
        )

    # ==================================================
    # WORK ORGANIZATION
    # ==================================================

    if document_usage_context == "work":

        if (
            not document_organization_id
            or not organization_id
        ):
            return DocumentAccessDecision(
                allowed=False,
                reason_code=(
                    "organization_required"
                ),
                reason=(
                    "Work document access requires "
                    "an organization scope."
                ),
            )

        if (
            document_organization_id
            != organization_id
        ):
            return DocumentAccessDecision(
                allowed=False,
                reason_code=(
                    "organization_mismatch"
                ),
                reason=(
                    "Document belongs to another "
                    "organization."
                ),
            )

    # ==================================================
    # ALLOW
    # ==================================================

    return DocumentAccessDecision(
        allowed=True,
        reason_code="allowed",
        reason="Document access is allowed.",
    )