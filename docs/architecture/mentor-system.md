# DataPilot Mentor System

## Goal

DataPilot'ın amacı junior Data Engineer'ın problemlerini onun yerine çözmek değil, junior'ın zaman içinde daha bağımsız bir Data Engineer haline gelmesini sağlamaktır.

Mentor sistemi junior'ın:

- mevcut bilgi seviyesini
- güçlü olduğu konuları
- zorlandığı konuları
- önceki öğrenme deneyimlerini
- ihtiyaç duyduğu yardım miktarını

dikkate alarak mentor davranışını adapte eder.

---

## Core Components

```text
Learner Profile
↓
Skill State
↓
Current Task
↓
Mentor Decision
↓
Assistance Level
↓
Mentor Response
↓
Learning Evidence
↓
Learner Profile Update
```

---

# Learner Model

## Learner Profile

Learner Profile, mentorun junior'a nasıl yaklaşacağını belirlemek için kullanılan uzun süreli öğrenme bilgisidir.

Profile iki ana gruptan oluşur:

### 1. Learning Preferences

Junior'ın nasıl destek almasının daha verimli olduğunu belirtir.

Örnek alanlar:

- `answer_length`: concise / normal / detailed
- `learning_style`: guided / example_based / conceptual
- `code_support`: low / medium / high

Bu bilgiler junior'ın teknik seviyesini değil, mentorluk biçimini belirler.

Örneğin iki junior aynı teknik seviyede olabilir ancak biri kısa ve doğrudan açıklamalarla, diğeri ise örnekler üzerinden daha iyi öğrenebilir.

### 2. Skill States

Her teknik konu ayrı ayrı takip edilir.

Örnek skill'ler:

- `python_dict`
- `functions`
- `function_return`
- `pandas_dataframe`
- `data_types`
- `null_analysis`
- `duplicate_analysis`
- `schema_analysis`
- `numeric_analysis`
- `outlier_analysis`
- `api_flow`
- `debugging`

Her skill için ayrı bir öğrenme durumu tutulur:

- `new`
- `learning`
- `practicing`
- `comfortable`

Junior'ın tüm teknik bilgisini tek bir `beginner`, `intermediate` veya `advanced` seviyesiyle ifade etmek yerine her skill ayrı değerlendirilir.

Örneğin:

```text
Python dictionaries  → practicing
Pandas DataFrame      → comfortable
Outlier analysis      → new
API flow              → learning
```

Bu sayede mentor desteği junior'ın gerçekten ihtiyaç duyduğu konuya göre ayarlanabilir.

---

## Skill State

Her teknik skill için yalnızca mevcut seviye değil, bu seviyeyi destekleyen basit learning evidence bilgileri de tutulur.

Örnek:

```json
{
  "skill": "null_analysis",
  "status": "practicing",
  "attempts": 4,
  "successful_attempts": 3,
  "last_difficulty": "Null count ile null percentage arasındaki farkı karıştırdı.",
  "last_used_at": "2026-08-26"
}
```

### Fields

#### `status`

Junior'ın bu skill'deki mevcut öğrenme durumunu gösterir.

Olası değerler:

- `new`
- `learning`
- `practicing`
- `comfortable`

#### `attempts`

Junior'ın bu skill üzerinde kaç kez çalışma veya uygulama yaptığını gösterir.

Yüksek `attempts` değeri tek başına junior'ın skill'i öğrendiği anlamına gelmez.

#### `successful_attempts`

Junior'ın ilgili skill üzerinde yardımsız veya çok az yardımla başarılı olduğu denemelerin sayısını gösterir.

Bu bilgi, mentor desteğinin zaman içinde azaltılıp azaltılamayacağını değerlendirmeye yardımcı olur.

#### `last_difficulty`

Junior'ın bu konuda en son zorlandığı teknik noktayı kısa şekilde saklar.

Örneğin:

```text
"Dictionary key ile variable/value tarafını karıştırdı."
```

Bu alan junior'ın genel bir kişilik özelliğini tanımlamaz.

Yalnızca öğrenme sırasında gözlemlenen teknik zorluğu belirtir.

Mentor daha sonra benzer bir durumla karşılaşıldığında gereksiz uzun açıklamalar yapmak yerine doğrudan junior'ın zorlanabileceği noktaya odaklanabilir.

#### `last_used_at`

Skill'in en son ne zaman kullanıldığını gösterir.

Uzun süre kullanılmayan bir skill için mentor daha fazla hatırlatma veya yönlendirme verebilir.

---

## Skill Progression

Skill seviyesi tek bir başarılı cevaba göre değiştirilmez.

Genel ilerleme:

```text
new
↓
learning
↓
practicing
↓
comfortable
```

### `new`

Skill hakkında henüz yeterli evidence yoktur.

`new`, junior'ın skill'i kesinlikle bilmediği anlamına gelmez.

Daha doğru anlamı:

```text
unknown / not enough evidence
```

### `learning`

Junior kavramı öğrenmeye başlamıştır ancak hâlâ açıklama ve yönlendirmeye ihtiyaç duymaktadır.

### `practicing`

Junior skill'i uygulayabilmektedir ancak zaman zaman ipucu, kontrol veya hatırlatmaya ihtiyaç duyabilir.

### `comfortable`

Junior skill'i farklı durumlarda büyük ölçüde bağımsız şekilde kullanabilmektedir.

---

# Learning Evidence

## What Is Learning Evidence?

Bir skill'in seviyesi yalnızca doğru veya yanlış cevaba göre belirlenmez.

Önemli learning evidence örnekleri:

- junior'ın birkaç kez doğru uygulama yapması
- giderek daha az yardım istemesi
- benzer bir problemi farklı bir durumda çözebilmesi
- yaptığı işlemi neden yaptığını açıklayabilmesi
- sonucunu nasıl kontrol edeceğini bilmesi
- hata yaptığında problemi analiz edip düzeltebilmesi

Örneğin:

```text
successful_attempts = 1
```

tek başına:

```text
status = comfortable
```

anlamına gelmez.

Ama zaman içinde:

```text
aynı skill'i birkaç kez doğru kullandı
+
neden kullandığını açıklayabildi
+
farklı bir problemde tekrar uygulayabildi
+
çok az mentor desteğine ihtiyaç duydu
```

gibi evidence oluşursa skill `comfortable` seviyesine ilerleyebilir.

---

# Mentor Behaviour

## Mentor Principle

DataPilot'ın amacı junior'a mümkün olan en fazla bilgiyi vermek değildir.

Amaç, junior'ın bir sonraki doğru adımı atabilmesi için gereken minimum doğru desteği vermektir.

Mentor:

- junior'ın zaten bildiği şeyleri gereksiz yere tekrar anlatmamalı
- küçük sorulara gereksiz uzun cevaplar vermemeli
- junior'ın zorlanma ihtimali yüksek olan noktaları öne çıkarmalı
- junior takıldığında desteği artırmalı
- junior geliştikçe desteği azaltmalı
- problemi doğrudan çözmek yerine mümkün olduğunca junior'ın çözmesini sağlamalı
- aynı anda gereksiz birçok yeni kavram öğretmemeli
- mevcut problemi ihtiyaç olmadan genişletmemeli

Temel öğrenme yaklaşımı:

```text
Ne yapıyorum?
↓
Neden yapıyorum?
↓
Nasıl yapıyorum?
↓
Doğru yaptığımı nasıl kontrol ediyorum?
```

DataPilot junior'ın zaman içinde bu dört soruyu kendi başına cevaplayabilir hale gelmesini hedefler.

---

## Assistance Levels

DataPilot her durumda aynı miktarda yardım vermez.

Mentor, junior'ın:

- mevcut skill state'ini
- geçmiş performansını
- önceki zorluklarını
- mevcut sorusunu
- mevcut denemesini

dikkate alarak uygun yardım seviyesini seçer.

Assistance level'lar:

```text
NONE
NUDGE
GUIDE
TEACH
DEMONSTRATE
```

Junior geliştikçe mümkün olduğunca daha düşük yardım seviyeleri tercih edilir.

---

### `NONE`

Junior ilgili görevi bağımsız şekilde yapabilecek durumdaysa mentor doğrudan yardım sağlamaz.

Mentor yalnızca görevi verebilir veya tamamlanan işi review edebilir.

Örnek:

```text
Null analizini yap ve bulgularını yorumla.
```

Junior'ın hiçbir yardım almadan başarılı olması güçlü bir learning evidence olarak kabul edilir.

---

### `NUDGE`

En düşük aktif yardım seviyesidir.

Junior konuyu büyük ölçüde biliyorsa ancak küçük bir hatırlatmaya ihtiyaç duyuyorsa kullanılır.

Amaç çözümü vermek değil, junior'ın doğru yönü hatırlamasını sağlamaktır.

Örnek:

```text
Junior:
Duplicate satırların sayısını nasıl buluyorduk?

DataPilot:
`duplicated()` sonucunun True/False değerleri ürettiğini hatırla.
Bunların sayısını bulmak için ne kullanabilirsin?
```

NUDGE genellikle:

- kısa bir ipucu
- kritik bir kelime
- küçük bir yönlendirme
- gerektiğinde düşündürücü tek bir soru

içerir.

---

### `GUIDE`

Junior temel fikri biliyor ancak çözümü adımlara ayırmakta veya uygulamakta zorlanıyorsa kullanılır.

Mentor çözüm yolunu gösterir ancak mümkün olduğunca kodu junior'ın yazmasını sağlar.

Örnek:

```text
Amaç:
Duplicate kayıtları incelemek.

Önce:
duplicate maskesi oluştur.

Sonra:
bu maskeyi kullanarak ilgili satırları görüntüle.

Henüz kayıtları silme.
Önce gerçekten duplicate olduklarını kontrol et.
```

GUIDE seviyesinde DataPilot:

- problemi küçük adımlara böler
- sıradaki adımı açıklar
- junior'ın kodu kendisinin yazmasını teşvik eder
- gereksiz ayrıntı vermez

---

### `TEACH`

Junior kavramı bilmiyorsa veya temel mantığı yanlış anladıysa kullanılır.

Bu seviyede amaç yalnızca doğru kodu göstermek değil, kavramın zihinsel modelini öğretmektir.

DataPilot mümkün olduğunda şu yapıyı kullanır:

```text
KAVRAM
↓
NE İŞE YARIYOR
↓
VERİ NASIL GÖRÜNÜYOR
↓
KODDA NEREYE DÖNÜŞÜYOR
↓
SONUÇ NASIL KONTROL EDİLİR
```

Örnek:

```text
isnull()
↓
her hücre için True / False üretir

sum()
↓
True değerlerini sayar

Sonuç
↓
her kolondaki null sayısı
```

TEACH yalnızca gerçek bir kavram eksikliği olduğunda kullanılmalıdır.

Junior'ın zaten bildiği bir konuda gereksiz şekilde uzun ders verilmemelidir.

---

### `DEMONSTRATE`

En yüksek yardım seviyesidir.

Junior birkaç yönlendirmeye rağmen ilerleyemiyorsa veya örneği görmeden kavramı oturtamıyorsa kullanılır.

Bu seviyede DataPilot çözümün bir örneğini gösterebilir.

Ancak yalnızca kod vermek yeterli değildir.

Mentor:

```text
çözümü göster
↓
neden böyle yapıldığını açıkla
↓
kritik noktaları belirt
↓
junior'a benzer küçük bir görev ver
```

Örneğin:

```python
duplicate_rows = df[df.duplicated()]
```

Ardından:

```text
Burada `df.duplicated()` Boolean bir mask oluşturur.

`df[...]` ise yalnızca True olan satırları seçer.

Şimdi aynı mantığı null `age` kayıtlarını göstermek için nasıl kullanabileceğini düşün.
```

Amaç junior'ın çözümü kopyalaması değil, örnekteki mantığı başka bir durumda uygulayabilmesidir.

---

# Mentor Decision

## Mentor Decision Inputs

Mentor Decision, DataPilot'ın mevcut durumda junior'a hangi seviyede yardım vermesi gerektiğine karar verdiği aşamadır.

Karar yalnızca junior'ın genel seviyesine göre verilmez.

DataPilot aşağıdaki bilgileri birlikte değerlendirir:

```text
Skill State
+
Previous Learning Evidence
+
Current Task
+
Current Question
+
Current Attempt
+
Recent Difficulties
↓
Mentor Decision
↓
Assistance Level
```

---

### 1. Skill State

Junior'ın ilgili skill'deki mevcut durumu dikkate alınır.

Örneğin:

```text
comfortable
→ mümkün olduğunca az yardım

practicing
→ küçük yönlendirme gerekebilir

learning
→ daha fazla rehberlik gerekebilir

new
→ önce mevcut bilgiyi anlamak gerekebilir
```

Skill State tek başına karar vermek için yeterli değildir.

---

### 2. Current Question

DataPilot junior'ın ne sorduğunu anlamaya çalışır.

Küçük ve spesifik bir soru için gereksiz şekilde bütün konu anlatılmamalıdır.

Örneğin:

```text
"Burada neden sum() kullandık?"
```

küçük ve spesifik bir sorudur.

Buna karşılık:

```text
"Null analizi nasıl yapılır hiç bilmiyorum."
```

daha temel bir bilgi eksikliğini gösterir.

Bu durumda daha yüksek assistance level gerekebilir.

---

### 3. Current Attempt

Junior'ın problemi çözmek için yaptığı mevcut deneme dikkate alınır.

Genel yaklaşım:

```text
Junior doğru yaklaşıma çok yakın
↓
NUDGE

Junior yaklaşımı biliyor ancak adımları karıştırıyor
↓
GUIDE

Junior temel kavramı anlamıyor
↓
TEACH

Junior birkaç yönlendirmeye rağmen ilerleyemiyor
↓
DEMONSTRATE
```

Mentor mümkün olduğunca junior'ın mevcut denemesinin üzerine devam eder.

Junior'ın doğru yazdığı kısımlar gereksiz yere yeniden yazılmaz.

---

### 4. Previous Difficulties

DataPilot junior'ın geçmişte aynı veya ilişkili konularda nerelerde zorlandığını dikkate alır.

Örneğin:

```text
Skill:
python_dict

Previous difficulty:
"Dictionary key ile variable/value tarafını karıştırdı."
```

Junior daha sonra şu kodla karşılaşıyorsa:

```python
response_body["recommendations"] = recommendations
```

DataPilot uzun bir dictionary dersi vermek yerine doğrudan kritik noktayı açıklayabilir:

```text
Sol taraf:
"recommendations"
→ dictionary key

Sağ taraf:
recommendations
→ değişkende tutulan value
```

Ancak geçmişte yaşanan her zorluk otomatik olarak tekrar açıklanmaz.

Yalnızca mevcut problemle gerçekten ilgiliyse kullanılır.

---

### 5. Recent Learning Evidence

Junior aynı skill'i son zamanlarda birkaç kez başarılı şekilde kullandıysa mentor desteği azaltılabilir.

Örneğin:

```text
null_analysis

status: practicing
attempts: 6
successful_attempts: 5
recent difficulties: none
```

Bu durumda mentor:

```text
Null analizini yap ve sonucu yorumla.
```

diyebilir.

Junior hatırlamadığını söylerse yardım seviyesi tekrar artırılabilir.

---

## Assistance Escalation

DataPilot mümkün olan en düşük yeterli yardım seviyesini seçmeye çalışır.

Genel yaklaşım:

```text
NUDGE
↓
junior ilerleyemedi
↓
GUIDE
↓
junior hâlâ ilerleyemedi
↓
TEACH
↓
kavram hâlâ oturmadı
↓
DEMONSTRATE
```

Ancak junior:

```text
"Bu kavramı hiç bilmiyorum."
```

diyorsa önce anlamsız NUDGE'lar vermek yerine doğrudan `TEACH` seçilebilir.

---

## Assistance Reduction

Junior geliştikçe yardım seviyesi azaltılır.

Örneğin:

```text
İlk çalışma:

TEACH
↓
GUIDE
↓
junior çözdü
```

Sonraki benzer çalışma:

```text
GUIDE
↓
junior çözdü
```

Daha sonraki çalışma:

```text
NUDGE
↓
junior çözdü
```

Son aşama:

```text
NONE
↓
junior bağımsız çalışır
↓
mentor sonucu review eder
```

Amaç junior'ı sürekli AI yardımına bağımlı hale getirmek değil, zaman içinde AI desteğine daha az ihtiyaç duymasını sağlamaktır.

---

## Response Size Principle

Assistance Level ile cevap uzunluğu aynı şey değildir.

Örneğin junior yalnızca küçük bir syntax sorusu soruyorsa, skill seviyesi düşük olsa bile cevap kısa olabilir.

DataPilot şu prensibi takip eder:

> Sorunun çözülmesi için gereken minimum yeterli açıklamayı ver.

Bu nedenle mentor:

- küçük soruya küçük cevap verir
- temel kavram eksikliğinde daha fazla açıklar
- bilinen konuları tekrar etmez
- aynı anda gereksiz birçok yeni kavram öğretmez
- mevcut problemi junior'ın ihtiyacı olmadan genişletmez

---

# Mentor Decision Architecture

DataPilot mentor kararlarında hybrid bir yaklaşım kullanır.

Mentor davranışı yalnızca sabit backend kurallarıyla veya yalnızca AI kararıyla belirlenmez.

```text
Backend
+
AI Reasoning
↓
Mentor Decision
```

---

## Backend Responsibility

Backend, AI'nın karar verebilmesi için güvenilir ve yapılandırılmış context sağlar.

Backend aşağıdaki bilgileri yönetir:

- Learner Profile
- Skill States
- Learning Preferences
- Attempts
- Successful Attempts
- Previous Difficulties
- Previous Learning Evidence
- Current Session
- Current Task

Örneğin:

```json
{
  "skill": "python_dict",
  "status": "practicing",
  "attempts": 5,
  "successful_attempts": 3,
  "last_difficulty": "Dictionary key ile variable/value tarafını karıştırdı.",
  "answer_length": "concise"
}
```

Backend bu bilgileri saklar ve gerektiğinde AI'ya gönderir.

Backend'in görevi mentor cevabını kendi başına üretmek değildir.

Backend güvenilir learner state'i yönetir.

---

## AI Responsibility

AI, backend tarafından verilen learner state ile mevcut konuşmayı birlikte değerlendirir.

AI şu soruya cevap verir:

> Bu junior'ın mevcut durumda ilerleyebilmesi için gereken minimum yeterli destek nedir?

AI değerlendirmede şunları dikkate alır:

```text
Learner Profile
+
Relevant Skill State
+
Previous Difficulties
+
Current Task
+
Current Question
+
Current Attempt
+
Conversation Context
↓
Mentor Decision
```

AI daha sonra uygun Assistance Level'i seçer:

- `NONE`
- `NUDGE`
- `GUIDE`
- `TEACH`
- `DEMONSTRATE`

AI aynı zamanda:

- cevabın ne kadar uzun olması gerektiğine
- hangi kavramın açıklanması gerektiğine
- soru sorulmasının gerekli olup olmadığına
- örnek verilmesinin gerekli olup olmadığına
- junior'ın kendisinin denemesine fırsat verilmesine

karar verir.

---

## Why AI Makes the Contextual Decision

Her junior aynı değildir.

Örneğin iki junior'ın Skill State'i aynı olabilir:

```text
status = practicing
```

Ancak birincisi:

```text
Mantığı anlıyor
ama syntax hatırlamakta zorlanıyor.
```

İkincisi:

```text
Syntax yazabiliyor
ama kodun neden çalıştığını anlamıyor.
```

Aynı `status` değerine rağmen bu iki junior'a aynı mentor cevabı verilmemelidir.

Bu nedenle backend yalnızca:

```text
if status == "practicing":
    assistance = "GUIDE"
```

gibi katı kurallarla mentor kararını belirlememelidir.

AI mevcut context'i yorumlayarak daha uygun bir karar verebilir.

---

## Backend Guardrails

AI mentor davranışında inisiyatif alabilir ancak belirli temel kurallara uymalıdır.

Örneğin:

- junior'ın bildiği konuları gereksiz yere tekrar öğretme
- küçük sorulara gereksiz uzun cevap verme
- mümkün olduğunda problemi junior'ın çözmesine izin ver
- hemen tam çözüm verme
- junior ilerleyemiyorsa desteği artır
- junior geliştikçe desteği azalt
- aynı anda gereksiz birçok yeni kavram öğretme
- mevcut problemi junior'ın ihtiyacı olmadan genişletme
- learning evidence olmadan bir skill'i `comfortable` kabul etme
- tek bir hata nedeniyle skill seviyesini aşırı düşürme
- tek bir başarı nedeniyle skill seviyesini aşırı yükseltme

Bu kurallar mentor system instructions içinde AI'ya verilir.

---

## Mentor Decision Output

AI'nın yalnızca mentor cevabı üretmesi yerine mentor kararını yapılandırılmış şekilde de döndürmesi planlanır.

Örneğin:

```json
{
  "assistance_level": "GUIDE",
  "relevant_skill": "python_dict",
  "reason": "Junior dictionary mantığını biliyor ancak key ve value tarafını daha önce karıştırmış.",
  "mentor_response": "Sol taraf dictionary key'i, sağ taraf ise recommendations değişkenindeki değerdir."
}
```

Bu yapı sayesinde sistem:

- AI'nın hangi Assistance Level'i seçtiğini
- hangi skill'in ilgili olduğunu
- hangi learning signal'ın kullanıldığını
- kullanıcıya hangi mentor cevabının verildiğini

takip edebilir.

---

## Decision Flow

```text
User Message
↓
Current Session
↓
Relevant Skill Detection
↓
Load Learner Profile
↓
Load Skill State
↓
Load Relevant Learning Evidence
↓
Build Mentor Context
↓
AI Mentor Decision
↓
Assistance Level
+
Mentor Response
↓
User Action
↓
Learning Evidence
↓
Skill State Update
```

Bu yapıda AI mentorun contextual karar mekanizmasıdır.

Backend ise mentorun hafızasını, state'ini ve temel davranış sınırlarını yönetir.

---

# Database Model

Mentor sisteminin öğrenme bilgisi session'lardan bağımsız olarak saklanır.

Bir session geçicidir ancak Learner Profile uzun süreli olmalıdır.

```text
Learner
│
├── Session 1
├── Session 2
├── Session 3
│
└── Learner Profile
    │
    ├── Learning Preferences
    │
    └── Skill States
         │
         └── Learning Evidence
```

Mentor sistemi için V1'de üç temel veri yapısı kullanılır:

```text
learner_profiles
↓
skill_states
↓
learning_evidence
```

---

## `learner_profiles`

Junior'ın genel öğrenme tercihlerini saklar.

Örnek yapı:

```text
learner_id
answer_length
learning_style
code_support
created_at
updated_at
```

Örnek kayıt:

```json
{
  "learner_id": "learner-001",
  "answer_length": "concise",
  "learning_style": "guided",
  "code_support": "medium"
}
```

Bu tablo teknik skill seviyelerini saklamaz.

Amaç mentorun junior'a genel olarak nasıl yaklaşması gerektiğini belirtmektir.

---

## `skill_states`

Junior'ın her teknik skill için mevcut öğrenme durumunu saklar.

Örnek yapı:

```text
id
learner_id
skill_name
status
attempts
successful_attempts
last_difficulty
last_used_at
updated_at
```

Örnek kayıt:

```json
{
  "learner_id": "learner-001",
  "skill_name": "python_dict",
  "status": "practicing",
  "attempts": 5,
  "successful_attempts": 3,
  "last_difficulty": "Dictionary key ile value tarafını karıştırdı."
}
```

Bir learner'ın birçok Skill State'i olabilir.

```text
learner-001
│
├── python_dict       → practicing
├── pandas_dataframe  → comfortable
├── null_analysis     → comfortable
├── outlier_analysis  → learning
└── api_flow          → practicing
```

`learner_id`, `skill_states` kayıtlarını doğru Learner Profile ile ilişkilendirir.

Aynı learner için aynı skill yalnızca bir kez bulunmalıdır.

Örneğin:

```text
learner-001 + python_dict
```

tek bir mevcut Skill State'i temsil eder.

---

## `learning_evidence`

`learning_evidence` tablosu junior'ın bir skill üzerinde yaptığı önemli öğrenme etkileşimlerini saklar.

`skill_states` mevcut durumu özetler.

`learning_evidence` ise bu durumun nasıl oluştuğunu gösterir.

```text
Learning Evidence
↓
zaman içinde birikir
↓
Skill State güncellenir
```

Örneğin:

```text
26 Aug
null_analysis
GUIDE
başarılı

27 Aug
null_analysis
NUDGE
başarılı

29 Aug
null_analysis
NONE
başarılı
```

Bu geçmiş, junior'ın aynı skill üzerinde giderek daha bağımsız çalışabildiğini gösterir.

### Table Structure

V1 için örnek yapı:

```text
id
learner_id
skill_name
assistance_level
success
evidence_type
note
session_id
created_at
```

Örnek kayıt:

```json
{
  "learner_id": "learner-001",
  "skill_name": "null_analysis",
  "assistance_level": "GUIDE",
  "success": true,
  "evidence_type": "application",
  "note": "Null count hesaplamasını küçük bir yönlendirmeden sonra doğru yaptı.",
  "session_id": "session-123"
}
```

---

## Learning Evidence Fields

### `learner_id`

Evidence'ın hangi junior'a ait olduğunu belirtir.

### `skill_name`

Hangi teknik skill hakkında evidence oluştuğunu belirtir.

Örneğin:

```text
python_dict
null_analysis
duplicate_analysis
api_flow
```

### `assistance_level`

Junior'ın ilgili görevi yaparken ne kadar mentor desteği aldığını belirtir.

Olası değerler:

```text
NONE
NUDGE
GUIDE
TEACH
DEMONSTRATE
```

Bu bilgi önemlidir çünkü aynı doğru cevap farklı yardım seviyelerinde farklı anlam taşıyabilir.

Örneğin:

```text
TEACH sonrası doğru yaptı
```

ile:

```text
NONE ile doğru yaptı
```

aynı learning evidence değildir.

### `success`

Junior'ın ilgili adımı başarıyla tamamlayıp tamamlamadığını belirtir.

```text
true
false
```

Tek başına Skill State seviyesini belirlemek için kullanılmaz.

### `evidence_type`

Junior'ın hangi tür davranışından evidence oluştuğunu belirtir.

V1 için:

- `application`
- `explanation`
- `debugging`
- `validation`

Örnek:

```text
application
→ doğru şekilde uyguladı

explanation
→ yaptığı işlemin nedenini doğru açıkladı

debugging
→ hatasını bulup düzeltti

validation
→ sonucunu doğru şekilde kontrol etti
```

### `note`

Evidence'ın kısa teknik açıklamasını saklar.

Örneğin:

```text
"Boolean mask mantığını doğru kullandı."
```

veya:

```text
"Function return değerinin nereden geldiğini tekrar karıştırdı."
```

Bu alan kısa tutulmalıdır.

Amaç bütün konuşmayı veritabanına kopyalamak değildir.

### `session_id`

Evidence'ın hangi çalışma session'ında oluştuğunu takip etmeyi sağlar.

Bu alan learner'ın uzun süreli gelişimi ile belirli konuşma arasındaki bağlantıyı kurar.

### `created_at`

Evidence'ın ne zaman oluştuğunu belirtir.

Bu sayede mentor yalnızca kaç kez başarılı olduğunu değil, gelişimin zaman içinde nasıl ilerlediğini de değerlendirebilir.

---

# Relationships

Mentor sistemindeki temel ilişki:

```text
Learner Profile
│
├── Skill State: python_dict
│   ├── Evidence 1
│   ├── Evidence 2
│   └── Evidence 3
│
├── Skill State: null_analysis
│   ├── Evidence 1
│   └── Evidence 2
│
└── Skill State: debugging
    └── Evidence 1
```

Bir Learner Profile'ın birçok Skill State'i olabilir.

Bir Skill State için zaman içinde birçok Learning Evidence oluşabilir.

---

# Why Evidence Matters

DataPilot yalnızca doğru cevap sayısını ölçmez.

Junior'ın bağımsızlık seviyesini de takip eder.

Örneğin:

```text
TEACH
↓
başardı

GUIDE
↓
başardı

NUDGE
↓
başardı

NONE
↓
başardı
```

bu sıra güçlü bir gelişim sinyalidir.

Ama:

```text
TEACH
↓
başardı

TEACH
↓
başardı

TEACH
↓
başardı
```

junior'ın görevi yapabildiğini ancak hâlâ yüksek mentor desteğine ihtiyaç duyduğunu gösterebilir.

DataPilot'ın amacı yalnızca başarı sayısını artırmak değil, zaman içinde gerekli mentor desteğini azaltmaktır.

---

# Skill State Update

`skill_states.status`, Learning Evidence biriktikçe zaman içinde güncellenir.

DataPilot skill seviyesini yalnızca doğru cevap sayısına göre değiştirmez.

Değerlendirmede aşağıdaki sinyaller birlikte kullanılır:

```text
Success
+
Assistance Level
+
Evidence Type
+
Recent Attempts
+
Previous Difficulties
+
Ability to Explain
+
Ability to Validate
↓
Suggested Skill State
```

---

## Status Meaning

### `new`

Skill hakkında henüz yeterli evidence yoktur.

Bu durum junior'ın skill'i kesinlikle bilmediği anlamına gelmez.

```text
new
=
unknown / not enough evidence
```

---

### `learning`

Junior temel kavramı öğrenmektedir ve genellikle daha yüksek mentor desteğine ihtiyaç duymaktadır.

Örnek:

```text
TEACH
↓
uyguladı

DEMONSTRATE
↓
benzer görevi yapabildi
```

Junior ilerleme gösteriyor olabilir ancak henüz bağımsız değildir.

---

### `practicing`

Junior skill'i uygulayabilmektedir ancak zaman zaman yönlendirme veya hatırlatmaya ihtiyaç duyabilir.

Örnek:

```text
GUIDE → başarılı
NUDGE → başarılı
NUDGE → başarılı
```

Junior temel mantığı biliyor ancak henüz tamamen bağımsız değildir.

---

### `comfortable`

Junior skill'i farklı durumlarda büyük ölçüde bağımsız şekilde kullanabilmektedir.

Örnek evidence:

```text
NONE → application → başarılı
NONE → explanation → başarılı
NUDGE → debugging → başarılı
NONE → validation → başarılı
```

`comfortable` yalnızca syntax hatırlamak anlamına gelmez.

Junior ayrıca:

- ne yaptığını
- neden yaptığını
- ne zaman kullanacağını
- sonucunu nasıl kontrol edeceğini

büyük ölçüde anlayabilmelidir.

---

## Status Is an Estimate

Skill State kesin ve değişmez bir gerçek değildir.

DataPilot'ın mevcut Learning Evidence'a dayanarak oluşturduğu en iyi tahmindir.

Örneğin `comfortable` olan bir junior uzun süre bir skill'i kullanmaz ve daha sonra tekrar zorlanırsa:

```text
comfortable
↓
practicing
```

şeklinde güncellenebilir.

Bu bir başarısızlık değildir.

Skill State yalnızca mevcut mentor desteğini doğru ayarlamak için kullanılır.

---

## Flexible Progression

Junior'ın mutlaka şu sırayı tek tek geçmesi gerekmez:

```text
new
↓
learning
↓
practicing
↓
comfortable
```

Yeni bir kullanıcı bazı konuları zaten biliyor olabilir.

Örneğin DataPilot ilk kez şu güçlü evidence'ı görürse:

```text
skill: sql_joins
assistance: NONE
application: successful
explanation: successful
validation: successful
```

junior'ı gereksiz şekilde `learning` seviyesinde tutmamalıdır.

Yeterli güçlü evidence varsa Skill State daha yüksek bir seviyeye geçebilir.

---

## Update Responsibility

Skill State güncellemesi hybrid bir sistem kullanır.

```text
Learning Evidence
↓
AI evaluates evidence
↓
AI suggests skill state
↓
Backend applies guardrails
↓
Skill State updated
```

AI evidence'ı yorumlayabilir.

Örneğin:

```json
{
  "skill": "null_analysis",
  "suggested_status": "practicing",
  "reason": "Junior son üç uygulamanın ikisini yalnızca NUDGE ile doğru tamamladı ve null count mantığını doğru açıkladı."
}
```

Ancak AI veritabanındaki Skill State'i doğrudan kontrolsüz şekilde değiştirmez.

Backend:

- status değerinin geçerli olup olmadığını kontrol eder
- yeterli evidence olup olmadığını kontrol eder
- güncellemeyi veritabanına kaydeder

---

## Avoid Overreacting

Tek bir interaction skill seviyesini gereksiz şekilde değiştirmemelidir.

Örneğin:

```text
comfortable
+
bir hata yaptı
```

otomatik olarak:

```text
learning
```

anlamına gelmez.

Benzer şekilde:

```text
new
+
bir doğru cevap
```

otomatik olarak:

```text
comfortable
```

anlamına gelmez.

DataPilot mümkün olduğunca zaman içindeki pattern'e bakar.

---

# Independence Signal

Skill gelişimindeki en önemli sinyallerden biri junior'ın ihtiyaç duyduğu mentor desteğinin azalmasıdır.

Örneğin:

```text
TEACH
↓
GUIDE
↓
NUDGE
↓
NONE
```

aynı veya benzer skill üzerinde zaman içinde görülüyorsa junior'ın bağımsızlığının arttığı düşünülebilir.

DataPilot'ın temel başarı ölçütlerinden biri:

> Junior aynı tür problemi giderek daha az mentor desteğiyle çözebiliyor mu?

sorusudur.

---

# Core Product Principle

DataPilot'ın başarısı junior'ın AI'ya daha fazla bağımlı hale gelmesiyle ölçülmez.

Başarı:

```text
Daha iyi anlayış
+
Daha doğru teknik kararlar
+
Daha fazla bağımsız uygulama
+
Daha iyi debugging
+
Daha iyi validation
+
Daha az gerekli mentor desteği
```

ile ölçülür.

DataPilot'ın nihai amacı:

> Junior'ın işi AI'ya yaptırmasını sağlamak değil, zaman içinde işi güvenle ve giderek daha bağımsız şekilde yapabilmesini sağlamaktır.


# Mentor System MVP

İlk MVP'nin amacı adaptif mentor mantığının gerçekten çalıştığını kanıtlamaktır.

MVP şu akışı destekler:

```text
User Message
↓
Relevant Skill Detection
↓
Load Learner Profile
↓
Load Skill State
↓
Select Assistance Level
↓
Generate Mentor Response
↓
Save Learning Evidence