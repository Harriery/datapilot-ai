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
