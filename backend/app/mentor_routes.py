"""
Mentor ile ilgili API endpoint'lerini içerir.

Bu dosyanın görevi:
- Dışarıdan gelen mentor request'lerini almak.
- Request içindeki veriyi mentor_service.py'ye göndermek.
- Mentor servisinin ürettiği cevabı API response olarak döndürmek.

Önemli:
Burada mentorun karar mantığını yazmıyoruz.
Asıl mentor mantığı mentor_service.py içinde kalır.
Bu dosya sadece API ile service arasındaki bağlantıdır.
"""

from fastapi import APIRouter, HTTPException
from openai import (
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
)

from backend.app.models import DataQualityMentorRequest
from backend.app.mentor_service import (
    get_mentor_response_for_data_quality_finding,
)


# Bu router içindeki bütün endpoint'ler /mentor ile başlayacak.
#
# Örneğin aşağıda:
# @router.post("/data-quality")
#
# yazarsak gerçek endpoint:
# POST /mentor/data-quality
#
# olur.
router = APIRouter(
    prefix="/mentor",
    tags=["mentor"],
)


# ---------------------------------------------------------
# DATA QUALITY MENTOR ENDPOINT
# ---------------------------------------------------------
#
# Amaç:
# CSV analizinde daha önce oluşturulan bir DataQualityFinding'i
# learner'ın seviyesine uygun mentor yardımına dönüştürmek.
#
# Request örneği:
#
# {
#     "learner_id": "learner-1",
#     "finding": {
#         "issue_type": "missing_values",
#         "column": "age",
#         "severity": "medium",
#         "observation": "age sütununda eksik değer var.",
#         "suggested_action": "Eksik değerin nedenini inceleyin."
#     }
# }
#
# Akış:
#
# DataQualityMentorRequest
# ↓
# request.learner_id + request.finding
# ↓
# get_mentor_response_for_data_quality_finding()
# ↓
# learner skill state + MentorDecision
# ↓
# adaptif mentor cevabı
# ↓
# API response
#
@router.post("/data-quality")
def mentor_data_quality(request: DataQualityMentorRequest):

    try:
        mentor_response = get_mentor_response_for_data_quality_finding(
            learner_id=request.learner_id,
            finding=request.finding,
        )

    # Örneğin learner profile bulunamazsa
    # service tarafı ValueError üretebilir.
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    # OpenAI API anahtarı geçersizse.
    except AuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="OpenAI API anahtarı geçersiz.",
        )

    # OpenAI kullanım limiti / bakiye problemi varsa.
    except RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="AI kullanım limiti veya bakiyesi yetersiz.",
        )

    # OpenAI servisine bağlantı kurulamazsa.
    except APIConnectionError:
        raise HTTPException(
            status_code=503,
            detail="AI servisine şu anda ulaşılamıyor.",
        )

    # Finding herhangi bir mentor skill'i ile eşleşmiyorsa
    # service None döndürebilir.
    if mentor_response is None:
        raise HTTPException(
            status_code=400,
            detail="Bu data quality problemi için uygun mentor skill'i bulunamadı.",
        )

    # Junior'a gösterilecek adaptif mentor cevabı.
    return {
        "mentor_response": mentor_response
    }