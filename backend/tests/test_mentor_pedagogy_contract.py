from backend.app.mentor_pedagogy_contract import (
    enforce_discovery_contract,
    wants_discovery_without_solution,
)


def test_discovery_request_detects_explicit_preference():
    assert wants_discovery_without_solution(
        "Eksik oranını açıkla ve çözümü doğrudan vermeden yönlendir."
    )
    assert not wants_discovery_without_solution(
        "Bana bu pandas kodunu yaz."
    )


def test_solution_dump_replaced_with_single_learning_question():
    message = "Neden önemli? Çözümü doğrudan vermeden yönlendir."
    reply = (
        "Eksik değerler analiz sonuçlarını etkileyebilir.\n\n"
        "**İnceleme adımı:**\n"
        "1. `df[col].isnull().mean()` kullan.\n"
        "2. Sonucu tabloya dök.\n"
        "Ardından temizleme stratejisi belirle."
    )
    result = enforce_discovery_contract(message, reply)
    assert "Eksik değerler" in result
    assert "df[col]" not in result
    assert "temizleme stratejisi" not in result
    assert result.count("?") == 1
    assert "1." not in result
    assert "2." not in result


def test_short_conceptual_reply_is_preserved():
    message = "Çözümü verme, beni yönlendir."
    reply = "Eksik oranı verinin kullanılabilirliğini gösterir. Sence neden?"
    assert enforce_discovery_contract(message, reply) == reply


def test_code_allowed_when_explicitly_requested():
    message = "Çözümü verme ama bana kodu göster."
    reply = "Örnek: `df.isna()`"
    assert enforce_discovery_contract(message, reply) == reply
