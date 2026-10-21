from backend.app.mentor_pedagogy_contract import (
    enforce_discovery_contract,
    wants_discovery_without_solution,
    is_mentor_reply_review_request,
    enforce_reply_review_contract,
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


def test_previous_mentor_error_question_is_review_not_new_assignment():
    message = (
        "Az önce DIVERTED = 0 iptal edilmemiş demek dedin, ama "
        "CANCELLED = 1. Önceki açıklaman doğru muydu?"
    )
    assert is_mentor_reply_review_request(message)
    answer = (
        "Önceki açıklamam yanlıştı. Bu iki sütun farklı kavramları gösterir.\n\n"
        "**Bir sonraki küçük adım:** Bir sütunda yeni filtre çalıştır."
    )
    result = enforce_reply_review_contract(message, answer)
    assert "Önceki açıklamam yanlıştı" in result
    assert "Bir sonraki" not in result


def test_normal_mentor_guidance_is_not_suppressed():
    message = "Eksik kayıtlar için bir sonraki adım nedir?"
    answer = "Bir sonraki adım: Eksik satır sayısını kontrol et."
    assert not is_mentor_reply_review_request(message)
    assert enforce_reply_review_contract(message, answer) == answer


def test_review_correct_answer_does_not_force_false_apology():
    message = "Önceki cevabın doğru muydu?"
    answer = "Evet, önceki açıklama mevcut kanıtla uyumlu."
    assert enforce_reply_review_contract(message, answer) == answer


def test_explicit_previous_answer_review_is_detected_without_error_claim():
    assert is_mentor_reply_review_request(
        "Önceki cevabını teknik olarak yeniden değerlendir. "
        "Kanıtlarla varsayımları ayır ve yeni görev verme."
    )
    assert not is_mentor_reply_review_request(
        "Notebook bulgularını değerlendir ve sonucu açıkla."
    )
