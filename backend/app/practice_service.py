from backend.app.models import (
    PracticeRecommendation,
    PracticeRecommendationResponse,
    PracticeChallenge,
    PracticeChallengeResponse,
    PracticeChallengeRecord,
    PracticeAttemptRequest,
    PracticeAttemptValidation,
    PracticeValidationSpec,
)
import backend.app.database as database
from uuid import uuid4
from backend.app.progress_service import (
    get_learner_progress,
)

import pandas as pd

from backend.app.transformation_validation_service import (
    validate_missing_values_dataframes,
    validate_duplicate_rows_dataframes,
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


PYTHON_DATA_STRUCTURE_VARIANTS = [
    {
        "title": "Eksik city değerlerini bul",
        "instructions": (
            "Aşağıdaki records listesinde city değeri "
            "eksik olan kayıtların sayısını hesapla ve "
            "sonucu print ile ekrana yazdır."
        ),
        "starter_code": (
            "records = [\n"
            "    {'name': 'Ali', 'city': 'Den Haag'},\n"
            "    {'name': 'Ayse', 'city': None},\n"
            "    {'name': 'Mehmet', 'city': 'Utrecht'},\n"
            "    {'name': 'Zeynep', 'city': None},\n"
            "]\n"
        ),
        "expected_output": "2",
    },
    {
        "title": "Aktif kullanıcıları say",
        "instructions": (
            "Aşağıdaki users listesinde active değeri "
            "True olan kullanıcıların sayısını hesapla ve "
            "sonucu print ile ekrana yazdır."
        ),
        "starter_code": (
            "users = [\n"
            "    {'name': 'Sara', 'active': True},\n"
            "    {'name': 'Tom', 'active': False},\n"
            "    {'name': 'Lina', 'active': True},\n"
            "    {'name': 'Sam', 'active': True},\n"
            "]\n"
        ),
        "expected_output": "3",
    },
    {
        "title": "Yüksek skorları say",
        "instructions": (
            "Aşağıdaki results listesinde score değeri "
            "70 veya daha yüksek olan kayıtların sayısını "
            "hesapla ve sonucu print ile ekrana yazdır."
        ),
        "starter_code": (
            "results = [\n"
            "    {'name': 'A', 'score': 55},\n"
            "    {'name': 'B', 'score': 72},\n"
            "    {'name': 'C', 'score': 91},\n"
            "    {'name': 'D', 'score': 64},\n"
            "]\n"
        ),
        "expected_output": "2",
    },
]


def get_python_data_structure_variant(
    variant_index: int,
) -> dict:
    """
    Variant index büyüse bile mevcut template'ler
    arasında güvenli şekilde döner.
    """

    return PYTHON_DATA_STRUCTURE_VARIANTS[
        variant_index
        % len(PYTHON_DATA_STRUCTURE_VARIANTS)
    ]

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

        challenge_count = (
            database.get_practice_challenge_count_by_skill(
                learner_id=learner_id,
                skill_name=skill_name,
            )
        )

        variant = get_python_data_structure_variant(
            challenge_count
        )

        challenge = PracticeChallenge(
            challenge_id=str(uuid4()),
            skill_name=skill_name,
            difficulty=difficulty,
            challenge_type="code",
            title=variant["title"],
            instructions=variant["instructions"],
            starter_code=variant["starter_code"],
        )

        expected_outcome = (
            f"Beklenen çıktı: "
            f"{variant['expected_output']}"
        )

        validation_spec = PracticeValidationSpec(
            validation_type="exact_output",
            expected_output=variant["expected_output"],
        )
       # --------------------------------------------------
    # NULL ANALYSIS
    # --------------------------------------------------
    elif skill_name == "null_analysis":

        input_rows = [
            {
                "customer_id": 1,
                "name": "Ali",
                "age": 30,
            },
            {
                "customer_id": 2,
                "name": "Ayse",
                "age": None,
            },
            {
                "customer_id": 3,
                "name": "Mehmet",
                "age": None,
            },
        ]

        challenge = PracticeChallenge(
            challenge_id=str(uuid4()),
            skill_name=skill_name,
            difficulty=difficulty,
            challenge_type="transformation",
            title="Eksik age değerlerini incele",
            instructions=(
                "Customer dataset içindeki eksik age "
                "değerlerini tespit et ve uygun bir "
                "transformation uygula."
            ),
            starter_code=None,
            input_rows=input_rows,
        )

        expected_outcome = (
            "Eksik age değerleri analiz edilmeli ve "
            "transformation sonrası null sayısı azaltılmalı."
        )

        validation_spec = PracticeValidationSpec(
            validation_type="null_count_reduction",
            column="age",
        )

        # --------------------------------------------------
    # DUPLICATE ANALYSIS
    # --------------------------------------------------
    elif skill_name == "duplicate_analysis":

        input_rows = [
            {
                "customer_id": 1,
                "name": "Ali",
                "city": "Den Haag",
            },
            {
                "customer_id": 2,
                "name": "Ayse",
                "city": "Rotterdam",
            },
            {
                "customer_id": 2,
                "name": "Ayse",
                "city": "Rotterdam",
            },
        ]

        challenge = PracticeChallenge(
            challenge_id=str(uuid4()),
            skill_name=skill_name,
            difficulty=difficulty,
            challenge_type="transformation",
            title="Duplicate kayıtları temizle",
            instructions=(
                "Dataset içindeki duplicate customer "
                "kayıtlarını tespit et ve tekrar eden "
                "kayıtları temizle."
            ),
            starter_code=None,
            input_rows=input_rows,
        )

        expected_outcome = (
            "Transformation sonrası duplicate row "
            "sayısı azalmalı."
        )

        validation_spec = PracticeValidationSpec(
            validation_type="duplicate_count_reduction",
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

        validation_spec = None

    # Public challenge + backend'e özel validation bilgisi.
    record = PracticeChallengeRecord(
        challenge=challenge,
        expected_outcome=expected_outcome,
        validation_spec=validation_spec,
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
       # --------------------------------------------------
    # EXACT OUTPUT VALIDATION
    # --------------------------------------------------
    #
    # Artık burada "2" gibi challenge'a özel
    # sabit bir değer yok.
    #
    # Beklenen sonuç challenge oluşturulurken
    # validation_spec içine kaydedilir.

    validation_spec = record.validation_spec

    if validation_spec is None:
        raise ValueError(
            "Practice challenge validation spec bulunamadı."
        )

    if validation_spec.validation_type == "exact_output":

        if validation_spec.expected_output is None:
            raise ValueError(
                "Exact output validation için "
                "expected_output bulunamadı."
            )

        output = (
            attempt.execution_output or ""
        ).strip()

        expected_output = (
            validation_spec.expected_output.strip()
        )

        success = (
            output == expected_output
        )

        if success:
            return PracticeAttemptValidation(
                success=True,
                feedback=(
                    "Challenge başarıyla tamamlandı."
                ),
            )

        return PracticeAttemptValidation(
            success=False,
            feedback=(
                "Kod çalıştı ancak beklenen "
                "sonuç elde edilmedi."
            ),
        )

        # --------------------------------------------------
    # NULL COUNT REDUCTION
    # --------------------------------------------------

    if (
        validation_spec.validation_type
        == "null_count_reduction"
    ):

        if validation_spec.column is None:
            raise ValueError(
                "Null count validation için column bulunamadı."
            )

        if challenge.input_rows is None:
            raise ValueError(
                "Transformation challenge input_rows bulunamadı."
            )

        if attempt.result_rows is None:
            return PracticeAttemptValidation(
                success=False,
                feedback=(
                    "Transformation sonucu gönderilmedi."
                ),
            )

        before_df = pd.DataFrame(
            challenge.input_rows
        )

        after_df = pd.DataFrame(
            attempt.result_rows
        )

        if validation_spec.column not in after_df.columns:
            return PracticeAttemptValidation(
                success=False,
                feedback=(
                    "Transformation sonucunda gerekli "
                    "kolon bulunamadı."
                ),
            )

        result = validate_missing_values_dataframes(
            before_df=before_df,
            after_df=after_df,
            column=validation_spec.column,
        )

        if result.success:
            return PracticeAttemptValidation(
                success=True,
                feedback=(
                    "Transformation başarılı: "
                    "null sayısı azaltıldı."
                ),
            )

        return PracticeAttemptValidation(
            success=False,
            feedback=(
                "Transformation tamamlandı ancak "
                "null sayısı azalmadı."
            ),
        )

        # --------------------------------------------------
    # DUPLICATE COUNT REDUCTION
    # --------------------------------------------------

    if (
        validation_spec.validation_type
        == "duplicate_count_reduction"
    ):

        if challenge.input_rows is None:
            raise ValueError(
                "Transformation challenge input_rows bulunamadı."
            )

        if attempt.result_rows is None:
            return PracticeAttemptValidation(
                success=False,
                feedback=(
                    "Transformation sonucu gönderilmedi."
                ),
            )

        before_df = pd.DataFrame(
            challenge.input_rows
        )

        after_df = pd.DataFrame(
            attempt.result_rows
        )

        result = validate_duplicate_rows_dataframes(
            before_df=before_df,
            after_df=after_df,
        )

        if result.success:
            return PracticeAttemptValidation(
                success=True,
                feedback=(
                    "Transformation başarılı: "
                    "duplicate row sayısı azaltıldı."
                ),
            )

        return PracticeAttemptValidation(
            success=False,
            feedback=(
                "Transformation tamamlandı ancak "
                "duplicate row sayısı azalmadı."
            ),
        )

    raise ValueError(
        "Bu validation türü henüz desteklenmiyor."
    )