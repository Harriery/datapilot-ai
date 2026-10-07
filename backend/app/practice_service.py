from backend.app.models import (
    PracticeRecommendation,
    PracticeRecommendationResponse,
    PracticeChallenge,
    PracticeChallengeResponse,
    PracticeChallengeRecord,
    PracticeAttemptRequest,
    PracticeAttemptValidation,
    PracticeValidationSpec,
    PracticeSupportSpec,
    PracticeHintResponse,
    PracticeSolutionResponse,
)
import backend.app.database as database
from uuid import uuid4
from backend.app.progress_service import (
    build_misconception_counts,
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
        "context_code": (
            "records = [\n"
            "    {'name': 'Ali', 'city': 'Den Haag'},\n"
            "    {'name': 'Ayse', 'city': None},\n"
            "    {'name': 'Mehmet', 'city': 'Utrecht'},\n"
            "    {'name': 'Zeynep', 'city': None},\n"
            "]\n"
        ),
        "expected_output": "2",
        "hints": [
            (
                "Her kaydın city değerini tek tek "
                "kontrol etmeyi düşün."
            ),
            (
                "city değeri None olan kayıtları "
                "sayman gerekiyor."
            ),
            (
                "Bir count değişkeni, for döngüsü ve "
                "if record['city'] is None koşulunu "
                "kullanabilirsin."
            ),
        ],
        "solution": (
            "count = 0\n"
            "\n"
            "for record in records:\n"
            "    if record['city'] is None:\n"
            "        count += 1\n"
            "\n"
            "print(count)\n"
        ),
    },
    {
        "title": "Aktif kullanıcıları say",
        "instructions": (
            "Aşağıdaki users listesinde active değeri "
            "True olan kullanıcıların sayısını hesapla ve "
            "sonucu print ile ekrana yazdır."
        ),
        "context_code": (
            "users = [\n"
            "    {'name': 'Sara', 'active': True},\n"
            "    {'name': 'Tom', 'active': False},\n"
            "    {'name': 'Lina', 'active': True},\n"
            "    {'name': 'Sam', 'active': True},\n"
            "]\n"
        ),
        "expected_output": "3",
        "hints": [
            (
                "Her kullanıcının active değerini "
                "kontrol etmeyi düşün."
            ),
            (
                "Sadece active değeri True olan "
                "kullanıcıları saymalısın."
            ),
            (
                "Bir count değişkeni, for döngüsü ve "
                "if user['active'] koşulunu "
                "kullanabilirsin."
            ),
        ],
        "solution": (
            "count = 0\n"
            "\n"
            "for user in users:\n"
            "    if user['active']:\n"
            "        count += 1\n"
            "\n"
            "print(count)\n"
        ),
    },
    {
        "title": "Yüksek skorları say",
        "instructions": (
            "Aşağıdaki results listesinde score değeri "
            "70 veya daha yüksek olan kayıtların sayısını "
            "hesapla ve sonucu print ile ekrana yazdır."
        ),
        "context_code": (
            "results = [\n"
            "    {'name': 'A', 'score': 55},\n"
            "    {'name': 'B', 'score': 72},\n"
            "    {'name': 'C', 'score': 91},\n"
            "    {'name': 'D', 'score': 64},\n"
            "]\n"
        ),
        "expected_output": "2",
        "hints": [
            (
                "Her kaydın score değerini "
                "kontrol etmeyi düşün."
            ),
            (
                "score değeri 70 veya daha yüksek "
                "olan kayıtları saymalısın."
            ),
            (
                "Bir count değişkeni, for döngüsü ve "
                "if result['score'] >= 70 koşulunu "
                "kullanabilirsin."
            ),
        ],
        "solution": (
            "count = 0\n"
            "\n"
            "for result in results:\n"
            "    if result['score'] >= 70:\n"
            "        count += 1\n"
            "\n"
            "print(count)\n"
        ),
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

    if selected_skill.misconceptions:
        reason += (
            " Tekrarlayan/gözlenen açıklar: "
            + ", ".join(
                selected_skill.misconceptions[:3]
            )
            + "."
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

def get_practice_focus_misconception(
    *,
    learner_id: str,
    skill_name: str,
) -> str | None:
    evidence = database.get_learning_evidence_by_skill(
        learner_id=learner_id,
        skill_name=skill_name,
    )
    counts = build_misconception_counts(evidence)
    if not counts:
        return None
    return max(
        counts,
        key=lambda code: (counts[code], code),
    )


def get_reasoning_practice_variant(
    *,
    skill_name: str,
    misconceptions: set[str],
) -> dict | None:

    if skill_name == "data_modeling":
        if "relationship_cardinality_confusion" in misconceptions:
            return {
                "title": "İlişki cardinality'sini seç",
                "instructions": (
                    "fact_sales tablosunda aynı product_id birçok satırda bulunuyor. "
                    "dim_product tablosunda her product_id yalnız bir kez bulunuyor. "
                    "fact_sales -> dim_product ilişkisi için doğru cardinality hangisi?"
                ),
                "options": ["many_to_one", "one_to_many", "one_to_one"],
                "answer": "many_to_one",
                "hints": [
                    "Her iki tarafta aynı key'in kaç kez tekrar ettiğini düşün.",
                    "Fact tarafında product_id çok kez, dimension tarafında bir kez bulunuyor.",
                ],
            }

        return {
            "title": "Fact grain'i belirle",
            "instructions": (
                "Bir satış tablosunda her satır tek bir ürünün tek bir sipariş "
                "satırını temsil ediyor. Modellemeye başlamadan önce doğru fact grain hangisi?"
            ),
            "options": [
                "Bir satır = bir sipariş",
                "Bir satır = bir sipariş satırı",
                "Bir satır = bir müşteri",
            ],
            "answer": "Bir satır = bir sipariş satırı",
            "hints": [
                "Grain, fact tablosundaki tek satırın neyi temsil ettiğini söyler.",
                "Soruda her satırın tek bir ürün-sipariş satırı olduğu belirtiliyor.",
            ],
        }

    if skill_name == "semantic_modeling":
        return {
            "title": "Semantic model readiness kontrolü",
            "instructions": (
                "Fact ile dimension arasında ilişki kurulmuş fakat dimension key "
                "benzersiz değil. Analysis aşamasına geçmeden önce ne yapmalısın?"
            ),
            "options": [
                "Modeli onayla ve Analysis'e geç",
                "Dimension key benzersizliğini düzelt/doğrula",
                "İlişkiyi kaldırıp tüm kolonları fact'e taşı",
            ],
            "answer": "Dimension key benzersizliğini düzelt/doğrula",
            "hints": [
                "many-to-one ilişkinin 'one' tarafında key benzersiz olmalıdır.",
                "Semantic readiness, ilişki mantığının güvenilir olmasını gerektirir.",
            ],
        }

    if skill_name == "kpi_design":
        if "non_additive_measure_sum" in misconceptions:
            return {
                "title": "Non-additive KPI aggregation",
                "instructions": (
                    "Her satırda zaten hesaplanmış bir yüzde oranı var. "
                    "Bu oranları toplam KPI olarak SUM yapmak güvenilir mi?"
                ),
                "options": [
                    "Evet, yüzdeler her zaman SUM edilir",
                    "Hayır, önce oranın grain ve pay/payda mantığını kontrol et",
                    "Evet, ama yalnız Top 10 kullanılırsa",
                ],
                "answer": "Hayır, önce oranın grain ve pay/payda mantığını kontrol et",
                "hints": [
                    "Her measure additive değildir.",
                    "Oranlarda pay ve payda yeniden aggregate edilmeden SUM yanıltıcı olabilir.",
                ],
            }

        return {
            "title": "KPI aggregation seç",
            "instructions": (
                "Her satır bir satış işlemi ve revenue işlemin parasal tutarı. "
                "Toplam gelir KPI'sı için hangi aggregation uygundur?"
            ),
            "options": ["SUM", "MEAN", "COUNT"],
            "answer": "SUM",
            "hints": [
                "Measure'ın satır grain'inde ne ifade ettiğini düşün.",
                "İşlem tutarları additive ise toplam gelir için birleştirilebilir.",
            ],
        }

    if skill_name == "data_analysis":
        return {
            "title": "Analiz tanımını doğru kur",
            "instructions": (
                "'Hangi bölgenin ortalama sipariş değeri en yüksek?' sorusunu "
                "cevaplamak için doğru tanım hangisi?"
            ),
            "options": [
                "COUNT(order_id) + region",
                "MEAN(order_value) + region",
                "SUM(order_value) + customer_id",
            ],
            "answer": "MEAN(order_value) + region",
            "hints": [
                "Sorudaki metrik 'ortalama sipariş değeri'.",
                "Karşılaştırma boyutu bölge olduğu için dimension region olmalı.",
            ],
        }

    if skill_name == "dashboard_design":
        return {
            "title": "Doğru visual seç",
            "instructions": (
                "Aylara göre gelir trendini ve zaman içindeki yükseliş/düşüşü "
                "göstermek istiyorsun. En uygun temel visual hangisi?"
            ),
            "options": ["Line chart", "Pie chart", "KPI card"],
            "answer": "Line chart",
            "hints": [
                "Zaman sıralı değişim için sürekliliği gösteren visual düşün.",
                "Pie chart parça-bütün; KPI card tek değer içindir.",
            ],
        }

    if skill_name == "data_interpretation":
        return {
            "title": "Insight'ta nedensellik hatasını önle",
            "instructions": (
                "İki değişken birlikte yükseliyor fakat deneysel veya nedensel "
                "kanıt yok. Hangi insight daha güvenilir?"
            ),
            "options": [
                "A değişkeni kesin olarak B'ye neden oluyor",
                "A ve B arasında birlikte hareket eden bir ilişki gözleniyor; nedensellik kanıtlanmadı",
                "Bütün satırlar hatalıdır",
            ],
            "answer": (
                "A ve B arasında birlikte hareket eden bir ilişki gözleniyor; "
                "nedensellik kanıtlanmadı"
            ),
            "hints": [
                "Correlation tek başına causation değildir.",
                "Insight, kanıtın desteklediğinden daha güçlü iddia etmemeli.",
            ],
        }

    if skill_name == "technical_documentation":
        return {
            "title": "Handoff dokümantasyonunu tamamla",
            "instructions": (
                "Bir cleaning kararını dokümante ederken hangisi en güçlü kayıt olur?"
            ),
            "options": [
                "Sadece 'veri temizlendi' yazmak",
                "Karar + neden + before/after validation sonucu + limitation yazmak",
                "Yalnız kullanılan Python kodunu yapıştırmak",
            ],
            "answer": "Karar + neden + before/after validation sonucu + limitation yazmak",
            "hints": [
                "Handoff başka bir kişinin kararı doğrulayabilmesini sağlamalı.",
                "Kod tek başına gerekçeyi ve validation'ı açıklamaz.",
            ],
        }

    if skill_name == "data_validation":
        return {
            "title": "Validation kanıtını seç",
            "instructions": (
                "Null sayısı 20'den 0'a düştü ama row count da beklenmedik şekilde "
                "1000'den 800'e düştü. Validation sonucu ne olmalı?"
            ),
            "options": [
                "Passed; null sayısı 0 oldu",
                "Başarılı sayma; beklenmedik row loss'u araştır",
                "Schema değişmediyse otomatik passed",
            ],
            "answer": "Başarılı sayma; beklenmedik row loss'u araştır",
            "hints": [
                "Tek bir metriğin düzelmesi güvenli transformation kanıtı değildir.",
                "Unexpected row loss önce açıklanmalıdır.",
            ],
        }

    return None


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
    focus_misconception = get_practice_focus_misconception(
        learner_id=learner_id,
        skill_name=skill_name,
    )

    learner_progress = get_learner_progress(
        learner_id=learner_id
    )
    selected_progress = next(
        (
            item
            for item in learner_progress.skills
            if item.skill_name == skill_name
        ),
        None,
    )
    misconceptions = set(
        selected_progress.misconceptions
        if selected_progress is not None
        else []
    )

    # Her challenge'ın support sistemi olmak zorunda değil.
    # Destek tanımlanan challenge'larda aşağıda dolduracağız.
    support_spec = None

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

            # Sistem tarafından verilen read-only data.
            context_code=variant["context_code"],

            # Junior'ın kendi çözümünü yazacağı alan.
            starter_code="",
        )

        expected_outcome = (
            f"Beklenen çıktı: "
            f"{variant['expected_output']}"
        )

        validation_spec = PracticeValidationSpec(
            validation_type="exact_output",
            expected_output=variant["expected_output"],
        )

        support_spec = PracticeSupportSpec(
            hints=variant["hints"],
            solution=variant["solution"],
        )
       # --------------------------------------------------
    # DEBUGGING
    # --------------------------------------------------
    elif skill_name == "debugging":

        challenge = PracticeChallenge(
            challenge_id=str(uuid4()),
            skill_name=skill_name,
            difficulty=difficulty,
            challenge_type="code",
            title="Hatalı pandas ifadesini düzelt",
            instructions=(
                "Aşağıdaki kod çalışmıyor. Hatanın nedenini bul, "
                "sonra eksik age değerlerinin sayısını yazdıracak "
                "şekilde yalnız hatalı ifadeyi düzelt."
            ),
            context_code=(
                "import pandas as pd\n"
                "df = pd.DataFrame({\n"
                "    'age': [30, None, 41, None]\n"
                "})\n"
            ),
            starter_code=(
                "print(df['age'.isna()].sum())"
            ),
        )

        expected_outcome = "2"

        validation_spec = PracticeValidationSpec(
            validation_type="exact_output",
            expected_output="2",
        )

        support_spec = PracticeSupportSpec(
            hints=[
                (
                    "isna() string metodu değil; önce DataFrame'den "
                    "kolonu seçtiğinden emin ol."
                ),
                (
                    "Önce df['age'] ifadesini oluştur, sonra "
                    ".isna() ve .sum() zincirini uygula."
                ),
            ],
            solution=(
                "print(df['age'].isna().sum())"
            ),
        )

       # --------------------------------------------------
    # NULL ANALYSIS
    # --------------------------------------------------
    elif skill_name == "null_analysis":

        if focus_misconception == "filter_scope_confusion":
            challenge = PracticeChallenge(
                challenge_id=str(uuid4()),
                skill_name=skill_name,
                difficulty=difficulty,
                challenge_type="code",
                title="Eksik satır kapsamını doğru kur",
                instructions=(
                    "Önce age değeri eksik olan kayıtları dikkate al. "
                    "Yalnızca bu kayıtların içinde city değeri Rotterdam "
                    "olan kaç kayıt bulunduğunu print ile yazdır. "
                    "Tüm dataset üzerinde sayım yapma."
                ),
                context_code=(
                    "records = [\n"
                    "    {'id': 1, 'age': 31, 'city': 'Rotterdam'},\n"
                    "    {'id': 2, 'age': None, 'city': 'Rotterdam'},\n"
                    "    {'id': 3, 'age': None, 'city': 'Den Haag'},\n"
                    "    {'id': 4, 'age': None, 'city': 'Rotterdam'},\n"
                    "    {'id': 5, 'age': 27, 'city': 'Rotterdam'},\n"
                    "]\n"
                ),
                starter_code="",
            )
            expected_outcome = "Beklenen çıktı: 2"
            validation_spec = PracticeValidationSpec(
                validation_type="exact_output",
                expected_output="2",
            )
            support_spec = PracticeSupportSpec(
                hints=[
                    "İlk koşul age değerinin None olması.",
                    "city kontrolünü yalnızca eksik-age kayıtlarında yap.",
                    "İki koşulu aynı record üzerinde birlikte kontrol edebilirsin.",
                ],
                solution=(
                    "count = 0\n"
                    "for record in records:\n"
                    "    if record['age'] is None and record['city'] == 'Rotterdam':\n"
                    "        count += 1\n"
                    "print(count)\n"
                ),
            )

        elif focus_misconception == "dataset_context_confusion":
            challenge = PracticeChallenge(
                challenge_id=str(uuid4()),
                skill_name=skill_name,
                difficulty=difficulty,
                challenge_type="code",
                title="Raw ve working dataset bağlamını ayır",
                instructions=(
                    "Amaç orijinal eksik age kayıtlarını incelemek. "
                    "raw_records ve working_records verildi. Doğru veri "
                    "kaynağını seçip orijinal eksik age kayıtlarının "
                    "sayısını print et."
                ),
                context_code=(
                    "raw_records = [\n"
                    "    {'id': 1, 'age': 31},\n"
                    "    {'id': 2, 'age': None},\n"
                    "    {'id': 3, 'age': None},\n"
                    "]\n"
                    "working_records = [\n"
                    "    {'id': 1, 'age': 31},\n"
                    "    {'id': 2, 'age': 29},\n"
                    "    {'id': 3, 'age': 29},\n"
                    "]\n"
                ),
                starter_code="",
            )
            expected_outcome = "Beklenen çıktı: 2"
            validation_spec = PracticeValidationSpec(
                validation_type="exact_output",
                expected_output="2",
            )
            support_spec = PracticeSupportSpec(
                hints=[
                    "Soru orijinal eksikliği araştırıyor.",
                    "Working dataset temizlenmiş olabilir.",
                    "Raw kayıtlar içinde age is None koşulunu say.",
                ],
                solution=(
                    "print(sum(1 for record in raw_records "
                    "if record['age'] is None))\n"
                ),
            )

        elif focus_misconception == "premature_transformation":
            challenge = PracticeChallenge(
                challenge_id=str(uuid4()),
                skill_name=skill_name,
                difficulty=difficulty,
                challenge_type="code",
                title="Dönüşümden önce kanıt topla",
                instructions=(
                    "Bu görevde hiçbir age değerini doldurma veya silme. "
                    "Sadece eksik age değerlerinin sayısını inceleme "
                    "amacıyla print et."
                ),
                context_code=(
                    "records = [\n"
                    "    {'id': 1, 'age': None},\n"
                    "    {'id': 2, 'age': 40},\n"
                    "    {'id': 3, 'age': None},\n"
                    "]\n"
                ),
                starter_code="",
            )
            expected_outcome = "Beklenen çıktı: 2"
            validation_spec = PracticeValidationSpec(
                validation_type="exact_output",
                expected_output="2",
            )
            support_spec = PracticeSupportSpec(
                hints=[
                    "Bu turdaki hedef yalnızca gözlem.",
                    "Veriyi değiştirmeden age is None kayıtlarını say.",
                ],
                solution=(
                    "print(sum(1 for record in records "
                    "if record['age'] is None))\n"
                ),
            )

        else:
            input_rows = [
                {"customer_id": 1, "name": "Ali", "age": 30},
                {"customer_id": 2, "name": "Ayse", "age": None},
                {"customer_id": 3, "name": "Mehmet", "age": None},
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
    # TARGETED STAGE REASONING
    # --------------------------------------------------
    elif skill_name in {
        "data_modeling",
        "semantic_modeling",
        "kpi_design",
        "data_analysis",
        "dashboard_design",
        "data_interpretation",
        "technical_documentation",
        "data_validation",
    }:

        variant = get_reasoning_practice_variant(
            skill_name=skill_name,
            misconceptions=misconceptions,
        )

        if variant is None:
            raise ValueError(
                "Targeted reasoning practice variant bulunamadı."
            )

        challenge = PracticeChallenge(
            challenge_id=str(uuid4()),
            skill_name=skill_name,
            difficulty=difficulty,
            challenge_type="multiple_choice",
            title=variant["title"],
            instructions=variant["instructions"],
            starter_code=None,
            options=variant["options"],
        )

        expected_outcome = (
            "Doğru reasoning seçeneğini evidence'e göre seç."
        )

        validation_spec = PracticeValidationSpec(
            validation_type="exact_answer",
            expected_answer=variant["answer"],
        )

        support_spec = PracticeSupportSpec(
            hints=variant["hints"],
            solution=variant["answer"],
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
        support_spec=support_spec,
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
    # EXACT ANSWER VALIDATION
    # --------------------------------------------------
    if (
        validation_spec.validation_type
        == "exact_answer"
    ):
        if validation_spec.expected_answer is None:
            raise ValueError(
                "Exact answer validation için "
                "expected_answer bulunamadı."
            )

        answer = (
            attempt.answer or ""
        ).strip()

        expected_answer = (
            validation_spec.expected_answer
            .strip()
        )

        success = (
            answer == expected_answer
        )

        return PracticeAttemptValidation(
            success=success,
            feedback=(
                "Correct answer."
                if success
                else "That answer is not correct."
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

def get_next_practice_hint(
    learner_id: str,
    challenge_id: str,
) -> PracticeHintResponse:
    """
    Junior için sıradaki practice hint'ini döndürür.

    Hint'ler sırayla açılır:
    1 -> NUDGE
    2 -> GUIDE
    3 -> TEACH

    Bütün hint'ler kullanıldıktan sonra
    solution_available = True olur.

    Bu fonksiyon OpenAI kullanmaz.
    """

    record = database.get_practice_challenge(
        challenge_id=challenge_id,
        learner_id=learner_id,
    )

    if record is None:
        raise ValueError("Practice challenge bulunamadı.")

    support_spec = record.support_spec

    if support_spec is None or not support_spec.hints:
        return PracticeHintResponse(
            challenge_id=challenge_id,
            hint=None,
            hint_number=0,
            total_hints=0,
            assistance_level=None,
            solution_available=False,
        )

    current_hint_level = database.get_practice_hint_level(
        challenge_id=challenge_id,
        learner_id=learner_id,
    )

    total_hints = len(support_spec.hints)

    # Bütün hint'ler daha önce açılmış.
    if current_hint_level >= total_hints:
        return PracticeHintResponse(
            challenge_id=challenge_id,
            hint=None,
            hint_number=current_hint_level,
            total_hints=total_hints,
            assistance_level=None,
            solution_available=(
                support_spec.solution is not None
            ),
        )

    next_hint_number = current_hint_level + 1

    hint = support_spec.hints[current_hint_level]

    assistance_levels = {
        1: "NUDGE",
        2: "GUIDE",
        3: "TEACH",
    }

    assistance_level = assistance_levels.get(
        next_hint_number,
        "TEACH",
    )

    database.update_practice_hint_level(
        challenge_id=challenge_id,
        learner_id=learner_id,
        hint_level=next_hint_number,
    )

    return PracticeHintResponse(
        challenge_id=challenge_id,
        hint=hint,
        hint_number=next_hint_number,
        total_hints=total_hints,
        assistance_level=assistance_level,
        solution_available=(
            next_hint_number >= total_hints
            and support_spec.solution is not None
        ),
    )

def get_practice_solution(
    learner_id: str,
    challenge_id: str,
) -> PracticeSolutionResponse:
    """
    Full solution yalnızca bütün hint'ler
    açıldıktan sonra gösterilir.

    Solution gösterildiğinde learner artık
    bu challenge'ı bağımsız çözmüş sayılmaz.
    """

    record = database.get_practice_challenge(
        challenge_id=challenge_id,
        learner_id=learner_id,
    )

    if record is None:
        raise ValueError("Practice challenge bulunamadı.")

    support_spec = record.support_spec

    if (
        support_spec is None
        or support_spec.solution is None
    ):
        raise ValueError(
            "Bu challenge için çözüm bulunamadı."
        )

    current_hint_level = (
        database.get_practice_hint_level(
            challenge_id=challenge_id,
            learner_id=learner_id,
        )
    )

    total_hints = len(support_spec.hints)

    if current_hint_level < total_hints:
        raise PermissionError(
            "Tam çözüm henüz kullanılamıyor."
        )

    database.mark_practice_solution_shown(
        challenge_id=challenge_id,
        learner_id=learner_id,
    )

    return PracticeSolutionResponse(
        challenge_id=challenge_id,
        solution=support_spec.solution,
        assistance_level="DEMONSTRATE",
    )