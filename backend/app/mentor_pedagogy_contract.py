"""Turn-level pedagogical response guard for explicit discovery-first requests.

No external model call. Intended to prevent unsolicited code and multi-step
solutions while preserving a concise conceptual explanation.
"""
from __future__ import annotations

import re


_DISCOVERY_MARKERS = (
    "çözümü doğrudan verme",
    "çözümü verme",
    "çözümü söyleme",
    "çözümü göstermeden",
    "çözümü doğrudan vermeden",
    "beni yönlendir",
    "ipucu ver",
    "without giving me the solution",
    "don't give me the solution",
    "do not give me the solution",
    "guide me without",
)
_EXPLICIT_CODE_MARKERS = (
    "kodu göster",
    "kod örneği ver",
    "kodu yaz",
    "show me the code",
    "give me the code",
)
_CODE_PATTERN = re.compile(
    r"(?m)(`{3}|\bdf\s*\[|\.isnull\s*\(|\.isna\s*\(|"
    r"\.groupby\s*\(|\b(?:SELECT|UPDATE|DELETE|INSERT)\s+.+\bFROM\b|"
    r"^\s*(?:import |from \w+ import |print\())"
)
_STEPS_PATTERN = re.compile(r"(?m)^\s*(?:[-*]\s+|[1-9][.)]\s+)")
_MARKDOWN_BOLD = re.compile(r"\*\*(.*?)\*\*")


def wants_discovery_without_solution(message: str) -> bool:
    normalized = message.casefold()
    return (
        any(marker in normalized for marker in _DISCOVERY_MARKERS)
        and not any(marker in normalized for marker in _EXPLICIT_CODE_MARKERS)
    )


def enforce_discovery_contract(message: str, reply: str) -> str:
    """Replace solution dumps with one short concept and one question."""
    if not wants_discovery_without_solution(message):
        return reply
    if not (
        _CODE_PATTERN.search(reply)
        or len(_STEPS_PATTERN.findall(reply)) > 1
    ):
        return reply

    # Retain only a short explanatory paragraph, never the proposed procedure.
    first_paragraph = re.split(
        r"\n\s*\n|\n\s*(?:\*\*?İnceleme|[1-9][.)]|[-*]\s+)",
        reply,
        maxsplit=1,
    )[0].strip()
    first_paragraph = _MARKDOWN_BOLD.sub(r"\1", first_paragraph)
    first_paragraph = re.sub(r"\*([^*]+)\*", r"\1", first_paragraph)
    first_paragraph = re.sub(r"\s+", " ", first_paragraph)
    if (
        not first_paragraph
        or _CODE_PATTERN.search(first_paragraph)
        or len(first_paragraph) > 420
    ):
        first_paragraph = (
            "Önce kavramı anlamaya ve mevcut verideki kanıtları incelemeye "
            "odaklanalım; henüz çözüm uygulamayacağız."
        )
    return (
        first_paragraph.rstrip(".!?") + ".\n\n"
        "İlk olarak veri profilinde hangi gözlemi incelememiz gerektiğini "
        "düşünüyorsun?"
    )


# A review of Mentor's OWN preceding claim is not a request for another
# learning assignment. Never hard-code dataset-specific column meanings here.
_REPLY_REVIEW_MARKERS = (
    "önceki açıklaman doğru",
    "önceki cevabın doğru",
    "önceki açıklaman yanlış",
    "önceki cevabın yanlış",
    "hatalı cevap verdin",
    "yanlış söyledin",
    "was your previous answer correct",
    "was your earlier answer correct",
    "your previous answer was wrong",
    "you were wrong",
)
_UNSOLICITED_NEXT_STEP = re.compile(
    r"(?im)^\s*(?:\\*\\*)?\\s*(?:bir sonraki(?: küçük)? adım|"
    r"sıradaki(?: küçük)? adım|next step|yeni görev)"
    r"\\s*(?:\\*\\*)?\\s*[:：]"
)


def is_mentor_reply_review_request(message: str) -> bool:
    """Explicit request to audit or correct Mentor's prior answer."""
    normalized = message.casefold()
    if any(marker in normalized for marker in _REPLY_REVIEW_MARKERS):
        return True
    earlier = any(term in normalized for term in (
        "az önce", "biraz önce", "daha önce", "earlier you", "you said",
    ))
    assistant_claim = any(term in normalized for term in (
        "söyledin", "dedin", "cevabın", "açıklaman",
        "you said", "your answer", "your explanation",
    ))
    disputed = any(term in normalized for term in (
        "doğru", "yanlış", "hata", "correct", "wrong", "mistake",
    ))
    return earlier and assistant_claim and disputed


def enforce_reply_review_contract(message: str, reply: str) -> str:
    """Preserve actual correction, strip unsolicited follow-up assignments.

    No automatic 'you were wrong' is inserted: the previous claim may have
    been right and only the AI plus trusted context can judge that.
    """
    if not is_mentor_reply_review_request(message):
        return reply
    match = _UNSOLICITED_NEXT_STEP.search(reply)
    if match and reply[:match.start()].strip():
        return reply[:match.start()].rstrip()
    return reply
