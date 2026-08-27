from backend.app.models import MentorDecision
import pytest
from pydantic import ValidationError

# ==================================================
# TEST - GEÇERLİ MENTOR KARARI
# ==================================================
# Amaç:
# İzin verilen bir assistance_level ile
# MentorDecision modelinin oluşturulabildiğini doğrular.
def test_mentor_decision_accepts_valid_assistance_level():
    decision = MentorDecision(
        skill_name="python_dict",
        assistance_level="GUIDE",
        reason="Kullanıcı yönlendirmeye ihtiyaç duyuyor.",
    )

    assert decision.skill_name == "python_dict"
    assert decision.assistance_level == "GUIDE"


# ==================================================
# TEST - GEÇERSİZ MENTOR YARDIM SEVİYESİ REDDEDİLİYOR
# ==================================================
# Amaç:
# Literal içinde tanımlanmayan bir assistance_level verilirse
# Pydantic'in validation hatası verdiğini doğrular.
def test_mentor_decision_rejects_invalid_assistance_level():
    with pytest.raises(ValidationError):
        MentorDecision(
            skill_name="python_dict",
            assistance_level="SUPER_HELP",
            reason="Geçersiz yardım seviyesi testi.",
        )