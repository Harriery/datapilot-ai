# DataPilot AI — Kaldığımız Yer

Son güncelleme: 12 Eylül 2026

---

# 1. DataPilot AI nedir?

DataPilot AI basit bir:

> "AI'a soru sor → cevap al"

uygulaması değildir.

Projenin ana fikri:

> Junior Data Engineer gerçek görevler üzerinde çalışırken, sistem onun hangi becerilerde ne kadar bağımsız olduğunu takip eder ve sadece ihtiyaç duyduğu kadar yardım eder.

Ana ürün prensibi:

**AI junior'ın işini onun yerine yapmamalı. Junior'ın işi zamanla kendi başına yapabilmesini sağlamalı.**

Sistem iki ana parçadan oluşuyor:

```text
Data Engineering Workflow
+
Adaptive Mentor
```

Normal chatbot yaklaşımı:

```text
Junior soru sorar
↓
AI cevap verir
↓
biter
```

DataPilot yaklaşımı:

```text
Junior gerçek görev yapar
↓
DataPilot problemi tanır
↓
İlgili skill'i belirler
↓
Junior'ın o skill'deki geçmişine bakar
↓
Ne kadar yardım gerektiğini belirler
↓
Minimum gerekli yardımı verir
↓
Junior kendisi dener
↓
Attempt deterministik / AI destekli değerlendirilir
↓
Learning evidence kaydedilir
↓
Skill progress güncellenir
↓
Bir sonraki görev ve yardım buna göre adapte olur
```

---

# 2. Kullanılan teknoloji

Backend tarafında şu anda:

- FastAPI
- Python
- Pydantic
- SQLite
- Pandas
- OpenAI API
- Embeddings / RAG
- Pytest

kullanılıyor.

Frontend henüz başlamadı.

---

# 3. İlk backend

Proje başlangıçta basit bir yapıdaydı:

```text
POST /chat
↓
OpenAI
↓
reply
```

Daha sonra session, RAG, data profiling, adaptive mentor, progress ve practice sistemleri eklenerek gerçek bir ürün mimarisine dönüştürüldü.

---

# 4. Session ve konuşma geçmişi

Kullanıcının konuşmaları session altında saklanabiliyor.

Kabaca:

```text
session
↓
messages
↓
user
assistant
user
assistant
```

Böylece mentor yalnızca son mesaja bakmak yerine konuşmanın bağlamını kullanabiliyor.

---

# 5. Document / RAG sistemi

TXT / PDF gibi belgeler sisteme yüklenebiliyor.

Akış:

```text
document
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
relevant chunks
↓
AI response
```

Bu bölümde:

- chunking
- embeddings
- vector similarity
- retrieval
- RAG

mantıkları projeye eklendi.

---

# 6. CSV / Data Engineering workflow

Kullanıcı CSV yüklediğinde Pandas ile dataset profile çıkarılıyor.

Örnek bilgiler:

```text
row_count
column_count
columns
data_types
null_counts
duplicate_count
sample_rows
numeric_columns
numeric_summary
```

Örnek:

```text
name,age,city
Ali,30,Den Haag
Ayse,,Rotterdam
Ali,30,Den Haag
Mehmet,999,Utrecht
```

DataPilot dataset hakkında rastgele yorum yapmak yerine önce gerçek veriyi profilliyor.

---

# 7. Structured Data Quality Analysis

AI'nın yalnızca uzun bir metin üretmesi yerine structured modeller kullanıyoruz.

Temel model:

```text
DataQualityFinding
```

Alanları:

```text
issue_type
column
severity
observation
suggested_action
```

Örnek:

```json
{
  "issue_type": "missing_values",
  "column": "age",
  "severity": "medium",
  "observation": "age sütununda eksik değer var.",
  "suggested_action": "Eksik değerin nedenini inceleyin."
}
```

Bir dataset içinde birden fazla finding olabilir:

```text
duplicate_rows
missing_values
suspicious_values
data_type_issue
schema_issue
```

Böylece backend AI çıktısını programatik olarak kullanabiliyor.

---

# 8. Deterministic finding → skill mapping

AI'nın her seferinde:

> "Bu finding hangi skill?"

diye tahmin yapmasına izin vermiyoruz.

Backend deterministic mapping kullanıyor.

Örnek:

```text
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
```

Prensip:

> Deterministik yapılabilecek işi AI'ya bırakma.

---

# 9. Adaptive Mentor

Mentor junior'ın becerilerini skill bazında takip ediyor.

Örnek skill'ler:

```text
python_data_structures
python_functions
debugging
pandas_dataframe

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
```

Bu skill catalog gelecekte genişletilecek.

---

# 10. Skill durumları

Bir junior için her skill şu statülerden birinde olabilir:

```text
new
learning
practicing
comfortable
```

MVP kuralımız:

```text
0 attempt
→ new

1–2 attempts
→ learning

3+ attempts
→ practicing

5+ attempts
ve success rate >= %80
→ comfortable
```

Bu ileride daha gelişmiş bir mastery modeliyle değiştirilebilir.

---

# 11. Mentor assistance seviyeleri

Mentor herkese aynı miktarda yardım vermiyor.

Beş assistance seviyesi var:

```text
NONE
NUDGE
GUIDE
TEACH
DEMONSTRATE
```

Mantıkları:

```text
NONE
→ Junior bağımsız ilerleyebilir.

NUDGE
→ Küçük ipucu.

GUIDE
→ Bir sonraki küçük adımı göster.

TEACH
→ Kavramı kısa şekilde öğret.

DEMONSTRATE
→ Junior gerçekten takılmışsa küçük çalışan örnek göster.
```

Ana prensip:

**minimum sufficient help**

Yani mümkün olan en büyük cevabı değil, junior'ın devam etmesini sağlayacak en küçük yeterli yardımı veriyoruz.

---

# 12. Learning Evidence

Junior'ın yaptığı her şey doğrudan progress sayılmıyor.

Gerçek öğrenme kanıtlarını:

```text
application
explanation
debugging
validation
```

gibi evidence türleriyle kaydediyoruz.

Evidence:

```text
success = True
```

veya:

```text
success = False
```

olabilir.

Gerçek learning evidence kaydedildiğinde:

```text
attempts
successful_attempts
skill status
```

güncelleniyor.

---

# 13. Deterministic Transformation Validation

Bu bölüm tamamlandı.

Amaç:

Junior bir transformation yaptığında sadece:

> "Kod mantıklı görünüyor."

dememek.

Gerçek dataset sonucunu kontrol etmek.

Örnek:

```text
BEFORE
age null_count = 3

Junior transformation

AFTER
age null_count = 1

1 < 3
→ success = True
```

Mevcut validation'lar:

```text
validate_missing_values_transformation()
validate_missing_values_dataframes()

validate_duplicate_rows_transformation()
validate_duplicate_rows_dataframes()
```

Ayrıca finding'e göre doğru validator'ı seçen orchestration da mevcut.

---

# 14. Multi-Step Data Engineering Tasks

Junior'a tek mesajlık görev yerine çok adımlı Data Engineering task verilebiliyor.

Örnek:

```text
Task
├─ Step 1: missing values
├─ Step 2: duplicate rows
└─ Step 3: başka quality problemi
```

Step durumları:

```text
pending
active
completed
```

Bir step başarıyla tamamlandığında bir sonraki step aktif hale geliyor.

Bu yapı gerçek Data Engineering workflow'una daha yakın bir deneyim sağlıyor.

---

# 15. Learner Progress API

Junior'ın skill bazlı gelişimi artık API üzerinden görülebiliyor.

Örnek bilgiler:

```text
skill_name
status
attempts
successful_attempts
success_rate
last_assistance_level
independence_trend
practice_priority
```

Örnek:

```json
{
  "skill_name": "python_data_structures",
  "status": "practicing",
  "attempts": 3,
  "successful_attempts": 3,
  "success_rate": 1.0,
  "last_assistance_level": "NONE",
  "independence_trend": "improving",
  "practice_priority": "low"
}
```

---

# 16. Independence Trend

Sadece doğru / yanlış sonucuna bakmıyoruz.

Junior'ın ne kadar yardımla başardığını da takip ediyoruz.

Assistance independence score:

```text
DEMONSTRATE = 0
TEACH       = 1
GUIDE       = 2
NUDGE       = 3
NONE        = 4
```

Böylece:

```text
TEACH → GUIDE → NUDGE → NONE
```

gibi bir gelişim:

```text
independence_trend = improving
```

olarak değerlendirilebiliyor.

Önemli semantik:

Practice attempt evidence'ında kullanılan assistance level, attempt'ten SONRA verilen yardım değil, attempt'ten ÖNCE junior'ın sahip olduğu destek seviyesidir.

Bu şekilde independence ölçümü nedensel olarak doğru kalır.

---

# 17. Practice Recommendation

Progress sisteminin üstüne adaptive practice recommendation sistemi kuruldu.

Akış:

```text
learner progress
↓
practice priority
↓
en önemli skill
↓
difficulty
↓
practice recommendation
```

Difficulty:

```text
new
→ foundation

learning
→ easy

practicing
→ medium

comfortable
→ hard
```

Practice priority genel olarak:

```text
new
→ high

learning
→ high / medium

practicing
→ medium / low

comfortable
→ none
```

Success rate ve independence trend de karara etki ediyor.

---

# 18. Practice Challenge

Recommendation'a göre junior için gerçek challenge oluşturulabiliyor.

Challenge modelinde:

```text
challenge_id
skill_name
difficulty
challenge_type
title
instructions
starter_code
input_rows
```

bulunuyor.

Challenge type örnekleri:

```text
code
debug
output_prediction
sql
data_investigation
transformation
validation
explain
```

---

# 19. Public challenge / private validation ayrımı

Junior'a validation cevabını göstermiyoruz.

İç yapıda:

```text
PracticeChallengeRecord
```

şunları tutuyor:

```text
public challenge
+
validation_spec
+
legacy expected_outcome
```

API junior'a yalnızca public challenge döndürüyor.

Bu şekilde doğru cevap backend tarafında kalıyor.

---

# 20. Structured Practice Validation

Practice challenge validation sistemi artık structured hale getirildi.

Model:

```text
PracticeValidationSpec
```

Şu validation tiplerini destekliyor:

```text
exact_output
null_count_reduction
duplicate_count_reduction
```

Örnek:

```json
{
  "validation_type": "exact_output",
  "expected_output": "3"
}
```

Bu sayede validator artık şöyle sabit kod kullanmıyor:

```python
output == "2"
```

Onun yerine:

```text
challenge
↓
validation_spec
↓
expected_output
↓
deterministic validation
```

çalışıyor.

---

# 21. Challenge Variation

Demo için `python_data_structures` skill'inde kontrollü challenge variation sistemi var.

Şu anda 3 varyant mevcut:

```text
1. Eksik city değerlerini bul
2. Aktif kullanıcıları say
3. Yüksek skorları say
```

Bunlar aynı temel skill'i farklı veri ve koşullarla ölçüyor.

Örneğin:

```text
iteration
dictionary access
conditional logic
counting
output
```

Sistem learner + skill için daha önce kaç challenge oluşturulduğuna bakıyor.

```text
count = 0
→ variant 1

count = 1
→ variant 2

count = 2
→ variant 3

count = 3
→ variant 1
```

Demo için bu yeterli.

Gelecekte:

- daha fazla template
- difficulty'ye göre farklı template
- farklı dataset
- farklı kolon
- farklı threshold
- SQL variation
- Data Engineering scenario variation

eklenecek.

Ama Phase 5 demo scope'unda mevcut yapı yeterli kabul edildi.

---

# 22. Transformation Practice Challenge

Practice sistemi yalnızca kod çıktısı kontrol etmiyor.

Transformation challenge'larda challenge:

```text
input_rows
```

gönderiyor.

Junior transformation yaptıktan sonra:

```text
result_rows
```

gönderiyor.

Akış:

```text
challenge.input_rows
↓
junior transformation
↓
attempt.result_rows
↓
backend before / after karşılaştırması
↓
deterministic validation
```

Junior'ın `before_rows` göndermesine izin vermiyoruz.

Başlangıç dataset'i backend'in challenge kaydından geliyor.

Bu önemli çünkü learner başlangıç datasını değiştirerek validator'ı kandıramıyor.

---

# 23. Null Count Reduction Practice Validation

`null_analysis` practice challenge artık gerçek dataset üzerinden çalışıyor.

Örnek:

```text
INPUT:

Ali    30
Ayse   None
Mehmet None
```

Junior transformation:

```text
Ali    30
Ayse   25
Mehmet None
```

Backend:

```text
before null_count = 2
after null_count  = 1

1 < 2
→ success = True
```

Validation type:

```text
null_count_reduction
```

---

# 24. Duplicate Count Reduction Practice Validation

`duplicate_analysis` practice challenge da gerçek dataset üzerinden çalışıyor.

Örnek input:

```text
1 | Ali  | Den Haag
2 | Ayse | Rotterdam
2 | Ayse | Rotterdam
```

Junior output:

```text
1 | Ali  | Den Haag
2 | Ayse | Rotterdam
```

Backend:

```text
before duplicate_count = 1
after duplicate_count  = 0

0 < 1
→ success = True
```

Validation type:

```text
duplicate_count_reduction
```

---

# 25. Practice Attempt

Junior challenge için attempt gönderebiliyor.

PracticeAttemptRequest içinde:

```text
learner_id
challenge_id
answer
execution_output
execution_error
result_rows
```

bulunuyor.

Code challenge:

```text
frontend çalıştırır
↓
execution_output backend'e gelir
↓
backend expected_output ile karşılaştırır
```

Transformation challenge:

```text
result_rows gelir
↓
input_rows ile karşılaştırılır
↓
dataset gerçekten iyileşti mi?
```

Backend V1'de arbitrary learner Python kodunu çalıştırmıyor.

Frontend aşamasında Python execution için Pyodide düşünülüyor.

---

# 26. Practice Attempt → Learning Evidence → Progress

Bu bağlantı tamamlandı.

Practice attempt sonucu:

```text
validation.success
```

learning evidence'ın success değerini belirliyor.

AI burada yeniden:

> "Bu gerçekten başarılı mı?"

diye karar vermiyor.

Deterministik validator'ın sonucu source of truth.

Challenge type → evidence mapping örnekleri:

```text
code
sql
transformation
→ application

debug
→ debugging

output_prediction
explain
→ explanation

validation
data_investigation
→ validation
```

---

# 27. Adaptive Practice Mentor

Attempt başarısız olduğunda sistem junior'ın geçmiş attempt'lerine göre mentor support üretebiliyor.

Örneğin:

```text
ilk hata
→ küçük yardım

tekrar hata
→ daha güçlü yardım
```

Mentor support seviyeleri yine:

```text
NUDGE
GUIDE
TEACH
DEMONSTRATE
```

mantığına bağlı.

---

# 28. Persistent Micro-Check

Practice mentor desteğine micro-check sistemi eklendi.

Amaç:

Junior'a doğrudan çözümü vermek yerine çok küçük bir kontrol sorusu ile eksik kavramı anlamasını sağlamak.

Örnek:

```text
"Bu dictionary içinden year değerine nasıl erişirsin?"
```

Junior cevap verir.

Micro-check sonucu DB'ye kaydedilir.

Tekrar yanlış cevap verilirse sistem daha fazla destek verebilir.

Doğru cevap:

```text
return_to_challenge
```

ile ana challenge'a dönülmesini sağlar.

Önemli:

Micro-check'i doğru cevaplamak ana challenge'ı otomatik olarak başarılı yapmaz.

---

# 29. Practice Result → Adaptive Recommendation

Phase 5'in en önemli sonuçlarından biri budur.

Canlı Swagger testinde gerçek olarak doğrulandı.

Başlangıç:

```text
python_data_structures

status = learning
attempts = 2
successes = 2
priority = medium
```

Recommendation:

```text
python_data_structures
difficulty = easy
```

Junior bir challenge daha başarıyla tamamladı.

Sonuç:

```text
attempts = 3
successes = 3
status = practicing
priority = low
independence_trend = improving
```

Sistem tekrar recommendation üretti.

Bu kez:

```text
duplicate_analysis
```

seçildi çünkü:

```text
duplicate_analysis
status = learning
priority = medium
```

Yani gerçek adaptive loop çalıştı:

```text
practice
↓
learning evidence
↓
progress update
↓
skill priority change
↓
next skill selection
```

---

# 30. Swagger'da doğrulanan gerçek Phase 5 akışı

Gerçek API smoke test yapıldı.

İlk recommendation:

```text
python_data_structures
priority = medium
difficulty = easy
```

Challenge:

```text
Aktif kullanıcıları say
expected output = 3
```

Attempt:

```text
execution_output = 3
```

Sonuç:

```text
success = true
mentor_support = null
```

Progress:

```text
python_data_structures
attempts = 2
successes = 2
status = learning
```

Bir sonraki challenge:

```text
Yüksek skorları say
expected output = 2
```

Başarılı attempt sonrası:

```text
attempts = 3
successes = 3
status = practicing
priority = low
```

Yeni recommendation:

```text
duplicate_analysis
priority = medium
difficulty = easy
```

Duplicate transformation challenge:

```text
3 rows
↓
duplicate kaldırıldı
↓
2 rows
```

Validation sonucu:

```text
Transformation başarılı:
duplicate row sayısı azaltıldı.
```

Bu smoke test ile adaptive practice loop uçtan uca doğrulandı.

---

# 31. Test durumu

Son full regression:

```text
177 passed
```

Önemli test alanları:

```text
models
database
practice_service
practice_challenges
practice_review_service
practice_progress_integration
transformation_validation_service
mentor_routes
micro-check
progress
mentor policy
```

Şu anda bilinen test failure yok.

---

# 32. Phase durumu

## Phase 1 — Adaptive Data Quality Mentor

```text
✅ COMPLETE
```

Tamamlananlar:

```text
structured findings
finding → skill mapping
adaptive assistance
junior attempt
learning evidence
controlled next step
```

---

## Phase 2 — Deterministic Transformation Validation

```text
✅ COMPLETE
```

Tamamlananlar:

```text
before / after profile
missing values validation
duplicate validation
real dataframe validation
deterministic success
```

---

## Phase 3 — Multi-Step Data Engineering Tasks

```text
✅ COMPLETE
```

Tamamlananlar:

```text
task model
steps
active / pending / completed
task persistence
step transition
transformation validation integration
```

---

## Phase 4 — Learner Progress / Profile

```text
✅ MVP COMPLETE
```

Tamamlananlar:

```text
skill status
attempt count
success rate
last assistance
independence trend
practice priority
progress API
```

---

## Phase 5 — Adaptive Practice & Challenges

```text
✅ COMPLETE FOR MVP / DEMO
```

Tamamlananlar:

```text
practice recommendation
difficulty selection
practice challenge
challenge persistence
structured validation spec
exact output validation
null count reduction
duplicate count reduction
challenge variation
attempt persistence
AI diagnosis
adaptive mentor support
language-aware support
persistent micro-check
practice → evidence
practice → progress
progress → next recommendation
real API smoke test
```

Demo scope için mevcut challenge variation sayısı bilinçli olarak küçük tutuldu.

Gelecekte skill catalog ve challenge bank genişletilecek.

---

# 33. Şu anda ürünün yapabildiği şey

DataPilot artık şu gerçek loop'u çalıştırabiliyor:

```text
Junior profile
↓
skill progress
↓
practice recommendation
↓
appropriate difficulty
↓
challenge
↓
junior attempt
↓
deterministic validation
↓
gerekirse adaptive mentor support
↓
learning evidence
↓
progress update
↓
independence tracking
↓
practice priority update
↓
next challenge / next skill
```

Bu projenin ana ürün fikrinin backend tarafında çalışan MVP'sidir.

---

# 34. Bir sonraki büyük aşama

## PHASE 6 — FRONTEND

Şimdi backend'e yeni büyük feature eklemek yerine ürünü kullanılabilir hale getireceğiz.

Planlanan frontend stack:

```text
React
Tailwind
```

Muhtemel execution araçları:

```text
Python
→ Pyodide

SQL
→ DuckDB-Wasm

Code editor
→ Monaco Editor

Terminal / output
→ browser output panel / xterm-benzeri alan
```

Backend learner'ın arbitrary Python kodunu çalıştırmayacak.

Kod execution mümkün olduğunca browser sandbox tarafında olacak.

---

# 35. İlk frontend hedefi

İlk frontend MVP'de bütün backend özelliklerini bir anda göstermek istemiyoruz.

Önce ana learning loop görünür hale getirilecek.

İlk ekranlarda yaklaşık:

```text
Dashboard
↓
Current Recommendation
↓
Practice Challenge
↓
Code / Transformation Workspace
↓
Run
↓
Submit
↓
Validation Result
↓
Mentor Support
↓
Progress
```

olmalı.

---

# 36. Frontend için ürün prensibi

Workspace junior'ın gerçek işi yaptığı yer olacak.

Burada mentor:

```text
minimum sufficient help
```

vermeli.

Derin öğretim / uzun ders mantığı workspace'i boğmamalı.

İleride ayrı bir:

```text
Learning / Practice environment
```

ile daha derin çalışma yapılabilir.

Ana workspace:

```text
task
code/data
run
validation
next small mentor action
```

odaklı olmalı.

---

# 37. Gelecekte genişleteceğimiz skill sistemi

Şu anda demo için sınırlı skill ve challenge template kullanıyoruz.

Gelecekte skill catalog yaklaşık şu domain'lere ayrılmalı:

```text
Python
├─ data_structures
├─ loops_conditions
├─ functions
├─ error_handling
├─ file_json_csv
└─ data_transformation

SQL
├─ select_filter
├─ joins
├─ group_by_aggregation
├─ null_handling
├─ cte_subquery
├─ window_functions
└─ deduplication

Data Engineering
├─ data_quality
├─ schema_types
├─ transformation
├─ etl_elt
├─ incremental_load
├─ batch_streaming
├─ medallion_architecture
└─ validation_testing
```

Her skill aynı öneme sahip olmayacak.

Örneğin junior Data Engineer için:

```text
SQL joins
group by
data quality
null handling
transformations
```

daha yüksek ağırlıkta olabilir.

---

# 38. Gelecekte challenge difficulty

Her skill için farklı difficulty seviyesi olacak:

```text
foundation
easy
medium
hard
```

Örneğin SQL JOIN:

```text
foundation
→ INNER JOIN ne yapar?

easy
→ iki tabloyu birleştir

medium
→ JOIN + WHERE + GROUP BY

hard
→ üç tablo + NULL + aggregation + business rule
```

Selection ileride:

```text
skill importance
+
learner progress
+
recent mistakes
+
assistance dependency
+
previous challenges
↓
skill
↓
difficulty
↓
challenge type
↓
variant
```

şeklinde gelişecek.

---

# 39. Demo sonrası challenge variation geliştirmesi

Şu anda 3 Python variant var.

Demo sonrası:

```text
template
+
dataset variation
+
threshold variation
+
column variation
+
difficulty
```

kullanarak daha fazla kombinasyon üretilebilir.

Ama tamamen random üretim yerine mümkün olduğunca:

```text
controlled
deterministic
testable
```

template sistemi tercih edilmeli.

Bu sayede:

```text
AI randomness
```

yerine:

```text
predictable validation
```

korunur.

---

# 40. Teknik borç / daha sonra yapılabilecek cleanup

Şu anda `PracticeChallengeRecord` içinde:

```text
validation_spec
```

yanında eski:

```text
expected_outcome
```

alanı backward compatibility için tutuluyor.

DB'deki eski `expected_outcome` kolonu da NOT NULL olduğu için Phase 5 sırasında kaldırılmadı.

Şimdilik problem değildir.

Frontend ve demo tamamlandıktan sonra migration ile temizlenebilir.

---

# 41. Şu anda yapmamamız gerekenler

Phase 6'ya geçerken şu anda backend'i gereksiz büyütmemeliyiz.

Özellikle hemen:

```text
50 challenge template
tam skill ontology
çok gelişmiş mastery algorithm
production auth
cloud deployment
complex admin panel
```

eklememeliyiz.

Öncelik:

> Çalışan adaptive backend'i kullanıcı tarafından görülebilen bir ürüne dönüştürmek.

---

# 42. Bir sonraki oturumda başlayacağımız yer

İlk iş:

```text
PHASE 6 — FRONTEND
```

Başlangıç sırası:

```text
1. Frontend klasör yapısı
2. React app
3. Backend bağlantısı
4. Basit dashboard
5. Practice recommendation gösterimi
6. Challenge ekranı
7. Run / Submit akışı
8. Validation sonucu
9. Mentor support
10. Progress paneli
```

İlk amaç güzel tasarım değil.

İlk amaç:

```text
Backend'deki gerçek adaptive loop'u
tarayıcı üzerinden kullanılabilir hale getirmek.
```

---

# 43. Mevcut checkpoint özeti

Şu anda DataPilot AI backend:

```text
CSV profiling                    ✅
Structured data quality          ✅
Adaptive mentor                  ✅
Learning evidence                ✅
Transformation validation        ✅
Multi-step tasks                 ✅
Learner progress                 ✅
Independence tracking            ✅
Practice recommendation          ✅
Difficulty adaptation            ✅
Challenge generation             ✅
Challenge persistence            ✅
Challenge variation              ✅
Structured validation            ✅
Exact output validation          ✅
Null reduction validation        ✅
Duplicate reduction validation   ✅
Practice attempt persistence     ✅
Adaptive mentor support          ✅
Persistent micro-check           ✅
Practice → progress              ✅
Progress → new recommendation    ✅
Swagger end-to-end smoke test    ✅
Full test suite                  ✅ 177 passed
```

Sonuç:

**Phase 5 backend MVP tamamlandı.**

Sıradaki aşama:

# Phase 6 — Frontend 🚀
