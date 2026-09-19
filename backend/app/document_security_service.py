from backend.app.models import (
    DocumentSecurityDecision,
)


def evaluate_document_ai_policy(
    usage_context: str,
    data_sensitivity: str,
    organization_id: str | None = None,
    organization_ai_allowed: bool | None = None,
) -> DocumentSecurityDecision:

    # ==================================================
    # UNKNOWN CONTEXT
    # ==================================================
    #
    # Belgenin personal mı work mü olduğu bilinmiyorsa
    # external AI'ya gönderilmez.
    if usage_context not in {
        "personal",
        "work",
    }:
        return DocumentSecurityDecision(
            ai_processing_status="blocked",
            external_ai_allowed=False,
            reason_code="unknown_context",
            reason=(
                "Document usage context is unknown. "
                "External AI processing is blocked."
            ),
        )

    # ==================================================
    # UNKNOWN SENSITIVITY
    # ==================================================

    if data_sensitivity == "unknown":
        return DocumentSecurityDecision(
            ai_processing_status="blocked",
            external_ai_allowed=False,
            reason_code="unknown_sensitivity",
            reason=(
                "Document sensitivity is unknown. "
                "External AI processing is blocked."
            ),
        )

    # ==================================================
    # HIGH-SENSITIVITY DATA
    # ==================================================
    #
    # V1'de confidential ve restricted içerik hiçbir
    # durumda external AI processing'e gönderilmez.
    if data_sensitivity in {
        "confidential",
        "restricted",
    }:
        return DocumentSecurityDecision(
            ai_processing_status="blocked",
            external_ai_allowed=False,
            reason_code="sensitive_data_blocked",
            reason=(
                "Confidential or restricted documents "
                "cannot be processed by external AI."
            ),
        )

    # ==================================================
    # WORK DOCUMENT SCOPE
    # ==================================================
    #
    # Work document mutlaka bir organization scope'a
    # bağlı olmalıdır.
    if (
        usage_context == "work"
        and not organization_id
    ):
        return DocumentSecurityDecision(
            ai_processing_status="blocked",
            external_ai_allowed=False,
            reason_code="organization_required",
            reason=(
                "Work documents require an organization "
                "before external AI processing can be considered."
            ),
        )

    # ==================================================
    # PUBLIC
    # ==================================================

    if data_sensitivity == "public":
        return DocumentSecurityDecision(
            ai_processing_status="allowed",
            external_ai_allowed=True,
            reason_code="allowed_public",
            reason=(
                "Public document processing is allowed."
            ),
        )

    # ==================================================
    # INTERNAL — PERSONAL
    # ==================================================
    #
    # Personal context'teki internal içerik kullanıcının
    # kendi private çalışma içeriği olarak kabul edilir.
    #
    # Work kaynaklı içerik personal olarak
    # sınıflandırılmamalıdır.
    if (
        usage_context == "personal"
        and data_sensitivity == "internal"
    ):
        return DocumentSecurityDecision(
            ai_processing_status="allowed",
            external_ai_allowed=True,
            reason_code="allowed_personal_internal",
            reason=(
                "Personal internal document processing "
                "is allowed."
            ),
        )

    # ==================================================
    # INTERNAL — WORK
    # ==================================================
    #
    # Şirket içi veri için organization policy gerekir.
    if (
        usage_context == "work"
        and data_sensitivity == "internal"
    ):

        # Organization policy henüz bilinmiyor.
        if organization_ai_allowed is None:
            return DocumentSecurityDecision(
                ai_processing_status="pending",
                external_ai_allowed=False,
                reason_code=(
                    "organization_policy_required"
                ),
                reason=(
                    "Organization AI policy must explicitly "
                    "allow external processing."
                ),
            )

        # Organization açıkça external AI kullanımını
        # yasaklamış.
        if organization_ai_allowed is False:
            return DocumentSecurityDecision(
                ai_processing_status="blocked",
                external_ai_allowed=False,
                reason_code=(
                    "organization_policy_blocked"
                ),
                reason=(
                    "Organization policy blocks external "
                    "AI processing."
                ),
            )

        # Organization açıkça izin vermiş.
        return DocumentSecurityDecision(
            ai_processing_status="allowed",
            external_ai_allowed=True,
            reason_code=(
                "allowed_organization_internal"
            ),
            reason=(
                "Organization policy allows external "
                "AI processing for internal documents."
            ),
        )

    # ==================================================
    # DEFAULT DENY
    # ==================================================
    #
    # Gelecekte yeni bir sensitivity/context eklenirse
    # yanlışlıkla allow olmaması için.
    return DocumentSecurityDecision(
        ai_processing_status="blocked",
        external_ai_allowed=False,
        reason_code="unknown_sensitivity",
        reason=(
            "No security policy allows this document "
            "to use external AI processing."
        ),
    )