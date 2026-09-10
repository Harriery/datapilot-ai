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

from backend.app.models import (
    DataQualityMentorRequest,
    DataQualityAttemptRequest,
    DataQualityAttemptResponse,
    DataQualityTransformationRequest,
    DataQualityTransformationResponse,
    DataEngineeringTaskTransformationRequest,
    DataEngineeringTaskTransformationResponse,
    DataEngineeringTask,
    DataEngineeringTaskCreateRequest,
)
from backend.app.mentor_service import (
    get_mentor_response_for_data_quality_finding,
    review_data_quality_attempt,
    review_data_quality_transformation,
    review_data_engineering_task_transformation,
)
import pandas as pd
import backend.app.database as database
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

# ---------------------------------------------------------
# DATA QUALITY JUNIOR ATTEMPT ENDPOINT
# ---------------------------------------------------------
#
# Junior mentorun yönlendirmesinden sonra kendi çözümünü,
# kodunu veya yaklaşımını buraya gönderir.
#
# Akış:
#
# learner + finding + attempt
# ↓
# review_data_quality_attempt()
# ↓
# learning evidence değerlendirmesi
# ↓
# skill state update
# ↓
# adaptif mentor feedback
#
@router.post(
    "/data-quality/attempt",
    response_model=DataQualityAttemptResponse,
)
def mentor_data_quality_attempt(
    request: DataQualityAttemptRequest,
):

    try:
        result = review_data_quality_attempt(
            learner_id=request.learner_id,
            finding=request.finding,
            attempt=request.attempt,
        )

    except ValueError as exc:
        # Learner yoksa resource bulunamadı.
        if "Learner profile bulunamadı" in str(exc):
            raise HTTPException(
                status_code=404,
                detail=str(exc),
            )

        # Boş attempt vb. kullanıcı request hataları.
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except AuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="OpenAI API anahtarı geçersiz.",
        )

    except RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="AI kullanım limiti veya bakiyesi yetersiz.",
        )

    except APIConnectionError:
        raise HTTPException(
            status_code=503,
            detail="AI servisine şu anda ulaşılamıyor.",
        )

    if result is None:
        raise HTTPException(
            status_code=400,
            detail="Bu data quality problemi için uygun mentor skill'i bulunamadı.",
        )

    return result

# ---------------------------------------------------------
# DATA QUALITY TRANSFORMATION ENDPOINT
# ---------------------------------------------------------
#
# Junior'ın gerçek before/after data sonucunu alır.
#
# API JSON içindeki row listelerini pandas DataFrame'e çevirir.
#
# Sonrasında:
#
# before_df + after_df + finding
# ↓
# review_data_quality_transformation()
# ↓
# deterministic validation
# ↓
# learning evidence
# ↓
# skill status update
# ↓
# structured API response
#
@router.post(
    "/data-quality/transformation",
    response_model=DataQualityTransformationResponse,
)
def mentor_data_quality_transformation(
    request: DataQualityTransformationRequest,
):

    # API'den gelen JSON row listelerini
    # pandas DataFrame'e dönüştürüyoruz.
    before_df = pd.DataFrame(request.before_rows)
    after_df = pd.DataFrame(request.after_rows)

    try:
        result = review_data_quality_transformation(
            learner_id=request.learner_id,
            finding=request.finding,
            before_df=before_df,
            after_df=after_df,
        )

    except ValueError as exc:
        # Örneğin missing_values finding'inde column yoksa.
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    if result is None:
        # Şimdilik missing_values dışındaki transformation
        # validation türleri desteklenmiyor.
        raise HTTPException(
            status_code=400,
            detail="Bu data quality transformation türü henüz desteklenmiyor.",
        )

    return result

# ---------------------------------------------------------
# MULTI-STEP DATA ENGINEERING TASK TRANSFORMATION ENDPOINT
# ---------------------------------------------------------
#
# Junior'ın multi-step task içindeki mevcut step için
# yaptığı transformation'ı değerlendirir.
#
# Akış:
#
# learner + task + before_rows + after_rows
# ↓
# JSON rows → pandas DataFrame
# ↓
# current task step bulunur
# ↓
# transformation review
# ↓
# validation
# ↓
# learning evidence
# ↓
# skill status update
# ↓
# success ise task sonraki step'e ilerler
#
@router.post(
    "/task/transformation",
    response_model=DataEngineeringTaskTransformationResponse,
)
@router.post(
    "/task/transformation",
    response_model=DataEngineeringTaskTransformationResponse,
)
def mentor_task_transformation(
    request: DataEngineeringTaskTransformationRequest,
):

    # Task state artık request içinde taşınmıyor.
    # Backend task_id + learner_id kullanarak
    # güncel task durumunu veritabanından yükler.
    task = database.get_data_engineering_task(
        task_id=request.task_id,
        learner_id=request.learner_id,
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Data Engineering task bulunamadı.",
        )

    before_df = pd.DataFrame(request.before_rows)
    after_df = pd.DataFrame(request.after_rows)

    try:
        result = review_data_engineering_task_transformation(
            learner_id=request.learner_id,
            task=task,
            before_df=before_df,
            after_df=after_df,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return result

# ---------------------------------------------------------
# CREATE DATA ENGINEERING TASK ENDPOINT
# ---------------------------------------------------------
#
# Yeni bir multi-step task'ı ilk kez DB'ye kaydeder.
#
# Bu işlem sadece task başlangıcında yapılır.
#
# Sonraki transformation request'lerinde artık
# bütün task gönderilmez; sadece task_id gönderilir.
@router.post(
    "/task",
    response_model=DataEngineeringTask,
)
def create_data_engineering_task(
    request: DataEngineeringTaskCreateRequest,
):

    # Task'ın bağlanacağı learner gerçekten var mı?
    learner_profile = database.get_learner_profile_by_id(
        request.learner_id
    )

    if learner_profile is None:
        raise HTTPException(
            status_code=404,
            detail="Learner profile bulunamadı.",
        )

    # Başlangıç task state'ini DB'ye kaydet.
    database.save_data_engineering_task(
        learner_id=request.learner_id,
        task=request.task,
    )

    return request.task

# ---------------------------------------------------------
# GET DATA ENGINEERING TASK ENDPOINT
# ---------------------------------------------------------
#
# Junior daha sonra uygulamaya geri geldiğinde
# task'ın en son kaydedilmiş durumunu DB'den getirir.
@router.get(
    "/task/{task_id}",
    response_model=DataEngineeringTask,
)
def get_data_engineering_task(
    task_id: str,
    learner_id: str,
):

    task = database.get_data_engineering_task(
        task_id=task_id,
        learner_id=learner_id,
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Data Engineering task bulunamadı.",
        )

    return task