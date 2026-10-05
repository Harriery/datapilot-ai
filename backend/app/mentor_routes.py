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
    LearnerProgressResponse,
    PracticeRecommendationResponse,
    PracticeChallengeResponse,
    PracticeAttemptRequest,
    LearnerLanguageUpdateRequest,
    LearnerLanguageResponse,
    PracticeAttemptPublicResponse,
    PracticeMicroCheckRequest,
    PracticeMicroCheckResponse,
    PracticeHintRequest,
    PracticeHintResponse,
    PracticeSolutionRequest,
    PracticeSolutionResponse,
    PracticeCatalogResponse,
    PracticeExerciseSourceResponse,
    PracticeExerciseContentResponse,
    PracticeExerciseValidationBundle,
    LearnerJournalResponse,
    LearnerNote,
    LearnerNoteCreateRequest,
    LearnerNoteUpdateRequest,
    LearnerResumeState,
    LearnerResumeStateUpsertRequest,
)
from backend.app.practice_micro_check_service import (
    review_practice_micro_check,
)

from backend.app.practice_review_service import (
    review_practice_attempt,
)

from backend.app.practice_service import (
    get_practice_recommendation,
    create_practice_challenge,
    get_next_practice_hint,
    get_practice_solution,
)
from backend.app.practice_catalog_service import (
    get_practice_catalog,
)
from backend.app.practice_exercism_adapter import (
    get_exercism_python_exercise_content,
    get_exercism_python_validation_bundle,
    list_exercism_python_exercises,
)
from backend.app.progress_service import (
    get_learner_progress,
)
from backend.app.learner_journal_service import (
    add_note,
    edit_note,
    get_journal,
    remove_note,
    save_resume_state,
)



from backend.app.local_data_quality_mentor_service import (
    get_local_mentor_response_for_data_quality_finding,
    review_data_quality_attempt_locally,
    review_data_quality_transformation_locally,
    review_task_transformation_locally,
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
def mentor_data_quality(
    request: DataQualityMentorRequest,
):

    mentor_response = (
        get_local_mentor_response_for_data_quality_finding(
            learner_id=request.learner_id,
            finding=request.finding,
        )
    )

    if mentor_response is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Bu data quality problemi için "
                "uygun mentor skill'i bulunamadı."
            ),
        )

    return {
        "mentor_response":
            mentor_response
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
        result = (
            review_data_quality_attempt_locally(
                learner_id=request.learner_id,
                finding=request.finding,
                attempt=request.attempt,
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    if result is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Bu data quality problemi için "
                "uygun mentor skill'i bulunamadı."
            ),
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
        result = (
            review_data_quality_transformation_locally(
                learner_id=request.learner_id,
                finding=request.finding,
                before_df=before_df,
                after_df=after_df,
            )
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
        result = (
            review_task_transformation_locally(
                learner_id=request.learner_id,
                task=task,
                before_df=before_df,
                after_df=after_df,
            )
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

# ---------------------------------------------------------
# LEARNER PROGRESS ENDPOINT
# ---------------------------------------------------------
#
# Junior'ın bütün takip edilen skill'lerdeki
# mevcut gelişim özetini döndürür.
#
# Akış:
#
# learner_id
# ↓
# learner gerçekten var mı?
# ↓
# skill states + learning evidence
# ↓
# progress_service
# ↓
# LearnerProgressResponse


@router.get(
    "/progress/{learner_id}",
    response_model=LearnerProgressResponse,
)
def get_progress(
    learner_id: str,
):

    learner_profile = database.get_learner_profile_by_id(
        learner_id
    )

    if learner_profile is None:
        raise HTTPException(
            status_code=404,
            detail="Learner profile bulunamadı.",
        )

    return get_learner_progress(
        learner_id=learner_id
    )

# ---------------------------------------------------------
# LEARNER JOURNAL / RESUME STATE
# ---------------------------------------------------------

@router.put(
    "/journal/{learner_id}/resume",
    response_model=LearnerResumeState,
)
def upsert_learner_resume_state_route(
    learner_id: str,
    request: LearnerResumeStateUpsertRequest,
):
    learner = database.get_learner_profile_by_id(
        learner_id
    )

    if learner is None:
        raise HTTPException(
            status_code=404,
            detail="Learner profile bulunamadı.",
        )

    return save_resume_state(
        learner_id=learner_id,
        request=request,
    )


@router.get(
    "/journal/{learner_id}",
    response_model=LearnerJournalResponse,
)
def get_learner_journal_route(
    learner_id: str,
    context_type: str,
    context_key: str,
):
    learner = database.get_learner_profile_by_id(
        learner_id
    )

    if learner is None:
        raise HTTPException(
            status_code=404,
            detail="Learner profile bulunamadı.",
        )

    if context_type not in {
        "practice",
        "workspace",
    }:
        raise HTTPException(
            status_code=400,
            detail="Geçersiz journal context_type.",
        )

    return get_journal(
        learner_id=learner_id,
        context_type=context_type,
        context_key=context_key,
    )


@router.post(
    "/journal/{learner_id}/notes",
    response_model=LearnerNote,
)
def create_learner_note_route(
    learner_id: str,
    request: LearnerNoteCreateRequest,
):
    learner = database.get_learner_profile_by_id(
        learner_id
    )

    if learner is None:
        raise HTTPException(
            status_code=404,
            detail="Learner profile bulunamadı.",
        )

    return add_note(
        learner_id=learner_id,
        request=request,
    )


@router.patch(
    "/journal/{learner_id}/notes/{note_id}",
    response_model=LearnerNote,
)
def update_learner_note_route(
    learner_id: str,
    note_id: str,
    request: LearnerNoteUpdateRequest,
):
    note = edit_note(
        learner_id=learner_id,
        note_id=note_id,
        request=request,
    )

    if note is None:
        raise HTTPException(
            status_code=404,
            detail="Note bulunamadı.",
        )

    return note


@router.delete(
    "/journal/{learner_id}/notes/{note_id}",
    status_code=204,
)
def delete_learner_note_route(
    learner_id: str,
    note_id: str,
):
    deleted = remove_note(
        learner_id=learner_id,
        note_id=note_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Note bulunamadı.",
        )


# ---------------------------------------------------------
# PRACTICE V2 EXTERNAL EXERCISE SOURCE
# ---------------------------------------------------------

@router.get(
    "/practice/source/exercism/python/{learner_id}",
    response_model=PracticeExerciseSourceResponse,
)
def get_exercism_python_practice_source(
    learner_id: str,
    subtopic_id: str,
    difficulty: str,
    practice_mode: str = "code",
):
    learner_profile = (
        database.get_learner_profile_by_id(
            learner_id
        )
    )

    if learner_profile is None:
        raise HTTPException(
            status_code=404,
            detail="Learner profile bulunamadı.",
        )

    if practice_mode != "code":
        raise HTTPException(
            status_code=400,
            detail=(
                "Exercism Python adapter currently "
                "supports code mode only."
            ),
        )

    try:
        return list_exercism_python_exercises(
            learner_id=learner_id,
            subtopic_id=subtopic_id,
            difficulty=difficulty,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get(
    (
        "/practice/source/exercism/python/"
        "{learner_id}/exercise/{exercise_id}"
    ),
    response_model=PracticeExerciseContentResponse,
)
def get_exercism_python_exercise_content_route(
    learner_id: str,
    exercise_id: str,
    title: str,
    source_revision: str | None = None,
):
    learner_profile = (
        database.get_learner_profile_by_id(
            learner_id
        )
    )

    if learner_profile is None:
        raise HTTPException(
            status_code=404,
            detail="Learner profile bulunamadı.",
        )

    try:
        return get_exercism_python_exercise_content(
            learner_id=learner_id,
            exercise_id=exercise_id,
            title=title,
            source_revision=source_revision,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "External Practice source "
                "could not be loaded."
            ),
        ) from exc


@router.get(
    (
        "/practice/source/exercism/python/"
        "{learner_id}/exercise/{exercise_id}/validation"
    ),
    response_model=PracticeExerciseValidationBundle,
)
def get_exercism_python_validation_bundle_route(
    learner_id: str,
    exercise_id: str,
    source_revision: str | None = None,
):
    learner_profile = (
        database.get_learner_profile_by_id(
            learner_id
        )
    )

    if learner_profile is None:
        raise HTTPException(
            status_code=404,
            detail="Learner profile bulunamadı.",
        )

    try:
        return get_exercism_python_validation_bundle(
            learner_id=learner_id,
            exercise_id=exercise_id,
            source_revision=source_revision,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "External Practice validation "
                "bundle could not be loaded."
            ),
        ) from exc


# ---------------------------------------------------------
# PRACTICE V2 CATALOG ENDPOINT
# ---------------------------------------------------------

@router.get(
    "/practice/catalog/{learner_id}",
    response_model=PracticeCatalogResponse,
)
def get_practice_catalog_route(
    learner_id: str,
):
    learner_profile = (
        database.get_learner_profile_by_id(
            learner_id
        )
    )

    if learner_profile is None:
        raise HTTPException(
            status_code=404,
            detail="Learner profile bulunamadı.",
        )

    return get_practice_catalog(
        learner_id=learner_id
    )


# ---------------------------------------------------------
# PRACTICE RECOMMENDATION ENDPOINT
# ---------------------------------------------------------
#
# Learner progress verisine bakarak
# junior için sıradaki practice hedefini döndürür.
#
# Akış:
#
# learner_id
# ↓
# learner var mı?
# ↓
# progress
# ↓
# practice priority
# ↓
# recommended skill + difficulty


@router.get(
    "/practice/recommendation/{learner_id}",
    response_model=PracticeRecommendationResponse,
)
def get_practice_recommendation_route(
    learner_id: str,
):

    learner_profile = database.get_learner_profile_by_id(
        learner_id
    )

    if learner_profile is None:
        raise HTTPException(
            status_code=404,
            detail="Learner profile bulunamadı.",
        )

    return get_practice_recommendation(
        learner_id=learner_id
    )

# ---------------------------------------------------------
# CREATE PRACTICE CHALLENGE ENDPOINT
# ---------------------------------------------------------
#
# Learner progress ve practice recommendation üzerinden
# junior için yeni bir challenge oluşturur.
#
# Akış:
#
# learner_id
# ↓
# learner var mı?
# ↓
# practice recommendation
# ↓
# skill + difficulty
# ↓
# PracticeChallenge


@router.post(
    "/practice/challenge/{learner_id}",
    response_model=PracticeChallengeResponse,
)
def create_practice_challenge_route(
    learner_id: str,
):

    learner_profile = database.get_learner_profile_by_id(
        learner_id
    )

    if learner_profile is None:
        raise HTTPException(
            status_code=404,
            detail="Learner profile bulunamadı.",
        )

    try:
        return create_practice_challenge(
            learner_id=learner_id
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

# ---------------------------------------------------------
# PRACTICE HINT ENDPOINT
# ---------------------------------------------------------
#
# Junior challenge sırasında yardım istediğinde
# sıradaki deterministik hint'i döndürür.
#
# Bütün hint'ler bir anda frontend'e gönderilmez.
# Backend yalnızca sıradaki izin verilen hint'i açar.
#
# Bu endpoint OpenAI kullanmaz.
@router.post(
    "/practice/hint",
    response_model=PracticeHintResponse,
)
def get_practice_hint_route(
    request: PracticeHintRequest,
):
    learner_profile = database.get_learner_profile_by_id(
        request.learner_id
    )

    if learner_profile is None:
        raise HTTPException(
            status_code=404,
            detail="Learner profile bulunamadı.",
        )

    try:
        return get_next_practice_hint(
            learner_id=request.learner_id,
            challenge_id=request.challenge_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

# ---------------------------------------------------------
# PRACTICE SOLUTION ENDPOINT
# ---------------------------------------------------------
#
# Junior bütün hint'leri kullandıktan sonra
# tam çözümü özellikle isterse döndürülür.
#
# Solution kullanımı DEMONSTRATE seviyesidir.
@router.post(
    "/practice/solution",
    response_model=PracticeSolutionResponse,
)
def get_practice_solution_route(
    request: PracticeSolutionRequest,
):
    learner_profile = database.get_learner_profile_by_id(
        request.learner_id
    )

    if learner_profile is None:
        raise HTTPException(
            status_code=404,
            detail="Learner profile bulunamadı.",
        )

    try:
        return get_practice_solution(
            learner_id=request.learner_id,
            challenge_id=request.challenge_id,
        )

    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )



# ---------------------------------------------------------
# REVIEW PRACTICE ATTEMPT ENDPOINT
# ---------------------------------------------------------
#
# Junior'ın challenge için yaptığı denemeyi işler.
#
# Akış:
#
# PracticeAttemptRequest
# ↓
# learner kontrolü
# ↓
# challenge kontrolü
# ↓
# deterministic validation
# ↓
# başarısızsa AI diagnosis
# ↓
# adaptive assistance policy
# ↓
# mentor support
# ↓
# attempt DB'ye kaydedilir
# ↓
# PracticeAttemptReview


@router.post(
    "/practice/attempt",
    response_model=PracticeAttemptPublicResponse,
)
def review_practice_attempt_route(
    attempt: PracticeAttemptRequest,
):

    # --------------------------------------------------
    # LEARNER VAR MI?
    # --------------------------------------------------

    learner_profile = database.get_learner_profile_by_id(
        attempt.learner_id
    )

    if learner_profile is None:
        raise HTTPException(
            status_code=404,
            detail="Learner profile bulunamadı.",
        )

    # --------------------------------------------------
    # CHALLENGE VAR MI VE BU LEARNER'A MI AİT?
    # --------------------------------------------------

    challenge_record = database.get_practice_challenge(
        challenge_id=attempt.challenge_id,
        learner_id=attempt.learner_id,
    )

    if challenge_record is None:
        raise HTTPException(
            status_code=404,
            detail="Practice challenge bulunamadı.",
        )

    # --------------------------------------------------
    # ATTEMPT REVIEW
    # --------------------------------------------------

    try:
        return review_practice_attempt(
            attempt=attempt
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

# ---------------------------------------------------------
# UPDATE LEARNER LANGUAGE
# ---------------------------------------------------------
#
# Frontend'de kullanıcı mentor dilini seçebilir:
#
# auto → kullanıcının diline göre
# tr   → Türkçe
# en   → English
# nl   → Nederlands


@router.patch(
    "/profile/{learner_id}/language",
    response_model=LearnerLanguageResponse,
)
def update_learner_language(
    learner_id: str,
    request: LearnerLanguageUpdateRequest,
):

    learner_profile = database.get_learner_profile_by_id(
        learner_id
    )

    if learner_profile is None:
        raise HTTPException(
            status_code=404,
            detail="Learner profile bulunamadı.",
        )

    database.update_learner_preferred_language(
        learner_id=learner_id,
        preferred_language=request.preferred_language,
    )

    return LearnerLanguageResponse(
        learner_id=learner_id,
        preferred_language=request.preferred_language,
    )

# ---------------------------------------------------------
# REVIEW PRACTICE MICRO-CHECK
# ---------------------------------------------------------
#
# Mentorun sorduğu küçük kontrol sorusuna
# junior'ın verdiği cevabı değerlendirir.
#
# Akış:
#
# learner_id + attempt_id + answer
# ↓
# ilgili attempt DB'den bulunur
# ↓
# micro-check sorusu bulunur
# ↓
# primary concept bulunur
# ↓
# cevap değerlendirilir
# ↓
# doğru  → return_to_challenge
# yanlış → more_support


@router.post(
    "/practice/micro-check",
    response_model=PracticeMicroCheckResponse,
)
def review_practice_micro_check_route(
    request: PracticeMicroCheckRequest,
):

    try:
        return review_practice_micro_check(
            request=request
        )

    except ValueError as exc:

        message = str(exc)

        if (
            "Practice attempt bulunamadı" in message
            or "Learner profile bulunamadı" in message
        ):
            raise HTTPException(
                status_code=404,
                detail=message,
            )

        raise HTTPException(
            status_code=400,
            detail=message,
        )