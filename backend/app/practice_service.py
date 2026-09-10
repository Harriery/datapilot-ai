from backend.app.models import (
    PracticeRecommendation,
    PracticeRecommendationResponse,
    PracticeChallenge,
    PracticeChallengeResponse,
    PracticeChallengeRecord,
    PracticeAttemptRequest,
    PracticeAttemptValidation,
)
import backend.app.database as database
from uuid import uuid4
from backend.app.progress_service import (
    get_learner_progress,
)


# ==================================================
# PRACTICE RECOMMENDATION SERVICE
# ==================================================
#
# Akış:
#
# learner_id
# ↓
# learner progress
# ↓
# practice_priority
# ↓
# en önemli skill
# ↓
# difficulty
# ↓
# PracticeRecommendationResponse


PRIORITY_SCORE = {
    "high": 3,
    "medium": 2,
    "low": 1,
    "none": 0,
}


def get_practice_difficulty(
    skill_status: str,
) -> str:

    if skill_status == "new":
        return "foundation"

    if skill_status == "learning":
        return "easy"

    if skill_status == "practicing":
        return "medium"

    return "hard"


def get_practice_recommendation(
    learner_id: str,
) -> PracticeRecommendationResponse:

    progress = get_learner_progress(
        learner_id=learner_id
    )

    # Practice gerektirmeyen skill'leri çıkarıyoruz.
    practice_candidates = [
        skill
        for skill in progress.skills
        if skill.practice_priority != "none"
    ]

    # Hiç candidate yoksa şu anda practice önerisi yok.
    if not practice_candidates:
        return PracticeRecommendationResponse(
            learner_id=learner_id,
            recommendation=None,
        )

    # En yüksek practice priority'ye sahip skill seçilir.
    selected_skill = max(
        practice_candidates,
        key=lambda skill: (
            PRIORITY_SCORE[
                skill.practice_priority
            ],
            1 - skill.success_rate,
        ),
    )

    difficulty = get_practice_difficulty(
        selected_skill.status
    )

    reason = (
        f"{selected_skill.skill_name} skill'i "
        f"{selected_skill.status} seviyesinde ve "
        f"practice priority "
        f"{selected_skill.practice_priority}."
    )

    recommendation = PracticeRecommendation(
        skill_name=selected_skill.skill_name,
        priority=selected_skill.practice_priority,
        difficulty=difficulty,
        reason=reason,
    )

    return PracticeRecommendationResponse(
        learner_id=learner_id,
        recommendation=recommendation,
    )

def create_practice_challenge(
    learner_id: str,
) -> PracticeChallengeResponse:

    recommendation_response = get_practice_recommendation(
        learner_id=learner_id
    )

    recommendation = recommendation_response.recommendation

    if recommendation is None:
        raise ValueError(
            "Bu learner için şu anda practice recommendation yok."
        )

    skill_name = recommendation.skill_name
    difficulty = recommendation.difficulty

    # --------------------------------------------------
    # PYTHON DATA STRUCTURES
    # --------------------------------------------------
    if skill_name == "python_data_structures":

        challenge = PracticeChallenge(
            challenge_id=str(uuid4()),
            skill_name=skill_name,
            difficulty=difficulty,
            challenge_type="code",
            title="Eksik city değerlerini bul",
            instructions=(
                "Aşağıdaki records listesinde city değeri "
                "eksik olan kayıtların sayısını hesapla ve "
                "sonucu print ile ekrana yazdır."
            ),
            starter_code=(
                "records = [\n"
                "    {'name': 'Ali', 'city': 'Den Haag'},\n"
                "    {'name': 'Ayse', 'city': None},\n"
                "    {'name': 'Mehmet', 'city': 'Utrecht'},\n"
                "    {'name': 'Zeynep', 'city': None},\n"
                "]\n"
            ),
        )

        expected_outcome = (
            "Eksik city değeri olan kayıtların sayısı 2 olmalı."
        )

    # --------------------------------------------------
    # NULL ANALYSIS
    # --------------------------------------------------
    elif skill_name == "null_analysis":

        challenge = PracticeChallenge(
            challenge_id=str(uuid4()),
            skill_name=skill_name,
            difficulty=difficulty,
            challenge_type="transformation",
            title="Eksik age değerlerini incele",
            instructions=(
                "Customer dataset içindeki eksik age değerlerini "
                "tespit et ve uygun bir transformation uygula."
            ),
            starter_code=None,
        )

        expected_outcome = (
            "Eksik age değerleri analiz edilmeli ve "
            "transformation sonrası null sayısı azaltılmalı."
        )

    # --------------------------------------------------
    # DUPLICATE ANALYSIS
    # --------------------------------------------------
    elif skill_name == "duplicate_analysis":

        challenge = PracticeChallenge(
            challenge_id=str(uuid4()),
            skill_name=skill_name,
            difficulty=difficulty,
            challenge_type="transformation",
            title="Duplicate kayıtları temizle",
            instructions=(
                "Dataset içindeki duplicate customer kayıtlarını "
                "tespit et ve tekrar eden kayıtları temizle."
            ),
            starter_code=None,
        )

        expected_outcome = (
            "Transformation sonrası duplicate row sayısı azalmalı."
        )

    # --------------------------------------------------
    # FALLBACK
    # --------------------------------------------------
    else:

        challenge = PracticeChallenge(
            challenge_id=str(uuid4()),
            skill_name=skill_name,
            difficulty=difficulty,
            challenge_type="explain",
            title=f"{skill_name} practice",
            instructions=(
                f"{skill_name} konusunda kullandığın yaklaşımı "
                "kısa şekilde açıkla."
            ),
            starter_code=None,
        )

        expected_outcome = (
            "Junior çözüm mantığını kendi cümleleriyle açıklamalı."
        )

    # Public challenge + backend'e özel validation bilgisi.
    record = PracticeChallengeRecord(
        challenge=challenge,
        expected_outcome=expected_outcome,
    )

    # Challenge artık challenge_id ile daha sonra
    # tekrar bulunabilmesi için DB'ye kaydedilir.
    database.save_practice_challenge(
        learner_id=learner_id,
        record=record,
    )

    # Junior'a yalnızca PUBLIC challenge gönderilir.
    return PracticeChallengeResponse(
        learner_id=learner_id,
        challenge=challenge,
    )

def validate_practice_attempt(
    attempt: PracticeAttemptRequest,
) -> PracticeAttemptValidation:
    """
    Junior'ın practice attempt'ini deterministik olarak kontrol eder.

    AI burada kullanılmaz.

    Akış:
    challenge_id
    ↓
    challenge DB'den yüklenir
    ↓
    execution sonucu kontrol edilir
    ↓
    success True / False
    """

    record = database.get_practice_challenge(
        challenge_id=attempt.challenge_id,
        learner_id=attempt.learner_id,
    )

    if record is None:
        raise ValueError(
            "Practice challenge bulunamadı."
        )

    challenge = record.challenge

    # Kod çalışırken hata oluştuysa challenge başarılı değildir.
    if attempt.execution_error:
        return PracticeAttemptValidation(
            success=False,
            feedback="Kod çalışırken bir hata oluştu.",
        )

    # --------------------------------------------------
    # PYTHON DATA STRUCTURES
    # --------------------------------------------------
    #
    # İlk challenge'ımızda beklenen çıktı 2.
    #
    # Backend junior'ın yazdığı kodu çalıştırmaz.
    # Kod ileride frontend'de Pyodide ile çalıştırılacak.
    # Backend yalnızca oluşan sonucu doğrular.
    if (
        challenge.skill_name == "python_data_structures"
        and challenge.challenge_type == "code"
    ):
        output = (
            attempt.execution_output or ""
        ).strip()

        success = output == "2"

        if success:
            return PracticeAttemptValidation(
                success=True,
                feedback="Challenge başarıyla tamamlandı.",
            )

        return PracticeAttemptValidation(
            success=False,
            feedback=(
                "Kod çalıştı ancak beklenen sonuç elde edilmedi."
            ),
        )

    raise ValueError(
        "Bu challenge türü için validation henüz desteklenmiyor."
    )