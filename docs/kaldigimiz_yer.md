# DataPilot AI — Kaldığımız Yer

Son güncelleme: 19 Eylül 2026

---

# 1. DataPilot AI nedir?

DataPilot AI basit bir:

> "AI'a soru sor → cevap al"

uygulaması değildir.

Ana ürün fikri:

> Junior Data Engineer gerçek görevler üzerinde çalışırken, sistem onun hangi becerilerde ne kadar bağımsız olduğunu takip eder ve yalnızca ihtiyaç duyduğu kadar yardım eder.

Ana prensip:

**AI junior'ın işini onun yerine yapmamalı. Junior'ın işi zamanla kendi başına yapabilmesini sağlamalı.**

Sistem iki ana parçadan oluşuyor:

```text
Data Engineering Workspace
+
Adaptive Mentor / Practice System

Temel ürün yaklaşımı:

Junior gerçek görev yapar
↓
DataPilot problemi ve bağlamı anlar
↓
Uygun çalışma planı oluşturulur
↓
Junior işi kendisi uygular
↓
Sistem sonucu doğrular
↓
Gerekiyorsa minimum yeterli yardım verir
↓
Learning evidence oluşur
↓
Skill progress güncellenir
↓
Bir sonraki görev / practice buna göre adapte olur
2. Kullanılan teknoloji

Backend:

Python
FastAPI
Pydantic
SQLite
Pandas
OpenAI API
Embeddings / RAG
Pytest

Frontend:

React
TypeScript
Vite
CSS
Pyodide
lucide-react

Python transformation kodu mümkün olduğunca browser tarafında çalıştırılıyor.

Backend learner'ın arbitrary Python kodunu çalıştırmıyor.

3. Ana ürün prensipleri
3.1 Minimum sufficient help

Mentor mümkün olan en büyük cevabı vermek yerine junior'ın devam edebilmesi için gereken en küçük yeterli yardımı vermeli.

Assistance seviyeleri:

NONE
NUDGE
GUIDE
TEACH
DEMONSTRATE

Amaç:

TEACH
↓
GUIDE
↓
NUDGE
↓
NONE

şeklinde zamanla daha bağımsız çalışmaya geçmek.

3.2 Deterministic yapılabilecek işi AI'ya bırakma

Örneğin:

missing_values
→ null_analysis

duplicate_rows
→ duplicate_analysis

gibi finding → skill mapping deterministic tutuluyor.

Validation da mümkün olduğunca gerçek before / after data üzerinden deterministic çalışıyor.

3.3 AI işi junior'ın yerine yapmamalı

Workspace içinde AI:

task'i anlamaya
plan oluşturmaya
minimum yardım vermeye
problemi açıklamaya

yardım edebilir.

Ancak transformation ve gerçek işi junior yapmalı.

Daha derin öğrenme Practice alanında yapılmalı.

4. Backend — mevcut ana sistemler

Backend tarafında şu temel sistemler çalışıyor:

Session / conversation history
Document upload
RAG
CSV profiling
Structured Data Quality Analysis
Adaptive Mentor
Learning Evidence
Transformation Validation
Multi-Step Tasks
Learner Progress
Independence Tracking
Practice Recommendation
Practice Challenges
Practice Validation
Micro-Check
Workspace persistence
Workspace dataset management
Version / rollback
Final validation
Review
Handoff
5. CSV profiling

CSV yüklendiğinde Pandas ile profile çıkarılıyor.

Profile içinde örneğin:

row_count
column_count
columns
data_types
null_counts
duplicate_count
sample_rows
numeric_columns
numeric_summary

bulunabiliyor.

Önemli güvenlik ayrımı:

build_data_profile()

içinde sample_rows üretilebilir.

Ancak workspace içinde persist edilen ve AI'a gönderilen profile bundan ayrılıyor.

6. Structured Data Quality Analysis

AI çıktısı düz serbest metin yerine structured modellerle tutuluyor.

Temel model:

DataQualityFinding

Alanlar:

issue_type
column
severity
observation
suggested_action

Desteklenen finding örnekleri:

missing_values
duplicate_rows
suspicious_values
data_type_issue
schema_issue

Bu sayede AI sonucu backend tarafından programatik olarak kullanılabiliyor.

7. Skill ve learner progress sistemi

Takip edilen skill örnekleri:

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

Skill durumları:

new
learning
practicing
comfortable

Learner progress API şu bilgileri takip edebiliyor:

skill_name
status
attempts
successful_attempts
success_rate
last_assistance_level
independence_trend
practice_priority
8. Learning Evidence

Junior'ın yaptığı her hareket doğrudan progress sayılmıyor.

Gerçek öğrenme kanıtları:

application
explanation
debugging
validation

gibi evidence türleriyle tutuluyor.

Evidence sonucu:

success = True

veya:

success = False

olabilir.

Bu veriler learner progress'i güncelliyor.

9. Independence tracking

Sadece doğru / yanlış sonucu değil, ne kadar yardımla başarıldığı da takip ediliyor.

Assistance independence yaklaşımı:

DEMONSTRATE = en yüksek yardım
TEACH
GUIDE
NUDGE
NONE = en bağımsız

Amaç junior'ın zamanla daha az desteğe ihtiyaç duyması.

Örneğin:

TEACH
↓
GUIDE
↓
NUDGE
↓
NONE

gelişimi:

independence_trend = improving

olarak değerlendirilebilir.

10. Practice sistemi

Practice sistemi Workspace'ten ayrı düşünülüyor.

Workspace:

gerçek işi yap
minimum yardım al
sonucu validate et

Practice:

öğren
tekrar et
farklı senaryolar çöz
hata yap
feedback al

Practice challenge type'ları:

code
multiple_choice
debug
output_prediction
sql
data_investigation
transformation
validation
explain
11. Practice recommendation

Learner progress'ten practice recommendation üretilebiliyor.

Akış:

learner progress
↓
practice priority
↓
skill seçimi
↓
difficulty seçimi
↓
challenge

Difficulty:

foundation
easy
medium
hard
12. Practice validation

Practice sistemi deterministic validation kullanıyor.

Mevcut validation örnekleri:

exact_output
exact_answer
null_count_reduction
duplicate_count_reduction

Transformation practice'te:

input_rows
↓
junior transformation
↓
result_rows
↓
before / after karşılaştırması
↓
deterministic validation

uygulanıyor.

13. Adaptive Practice Mentor

Junior challenge'da zorlandığında destek seviyesi kademeli artabiliyor.

Örnek:

ilk hata
→ NUDGE

tekrar hata
→ GUIDE

devam eden hata
→ TEACH

gerektiğinde
→ DEMONSTRATE

Amaç doğrudan cevabı vermek yerine junior'ın kendisinin çözmesini sağlamak.

14. Micro-Check sistemi

Mentor desteğinden sonra junior'a küçük kavram kontrolü sorulabiliyor.

Örnek:

"Bu dictionary içinden year değerine nasıl erişirsin?"

Micro-check sonucu ayrı kaydediliyor.

Doğru micro-check:

ana challenge'a geri dön

anlamına gelir.

Ana challenge otomatik başarılı sayılmaz.

15. Workspace 2.0 — ürün vizyonu

Workspace gerçek çalışma alanıdır.

Amaç:

Junior'ın şirket veya kişisel veri görevini kontrollü, doğrulanabilir ve güvenli bir ortamda tamamlaması.

Ürün konumlandırması:

Junior'ın şirket verisi üzerinde güvenli çalışmasını sağlayan kontrollü AI workspace.

Workspace context:

Work
Personal
16. Work ve Personal ayrımı

Work workspace:

şirket görevi
validation
review
handoff
security
audit

odaklıdır.

Personal workspace:

portfolio
Kaggle
deneme
kişisel öğrenme
exploration

gibi kullanım içindir.

Uzun vadeli kritik güvenlik kuralı:

Work data
→ Personal workspace içinde kullanılamaz
17. Workspace güvenlik hiyerarşisi

Planlanan yapı:

Account / Organization
        ↓
Security Policy
        ↓
Workspace
  Work / Personal
        ↓
Data Classification
        ↓
Dataset / Task / Mentor

Security iki katmanda düşünülüyor:

Organization / Account policy
+
Workspace context / data sensitivity

Şu an MVP seviyesinde data sensitivity metadata olarak tutuluyor.

Gerçek organization authorization daha sonra eklenecek.

18. Workspace data sensitivity

Work workspace oluşturulurken veri sensitivity metadata tutulabiliyor.

Seçenekler:

public
internal
confidential
restricted
unknown

Bu bilgiler gelecekte:

AI usage policy
export policy
document access
organization rules

ile bağlanacak.

19. Workspace 2.0 tam kullanıcı akışı

Şu anda çalışan temel flow:

Source
↓
Profile
↓
Plan
↓
Transform
↓
Validate
↓
Review
↓
Handoff
↓
Workspace Completed

Bu flow frontend'de stepper olarak da gösteriliyor.

20. Workspace creation

Yeni workspace oluşturulurken şu bilgiler alınabiliyor:

Workspace name
Task brief
Expected outcome
Work / Personal
Data sensitivity
Workflow type

Workflow type seçenekleri:

auto
etl
elt
data_quality
analysis
pipeline

Varsayılan:

auto
21. Dataset storage

Workspace dataset'i server tarafında workspace'e özel klasörde tutuluyor.

Yapı:

data/workspaces/<workspace_uuid>/
├── source.csv
├── working.csv
└── versions/

Prensip:

source.csv
→ original / read-only kaynak

working.csv
→ junior'ın transformation yaptığı çalışma kopyası

Transform işlemleri source dosyasını değiştirmiyor.

22. Data profiling ve AI güvenliği

Önce dataset lokal olarak profile ediliyor.

Hedef mimari:

Raw dataset
↓
local / approved processing
↓
schema + statistics + validation context
↓
sanitized profile
↓
AI

AI'a gereksiz raw satır gönderilmemeli.

23. sample_rows güvenlik düzeltmesi

19 Eylül 2026 itibarıyla bu konu düzeltildi.

Önceden route içinde akış:

profile
↓
generate_data_recommendations(profile)
↓
sample_rows siliniyordu

şeklindeydi.

Bu durumda route seviyesinde AI fonksiyonu sample_rows içeren profile alabiliyordu.

Şimdi:

profile
↓
sample_rows çıkarılır
↓
safe_profile
↓
generate_data_recommendations(safe_profile)

şeklinde çalışıyor.

Ayrıca data_ai_service.py içinde prompt oluşturulurken de sample_rows tekrar filtreleniyor.

Yani defense-in-depth var:

Route sanitization
+
AI prompt sanitization
24. sample_rows regression testi

Bu güvenlik davranışı için özel test eklendi.

Test doğruluyor:

generate_data_recommendations()
→ sample_rows ALMIYOR

API response profile
→ sample_rows İÇERMİYOR

Böylece gelecekte biri yanlışlıkla sanitization sırasını bozarsa test failure oluşacak.

25. AI Execution Plan

Dataset profile ve findings'ten AI destekli execution plan oluşturulabiliyor.

Plan:

task
├── step 1
├── step 2
└── ...

Ancak şu anda güvenli ve deterministic olarak validate edilebildiğimiz transformation finding'leri öncelikli:

missing_values
duplicate_rows

Execution plan maximum kontrollü tutuluyor.

AI doğrudan transformation'ı yapmıyor.

Junior'ın yapacağı adımları tarif ediyor.

26. Gelecekte gelişmiş step type

Execution plan ileride şu step type'larla genişletilebilir:

investigate
transform
validate
decision

Bu sayede:

suspicious_values
schema_issue
data_type_issue

gibi bulgular daha doğru workflow ile ele alınabilir.

Örnek:

Suspicious value
↓
Investigate
↓
business rule / documentation kontrolü
↓
Decision
↓
gerekirse Transform
↓
Validate
27. Browser-side transformation workbench

Workspace'te gerçek çalışma alanı mevcut.

Junior:

working.csv

üzerinde Python transformation yazabiliyor.

Python kodu Pyodide ile browser içinde çalıştırılıyor.

Flow:

working data
↓
Python code
↓
Run
↓
browser preview
↓
Submit
↓
backend validation

Run yalnızca preview üretir.

Submit backend validation + persistence akışını başlatır.

28. Transformation validation

Şu anda desteklenen ana transformation problemleri:

missing_values
duplicate_rows

Örnek:

before duplicate_count = 1
after duplicate_count = 0
→ success

veya:

before null_count = 2
after null_count = 0
→ success

Başarılı transformation sonrası:

working.csv güncellenir
task step tamamlanır
bir sonraki step aktif olur
checkpoint güncellenir
version oluşturulur
29. Version history ve rollback

Workspace transformation'ları version snapshot oluşturabiliyor.

Junior:

v1
v2
v3

gibi önceki working dataset durumlarını görebiliyor.

Restore işlemi:

working.csv
task state
checkpoint

durumunu ilgili version'a geri alabiliyor.

Gelecekte version metadata şu bilgilerle genişletilebilir:

transformation code
validation metrics
learner
timestamp
dataset hash
reason / note
30. Final validation

Task transformation adımları tamamlandığında final validation çalıştırılıyor.

Endpoint:

POST /workspaces/{learner_id}/{workspace_id}/validate

Kontroller:

Dataset integrity
Schema preserved
Duplicate rows
Missing values

Validation sonucu workspace içinde persist ediliyor.

Sayfa yenilense bile sonuç kaybolmuyor.

31. Structured validation localization

Validation check'leri artık yalnızca İngilizce human-readable string olarak kullanılmıyor.

Backend modelinde:

code
params

alanları var.

Örnek:

{
  "code": "missing_values",
  "params": {
    "column": "age",
    "missing_count": 0
  }
}

Frontend bu machine-readable bilgiyi kullanarak seçili dile göre metni oluşturuyor.

Böylece:

TR
Eksik değerler · age
age sütununda 0 eksik değer kaldı.

ve:

EN
Missing values · age
0 missing values remain in age.

gösterilebiliyor.

Eski persisted validation kayıtları için fallback desteği de bulunuyor.

32. Final review

Validation başarılı olduktan sonra insan review aşaması var.

Amaç:

Teknik validation başarılı olsa bile junior final dataset'i kendisi gözden geçirmeli.

Review tamamlandığında workspace checkpoint güncelleniyor.

33. Handoff

Review sonrası final teslim aşaması bulunuyor.

Fonksiyonlar:

Final CSV export
Handoff completion

Export için şartlar:

successful validation
+
completed review

Handoff completion ayrı bir action.

Final export dosyası:

datapilot_final.csv

olarak alınabiliyor.

34. Tamamlanmış test workspace

Gerçek smoke test yapılan workspace:

Frontend Workspace Test

Task:

Clean duplicate customer records and investigate missing IDs.

Expected outcome:

A validated clean customer dataset.

Başlangıç:

5 source rows
1 duplicate
2 missing age values

Final working data:

customer_id,name,age,city
1001,Alice,31,Den Haag
1002,Bob,29.5,Rotterdam
1003,Carol,28,Utrecht
1004,David,29.5,Delft

Sonuç:

4 rows
0 duplicates
0 missing age values
schema preserved
validation passed
review completed
handoff completed
workspace completed
35. Workspace frontend UX

Workspace uzun tek sayfa olarak çalışıyor ancak ana navigasyon korunuyor.

Mevcut davranış:

Sidebar
→ sabit

Sağ workspace içeriği
→ kendi içinde scroll

Workspace header + flow
→ sticky

Bu sayede junior uzun workspace'te aşağı inerken bağlamını kaybetmiyor.

36. Collapsible sections

Şu alanlar collapsible:

Data Source
Execution Plan

Execution Plan, Data Source bölümünden bağımsız bir kart.

Yani Data Source kapatıldığında Plan kaybolmuyor.

Validation / Review / Handoff şu anda gate stage oldukları için görünür tutuluyor.

37. Execution Plan status düzeltmesi

Önceden bütün task step'leri tamamlanmış olsa bile Execution Plan kartında:

Active

görünebiliyordu.

Bu düzeltildi.

Task tamamlandıysa:

Completed

gösteriliyor.

38. Merkezi localization sistemi

Frontend'de merkezi localization temeli kuruldu.

Dosya:

frontend/src/i18n.ts

Dil tipi:

en
tr

Frontend:

const t = translations[language]

mantığıyla çalışıyor.

Sidebar EN / TR switch üzerinden canlı değişiyor.

39. Şu anda localization durumu

Workspace tarafındaki önemli UI alanları büyük ölçüde EN / TR destekli:

Sidebar
Workspace header
Flow stepper
Workspace metadata
Task brief
Expected outcome
Progress
Data Source
Data Profile
Findings
Execution Plan heading
Final Validation
Validation stats
Validation check names/messages
Final Review
Handoff
Workspace completed state

Ancak localization henüz bütün uygulama için tamamlanmış değil.

Özellikle ileride temizlenecek alanlar:

Dashboard
New Workspace
Practice
Transform workbench içindeki bazı metinler
AI-generated plan step title/body
bazı backend-generated text alanları
40. Legacy frontend cleanup

Eski hardcoded:

Customer Data Quality

workspace ekranı tamamen kaldırıldı.

Kaldırılan legacy parçalar:

hardcoded Alice / Bob / Carol / David dataset
old transformation submit flow
old completeWorkspace flow
old mentor drawer
old mentor state
hardcoded inputRows
legacy workspace-specific JSX
unused functions / state

Artık bütün gerçek workspaces Workspace 2.0 ekranını kullanıyor.

Legacy cleanup sonrası frontend build başarılı.

41. Sidebar modülleri

Sidebar şu yapıda kalacak:

Dashboard
Practice
Tasks
Progress
Documents
Settings

Workspace açıldığında ayrıca:

Workspace

navigation item'ı görünüyor.

Bu modüller placeholder olarak kaldırılmayacak çünkü ürün roadmap'inin gerçek parçaları.

42. Tasks modülü — sıradaki ana feature

Sıradaki ana geliştirme:

Tasks

Amaç:

Junior'ın bütün workspace'lerdeki iş takibini tek yerde görebilmesi.

Planlanan task status:

To do
Active
Blocked
Completed

Task görünümünde ileride:

task
workspace
current step
next action
status
validation state
review state
handoff state
updated time

gösterilebilir.

Tasks günlük çalışma merkezi olacak.

43. Progress modülü

Tasks sonrasında Progress ekranı geliştirilecek.

Amaç:

Junior hangi becerilerde gelişiyor ve artık hangi işleri daha bağımsız yapabiliyor?

Gösterilebilecek bilgiler:

strong skills
weak skills
skills to practice
attempt count
success rate
last assistance level
independence trend
practice priority
recommended next topics

Mevcut learner progress backend'i bu ekranın temelini zaten sağlıyor.

44. Documents modülü

Documents yalnızca dosya listesi olmayacak.

Amaç:

Güvenli dataset / document library.

Planlanan yapı:

Documents
├── Personal
└── Work
    ├── Organization
    └── Workspace

Document metadata ileride:

scope
workspace_id
organization_id
data_sensitivity
document_type
owner
created_at

içerebilir.

Kritik kural:

Personal Workspace
+
Work / Confidential document
→ BLOCKED
45. Settings modülü

Settings içinde ileride:

Profile
Language
Theme
AI Usage
Budget / Limits
Security Preferences

bulunabilir.

Theme:

Light
Dark

Language:

English
Turkish
ileride Dutch
46. AI token / cost görünümü

Settings içinde AI usage takibi planlanıyor.

Örnek:

tokens used this month
estimated AI cost
budget limit
remaining budget
usage percentage

Örnek warning policy:

< 80%
→ normal

>= 80%
→ warning

>= 95%
→ critical

>= 100%
→ limit / policy action

Token / cost hesabı frontend'e hardcode edilmeyecek.

Gerçek backend API usage bilgisinden hesaplanmalı.

47. Production security roadmap

MVP sonrası güçlendirilmesi gereken alanlar:

authentication
organization policy
workspace authorization
document authorization
Work / Personal isolation
PII detection
sensitive column detection
destructive-operation warnings
audit trail
export policy
dataset hash
version metadata
AI usage policy

Şu anda gerçek confidential company data ile production kullanımı hedeflenmiyor.

Demo ve geliştirme sırasında:

synthetic
veya
public

data tercih edilmeli.

48. PII / sensitive data yaklaşımı

Uzun vadede sistem dataset'i AI'a göndermeden önce:

column classification
PII detection
sensitivity classification
policy check
sanitization

uygulayabilmeli.

Hedef:

Raw company data
↓
approved local processing
↓
sanitized metadata / statistics
↓
AI
49. Test durumu

19 Eylül 2026 itibarıyla full backend regression:

195 passed

Bilinen backend test failure yok.

Frontend:

npm run build

başarılı.

Browser smoke test de Workspace 2.0 için başarılı.

50. Son önemli Git checkpoint'leri

Son önemli commit'ler:

f677c5e
Prevent sample rows from reaching AI

d193ec5
Remove legacy workspace frontend

a26adb0
Localize persisted validation results

d77fbae
Localize workspace validation review and handoff

87e7341
Improve workspace UX and add localization foundation

34a63c1
Document Workspace 2.0 roadmap and next steps
51. Workspace 2.0 mevcut durum

Tamamlanan ana özellikler:

Workspace creation                     ✅
Task brief / expected outcome          ✅
Work / Personal context                ✅
Data sensitivity metadata              ✅
CSV upload                             ✅
source.csv / working.csv separation    ✅
Data profile                           ✅
Safe persisted profile                 ✅
sample_rows AI sanitization            ✅
AI execution plan                      ✅
Supported finding filtering            ✅
Step tracker                           ✅
Browser-side Pyodide                   ✅
Run preview                            ✅
Transformation submit                  ✅
Deterministic validation               ✅
working.csv persistence                ✅
Version snapshot                       ✅
Rollback / restore                     ✅
Final validation                       ✅
Validation persistence                 ✅
Structured validation localization     ✅
Final review                           ✅
Review persistence                     ✅
Final CSV export                       ✅
Handoff completion                     ✅
Workspace completed                    ✅
Sticky workspace navigation            ✅
Collapsible Data Source                ✅
Collapsible Execution Plan             ✅
EN / TR localization foundation        ✅
Legacy workspace removal               ✅
Backend regression                     ✅ 195 passed
Frontend production build              ✅
Browser smoke test                     ✅
52. Henüz tamamlanmamış önemli alanlar

Workspace 2.0 kullanılabilir bir MVP temelinde ancak production-ready değildir.

Önemli kalan alanlar:

Full-app localization
Tasks UI
Progress UI
Documents UI
Settings UI
Work / Personal authorization
Organization policies
PII detection
Audit trail
Authentication
Advanced workflow step types
Token / cost tracking
Dark theme
Dutch localization
53. Şu anda yapmamamız gerekenler

Bu aşamada ürünü gereksiz yere büyütmemeliyiz.

Şimdilik kaçınılacak işler:

50+ challenge template
tam skill ontology
çok karmaşık mastery algorithm
production cloud architecture
enterprise auth
complex admin panel
çok sayıda AI agent

Öncelik:

Çalışan temel ürünü temiz, anlaşılır, güvenli ve kullanılabilir hale getirmek.

54. Bir sonraki geliştirme sırası

Güncel sıra:

1. docs checkpoint update                         ← ŞU AN
2. Tasks modülü
3. Progress modülü
4. Documents modülü
5. Work / Personal document isolation
6. Settings
7. Theme
8. Full-app localization cleanup
9. AI usage / token / cost tracking
10. Audit / security hardening
11. Advanced workflow step types
12. PII / sensitive-column detection
13. Organization / authorization layer

Her büyük aşamada:

implement
↓
tests
↓
frontend build
↓
browser smoke test
↓
git checkpoint

uygulanacak.

55. Mentor olarak çalışma yöntemi

Bu proje öğrenme amacı da taşıyor.

Sadece çalışan kod üretmek yeterli değil.

Çalışma döngüsü:

Neden gerekiyor?
↓
Kullanıcı kodu görür / tamamlar
↓
Dosyalar arası akış açıklanır
↓
Test edilir
↓
Gerekirse temel parça yeniden kurulur

Kullanıcı uzun süre IT'den uzak kaldığı için amaç yalnızca projeyi bitirmek değil, bilgiyi tekrar aktif hale getirmek.

Kod değişikliklerinde:

dosya
↓
Ctrl + F ile aranacak yer
↓
tam değişiklik bloğu
↓
test komutu
↓
beklenen sonuç

şeklinde ilerlemek tercih ediliyor.

56. Güncel ürün özeti

DataPilot AI artık yalnızca bir chatbot veya eğitim demosu değil.

Şu anda çalışan yapı:

Workspace oluştur
↓
Task tanımla
↓
Dataset yükle
↓
Profile çıkar
↓
AI destekli plan oluştur
↓
Junior transformation'ı kendisi yazsın
↓
Browser'da çalıştır
↓
Backend sonucu doğrulasın
↓
Version oluştur
↓
Gerekirse rollback
↓
Final validation
↓
Human review
↓
Final export
↓
Handoff
↓
Workspace completed

Bunun yanında ayrı adaptive learning sistemi:

Practice
↓
Attempt
↓
Validation
↓
Mentor support
↓
Learning evidence
↓
Skill progress
↓
Next recommendation

olarak çalışıyor.

İki sistemin uzun vadeli birleşimi:

Gerçek işte yapılan çalışma
+
Practice alanındaki öğrenme
↓
Global learner profile
↓
Daha bağımsız junior
57. Şu an kaldığımız yer

Workspace 2.0'ın temel MVP foundation'ı tamamlandı.

Son teknik durum:

Backend tests:
195 passed

Frontend build:
passed

Legacy frontend:
removed

Validation localization:
structured and working

sample_rows security:
fixed + regression tested

Latest security commit:
f677c5e
Prevent sample rows from reaching AI

Bir sonraki ana feature:

Tasks Modülü

Amaç:

Bütün workspace'lerdeki gerçek işleri ve mevcut durumlarını tek bir günlük çalışma ekranında toplamak.


Kaydettikten sonra önce:

```powershell
git status

çalıştır