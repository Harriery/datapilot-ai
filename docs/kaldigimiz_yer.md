DataPilot AI nedir?

DataPilot AI'ın amacı basit bir “AI'a soru sor, cevap versin” uygulaması değil.

Asıl fikir:

Junior Data Engineer gerçek Data Engineering görevleri üzerinde çalışırken, DataPilot onun seviyesini takip eder ve sadece ihtiyaç duyduğu kadar yardım eder.

Yani sistem iki parçadan oluşuyor:

Data Engineering Workflow
+
Adaptive Mentor

Bunlar birleşince ürünün farkı ortaya çıkıyor.

Normal ChatGPT yaklaşımı:

Junior soru sorar
↓
AI cevabı verir
↓
biter

DataPilot yaklaşımı:

Junior gerçek bir görev yapar
↓
DataPilot problemi tespit eder
↓
Junior'ın o konudaki geçmişini bilir
↓
Ne kadar yardıma ihtiyacı olduğunu belirler
↓
Minimum gerekli yardımı verir
↓
Junior kendisi dener
↓
DataPilot denemeyi değerlendirir
↓
Öğrenme evidence'ı kaydedilir
↓
Skill seviyesi değişir
↓
Bir sonraki yardım buna göre adapte olur

Bu, projenin ana fikri.

1. Şu ana kadar yaptığımız temel backend

Backend:

FastAPI
Python
SQLite
OpenAI API
Pydantic
Pandas
Embeddings / RAG
Pytest

kullanıyor.

Başlangıçta çok daha basit bir sistemdi:

POST /chat
↓
OpenAI
↓
reply

Sonra bunu adım adım gerçek bir uygulamaya dönüştürdük.

2. Session ve konuşma geçmişi

Kullanıcıların konuşmalarını session üzerinden saklıyoruz.

Kabaca:

session
↓
messages
↓
user message
assistant message
user message
assistant message

Mentor artık sadece son cümleye bakmak zorunda değil.

Örneğin:

Junior:
"dict nasıl oluşturuluyordu?"

Mentor:
küçük yönlendirme verir

Junior:
"şöyle mi? x = {'a': 1}"

İkinci mesaj tek başına değerlendirilmek yerine önceki konuşmayla birlikte anlaşılabiliyor.

3. Document / RAG sistemi

TXT/PDF gibi belgeleri yükleyebiliyoruz.

Akış:

Document upload
↓
text extraction
↓
chunking
↓
embedding
↓
SQLite
↓
semantic search
↓
en alakalı chunk'lar
↓
AI cevabı

Yani kullanıcı yüklediği doküman hakkında soru sorabiliyor.

Bu bölüm bize:

embeddings
chunking
vector similarity
retrieval
RAG

mantığını projeye ekledi.

4. CSV / Data Engineering workflow

Sonra projeyi asıl hedefimiz olan Data Engineering tarafına çevirdik.

Kullanıcı CSV yüklüyor:

CSV
↓
Pandas DataFrame
↓
profiling

Profil şu tip bilgiler çıkarıyor:

row_count
column_count
columns
data_types
null_counts
duplicate_count
sample_rows
numeric_columns
numeric_summary

Örneğin:

name,age,city
Ali,30,Den Haag
Ayse,,Rotterdam
Ali,30,Den Haag
Mehmet,999,Utrecht

DataPilot artık “bu dosya hakkında genel yorum” yapmak yerine önce somut profil çıkarıyor.

5. Structured Data Quality Analysis

Burada önemli bir mimari değişiklik yaptık.

AI'nın rastgele uzun metin üretmesini istemedik.

Onun yerine:

DataQualityFinding

oluşturduk.

Her problem şu yapıda:

issue_type
column
severity
observation
suggested_action

Örneğin:

{
  "issue_type": "missing_values",
  "column": "age",
  "severity": "medium",
  "observation": "age sütununda eksik değer var.",
  "suggested_action": "Eksik değerin nedenini inceleyin."
}

Bir CSV için:

DataQualityAnalysis

içinde birden fazla finding geliyor.

Örneğin:

Finding 1
→ duplicate_rows

Finding 2
→ suspicious_values / age

Finding 3
→ missing_values / age

Finding 4
→ missing_values / city

Bu önemli çünkü backend artık AI cevabını programatik olarak kullanabiliyor.

6. Adaptive Mentor sistemi

Projenin en önemli kısmı burası.

Mentor şu skill'leri takip ediyor.

Örneğin:

python_functions
debugging
pandas_dataframe
data_types
null_analysis
duplicate_analysis
schema_analysis
numeric_analysis
sql_basics
sql_joins
etl_elt
pipeline_concepts
data_modeling
testing
git_workflow
...

Her junior için her skill'in bir durumu olabilir:

new
learning
practicing
comfortable

Mesela:

learner: demo-learner
skill: null_analysis
status: learning
attempts: 2
successful_attempts: 1
7. Mentor assistance seviyeleri

Mentor herkese aynı şekilde yardım etmiyor.

Beş seviyemiz var:

NONE
NUDGE
GUIDE
TEACH
DEMONSTRATE

Mantıkları:

NONE
→ Junior zaten yapabiliyor.
→ kısa review

NUDGE
→ küçük ipucu

GUIDE
→ sadece bir sonraki küçük adım

TEACH
→ kavramı kısa öğret

DEMONSTRATE
→ gerçekten takılmışsa çalışan küçük örnek

En önemli prensip:

minimum sufficient help

Yani junior'a yapılabilecek en büyük cevabı değil, ilerlemesini sağlayacak en küçük yeterli yardımı vermeye çalışıyoruz.

8. Mentor kararı nasıl oluşuyor?

Mentor şuna bakıyor:

Learner Profile
+
Skill State
+
Previous Learning Evidence
+
Current Task / Message
↓
MentorDecision

Örneğin:

skill_name = null_analysis
assistance_level = GUIDE

Sonra GUIDE davranışı uygulanıyor.

9. Learning Evidence sistemi

Mentor sadece yardım etmiyor.

Junior'ın gerçekten ne öğrendiğini de takip ediyor.

Bir junior mesajı:

application
explanation
debugging
validation

gibi evidence olabilir.

Ayrıca:

success = True

veya:

success = False

olabiliyor.

Gerçek evidence ise DB'ye kaydediliyor.

Sonra:

attempts
successful_attempts

güncelleniyor.

Şu an kullandığımız kaba MVP kuralı:

0 attempt
→ new

1-2
→ learning

3+
→ practicing

5+ ve %80+ başarı
→ comfortable

Bu ileride daha sofistike olabilir ama MVP için yeterli.

10. Data Quality ile Mentor'u bağladık

Burada önemli bir tasarım kararı aldık.

AI'nın tekrar:

“Bu finding hangi skill?”

diye tahmin yapmasını istemedik.

Backend deterministic mapping kullanıyor:

missing_values
→ null_analysis

duplicate_rows
→ duplicate_analysis

suspicious_values
→ numeric_analysis

data_type_issue
→ data_types

schema_issue
→ schema_analysis

Bu daha güvenilir.

Örneğin:

finding.issue_type = missing_values
↓
null_analysis
↓
learner'ın null_analysis geçmişi
↓
MentorDecision
↓
GUIDE
11. /mentor/data-quality

Bu endpoint ile structured finding'i adaptif mentora gönderiyoruz.

Akış:

DataQualityFinding
↓
skill mapping
↓
learner state
↓
MentorDecision
↓
mentor response

Swagger'da bunu gerçek olarak test ettik.

İlk başta mentor gereksiz:

ETL
raw data
pipeline
source
metadata

gibi şeyler uyduruyordu.

Prompt ve mimariyi düzelterek bunu kontrol altına aldık.

12. Bugün yaptığımız en önemli yeni parça: Junior Attempt

Burada ürün bir seviye daha ileri gitti.

Eskiden:

DataPilot:
"age kolonundaki eksikliği incele."

ve akış bitiyordu.

Şimdi:

DataPilot:
"age kolonundaki eksikliği incele."

Junior:
"Önce df['age'].isna().sum() ile kaç eksik olduğunu kontrol ederim."

Artık sistem bunu değerlendirebiliyor.

Yeni akış:

finding
↓
mentor guidance
↓
JUNIOR ATTEMPT
↓
attempt evaluation
↓
learning evidence
↓
skill state update
↓
mentor next step

Bu, projenin ana learning loop'unu ciddi anlamda tamamlıyor.

13. evaluate_data_quality_attempt()

Bu fonksiyon junior'ın denemesine bakıyor.

Örneğin:

df["age"].isna().sum()

AI şuna benzer structured karar veriyor:

{
  "is_evidence": true,
  "evidence_type": "validation",
  "success": true,
  "note": "..."
}

Yani:

Bu gerçekten bir attempt mi?
↓
Evet

Ne tür?
↓
validation

Doğru mu?
↓
Evet
14. review_data_quality_attempt()

Bu fonksiyon yeni workflow'un orchestration kısmı.

Yani bütün parçaları birbirine bağlıyor:

finding
↓
skill_name
↓
mentor_decision
↓
evaluate attempt
↓
record evidence
↓
refresh skill status
↓
mentor feedback
↓
API response

Bu çok önemli bir servis fonksiyonu.

15. /mentor/data-quality/attempt

Junior'ın denemesini gönderebildiğimiz endpoint.

Request:

{
  "learner_id": "demo-learner",
  "finding": {...},
  "attempt": "Önce df['age'].isna().sum() ile..."
}

Son gerçek Swagger sonucumuz:

{
  "mentor_response": "Evet, bu doğru bir adım. Eksik age değerlerinin bulunduğu örnek satırları inceleyin.",
  "skill_name": "null_analysis",
  "skill_status": "learning",
  "evidence": {
    "is_evidence": true,
    "evidence_type": "validation",
    "success": true
  }
}

Bu tam olarak ürünün yapmak istediğimiz davranışına yaklaştı:

Junior'ın yaptığını tanı
↓
doğruysa doğrula
↓
sadece bir sonraki küçük adımı ver
16. Neden DataQualityNextStep yaptık?

Burada çok önemli bir AI engineering dersi çıktı.

Önce AI'ya:

“Kısa cevap ver, tek adım ver.”

dedik.

Ama yine:

ETL kontrol et
raw data bak
pipeline loglarına bak
şunu yap
bunu yap
kod:
...

gibi cevaplar verdi.

Sonra structured output denedik.

Ama:

structured output
≠
kontrollü içerik

olduğunu gördük.

Sonunda responsibility'yi böldük:

Backend:
"Evet, bu doğru bir adım."

AI:
sadece next_step

Yani AI'nın kontrol etmesine gerek olmayan şeyi AI'ya bırakmıyoruz.

Bu aslında çok iyi bir ürün/mimari prensibi:

Deterministik olabilecek şeyi backend yönetir; reasoning gereken şeyi AI yapar.

Şu an nerede kaldık?

Yerel kodumuzda yaklaşık şu durumdayız:

CSV profiling                     ✅
Structured data quality findings  ✅
Adaptive mentor                   ✅
Skill state                       ✅
Learning evidence                 ✅
Finding → skill mapping           ✅
Finding → mentor                  ✅
Junior attempt                    ✅
Attempt evaluation                ✅
Skill state update                ✅
Controlled next-step feedback     ✅ / yeni

Ama son yaptığımız attempt geliştirmeleri henüz final hale getirilmedi.

GitHub son durumda attempt öncesindeki mentor bağlantısını içeriyor; bugünkü yerel değişiklikleri henüz pushlamadık.

Bir sonraki oturumda ilk yapacağımız şey

Yeni feature'a hemen başlamayacağız.

Önce bugünkü bölümü sağlamlaştıracağız:

1. Debug kodu kalmış mı kontrol
2. Kullanılmayan DataQualityAttemptFeedback varsa temizle
3. generate_data_quality_attempt_response için gerçek unit test
4. route/service testleri
5. full pytest
6. Swagger final smoke test
7. commit
8. push

Son full suite daha önce:

60 passed

idi.

Daha sonraki değişikliklerde mentor_service testleri:

19 passed

oldu.

Ama en son response-control değişikliğinden sonra final full suite'i henüz tekrar çalıştırmadık. Bir sonraki sefer bunu yapacağız.

Sonra ne yapacağız?

Bundan sonraki roadmap'i bence şu sırayla yürütmeliyiz:

PHASE 1 — mevcut attempt workflow'u kapat
        ↓
PHASE 2 — transformation validation
        ↓
PHASE 3 — multi-step data task
        ↓
PHASE 4 — learner progress/profile API
        ↓
PHASE 5 — frontend
        ↓
PHASE 6 — portfolio/demo polish
Phase 2 — Transformation Validation

Şu anda junior:

df["age"].isna().sum()

gibi yaklaşım/kod öneriyor ve AI değerlendiriyor.

Ama ileride gerçekten bir dönüşüm yaptığında:

df["age"] = ...

DataPilot sadece:

“Kod iyi görünüyor.”

dememeli.

Gerçek veriyi yeniden profile edip:

Önce:
null_count = 10

Junior transformation yaptı

Sonra:
null_count = 0

gibi veri sonucunu doğrulamalı.

Bu çok daha güçlü olacak:

Junior code
↓
execute / validate
↓
before profile
vs
after profile
↓
gerçek başarı

Burada DataPilot gerçekten Data Engineering tool haline gelir.

Phase 3 — Gerçek görev döngüsü

Sonra tek bir finding yerine task kavramı getirebiliriz.

Mesela:

Task:
Clean customer dataset

Altında:

1. Missing values
2. Duplicates
3. Suspicious values
4. Data types

Junior bunları tek tek çözebilir.

DataPilot:

task progress
skill evidence
mentor guidance
validation

birlikte takip eder.

Phase 4 — Learner Progress

Şu anda veriyi DB'ye kaydediyoruz ama kullanıcıya güzel bir şekilde göstermiyoruz.

Sonra endpoint'ler:

GET /learners/{id}/skills
GET /learners/{id}/progress
GET /learners/{id}/evidence

gibi olabilir.

Örneğin:

Null Analysis
████████░░ practicing

SQL Joins
██████░░░░ learning

Data Types
██████████ comfortable

Bu, “adaptive” kısmının gözle görünür hale gelmesini sağlar.

Phase 5 — Frontend

Backend yeterince oturduktan sonra frontend.

Ekran kabaca:

┌─────────────────────────────┐
│ DataPilot AI                │
├─────────────────────────────┤
│ Upload CSV                  │
├─────────────────────────────┤
│ Data Quality Findings       │
│                             │
│ ⚠ Missing values - age     │
│ ⚠ Duplicate rows           │
│ ⚠ Suspicious value - age   │
├─────────────────────────────┤
│ Mentor                      │
│                             │
│ "Önce age kolonundaki..."   │
│                             │
│ Your attempt:               │
│ [____________________]      │
│ [Submit]                    │
├─────────────────────────────┤
│ Skill: null_analysis        │
│ Status: learning            │
└─────────────────────────────┘

Böyle olunca portfolio demosu çok daha anlaşılır hale gelir.

En sonunda ürünün anlatımı

Projeyi iş görüşmesinde yaklaşık şöyle anlatabileceksin:

DataPilot AI is an adaptive mentoring platform for junior Data Engineers. It combines real data engineering workflows with learner-state tracking. The system profiles datasets, detects structured data-quality issues, maps those issues to engineering competencies, and selects the minimum level of assistance based on the learner's profile, skill state and previous evidence. Instead of solving the task automatically, it lets the junior attempt the solution, evaluates that attempt, stores learning evidence, updates proficiency and provides the next appropriate step.

Bu noktaya geldiğimizde proje “OpenAI API kullandım” projesi olmaktan çıkıyor.

Asıl gösterdiği şeyler:

Backend architecture
Data Engineering
AI orchestration
Structured outputs
RAG
State management
Adaptive systems
Database design
Testing
Prompt engineering
AI reliability
Product thinking

Ve bundan sonra her yeni feature için şu soruyu soracağız:

Bu feature junior'ın gerçek Data Engineering işi yapmasını ve zamanla daha bağımsız hale gelmesini sağlıyor mu?

Cevap hayırsa muhtemelen gereksiz feature'dır.

Bir sonraki oturumda da yeni bir şeye atlamadan önce bugünkü local değişiklikleri test edip pushlayarak başlayacağız.