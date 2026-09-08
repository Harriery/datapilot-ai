# DataPilot AI — Product Roadmap

## Amaç
DataPilot AI, junior data engineer'ların veri mühendisliği görevlerini anlamasına, planlamasına, uygulamasına ve kontrol etmesine yardımcı olan öğretici bir AI asistanı olarak geliştirilecektir.

Bu roadmap, projeyi gereksiz yere büyütmeden adım adım gerçek kullanım değerine taşıyacak ana yönü tanımlar.

---

## V1 — Standalone Junior Data Engineer Assistant

**Hedef:** Portföyde sunulabilecek, çalışan ve faydalı bağımsız bir uygulama.

Ana bileşenler:
- FastAPI backend
- AI chat
- Session ve conversation history
- TXT/PDF document upload
- Chunking
- Embeddings
- Semantic retrieval
- RAG tabanlı belge cevaplama
- RAG + session/history entegrasyonu
- CSV upload ve temel data profiling
- Null, duplicate, schema ve data type kontrolleri
- Data cleaning / transformation önerileri
- SQL, Python ve PySpark konusunda öğretici yardım
- ETL/ELT ve Bronze/Silver/Gold workflow rehberliği
- Basit frontend
- Testler
- README ve architecture dokümantasyonu

**Rolü:**  
Junior data engineer'a sadece kod vermek yerine, hangi adımları hangi sırayla ve neden takip etmesi gerektiğini açıklayan mentor/copilot.

---

## V2 — Azure Deployment

**Hedef:** DataPilot'ı localhost'tan çıkarıp gerçek bir web uygulaması haline getirmek.

Plan:
- Backend'i Azure üzerinde deploy etmek
- Environment variables / secrets yönetimi
- Uygulamanın internet üzerinden erişilebilir olması
- Gerekirse production database'e geçiş
- Logging ve temel monitoring

**Sonuç:**  
DataPilot bağımsız çalışan gerçek bir cloud application olur.

---

## V3 — Microsoft Entra + Fabric REST API Integration

**Hedef:** DataPilot'ın sadece yol gösteren bir asistan olmaktan çıkıp Microsoft Fabric workspace ile kontrollü şekilde etkileşebilmesi.

Potansiyel yetenekler:
- Microsoft Entra ile authentication
- Fabric workspace metadata'sını okumak
- Mevcut Lakehouse / Notebook / Pipeline yapılarını incelemek
- Kullanıcıya mevcut ortama göre öneri vermek
- Notebook taslağı oluşturmak
- Pipeline oluşturma veya yönetme işlemlerini Fabric REST API üzerinden yapmak

Örnek:

```text
Junior:
"Bu workspace'te customer verisini Silver katmana nasıl taşımalıyım?"

DataPilot:
"Bronze_Customers mevcut.
Silver_Customers notebook'u var.
Önce mevcut notebook'u inceleyelim ve data quality kontrollerini doğrulayalım."
```

**Sonuç:**  
DataPilot gerçek çalışma ortamını anlayan bir Data Engineering assistant'a dönüşür.

---

## V4 — Fabric Extensibility Toolkit / Custom Workload

**Hedef:** DataPilot'ı Microsoft Fabric deneyiminin içine entegre etmek.

Potansiyel yapı:

```text
Microsoft Fabric
│
├── Lakehouse
├── Notebook
├── Pipeline
├── Dataflow
│
└── DataPilot AI
    ├── Pipeline açıklama
    ├── Dataset analizi
    ├── Silver/Gold önerileri
    ├── Notebook taslağı
    └── Pipeline yardımı
```

Bu aşamada DataPilot bağımsız bir web uygulamasından daha ileri giderek Fabric içinde özel bir workload / extension experience haline gelebilir.

---

## Geliştirme Prensibi

Her aşama bir önceki aşama tamamlandıktan sonra ele alınacaktır.

```text
V1
Standalone Junior Data Engineer Assistant
↓
V2
Azure Deployment
↓
V3
Fabric REST API Integration
↓
V4
Fabric Custom Workload
```

Öncelik her zaman çalışan, anlaşılır ve test edilebilir bir ürün oluşturmaktır. Advanced özellikler temel ürün tamamlanmadan eklenmeyecektir.

---

## Şu Anki Odak

Şu anda **V1 — Standalone Junior Data Engineer Assistant** geliştirilmektedir.

V1'in temel ürün yapısı üç ana kullanıcı alanından oluşacaktır:

```text
DataPilot
│
├── Workspace
│   └── Gerçek Data Engineering görevleri
│
├── Practice
│   └── Kişiselleştirilmiş skill geliştirme ve challenge'lar
│
└── Progress
    └── Learner skill gelişimi ve bağımsızlık seviyesi
```

### Temel ürün prensibi

Workspace sırasında amaç junior'a mümkün olan en fazla eğitimi vermek değildir.

Amaç:

```text
minimum interruption
+
minimum sufficient help
+
real work validation
```

ile junior'ın gerçek işi mümkün olduğunca kendisinin yapmasını sağlamaktır.

Derin öğrenme ve ek alıştırmalar ayrı **Practice** alanında yapılacaktır.

Böylece gerçek çalışma sırasında junior gereksiz eğitim soruları ile yavaşlatılmaz; ancak çalışma sırasında tespit edilen eksikler kaybolmaz ve daha sonra hedefli challenge'lara dönüştürülebilir.

---

## V1 Implementation Phases

### Phase 1 — Adaptive Data Quality Mentor

**Status: Completed**

* Data quality findings
* Issue → skill mapping
* Learner skill state
* Assistance levels
* Junior attempt evaluation
* Learning evidence
* Adaptive mentor response

---

### Phase 2 — Deterministic Transformation Validation

**Status: Completed**

* Reusable DataFrame profiling
* Missing-values validation
* Duplicate-rows validation
* Before/after DataFrame comparison
* Validation → learning evidence
* Skill status update
* Transformation API

Başarı kararı mümkün olduğunda AI tarafından tahmin edilmez.

```text
before data
+
after data
↓
backend validation
↓
success / failure
```

---

### Phase 3 — Multi-Step Data Engineering Tasks

**Status: In Progress**

Amaç gerçek bir Data Engineering problemini tek cevap yerine sıralı task step'leri olarak yönetmektir.

```text
Task
│
├── Step 1 → active
├── Step 2 → pending
└── Step 3 → pending
```

Junior mevcut step'i başarıyla tamamlamadan sonraki step aktif olmaz.

Akış:

```text
current step
↓
junior transformation
↓
before / after validation
↓
success?
├── no  → aynı step
└── yes → current step completed
          next step active
```

Sonraki çalışmalar:

* task progression ile learner evidence sistemini tam birleştirmek
* task response modelleri
* task API
* task state persistence

---

### Phase 4 — Learner Progress / Profile

Junior'ın farklı skill'lerdeki gelişimini görünür hale getirmek.

Örnek:

```text
null_analysis       → practicing
duplicate_analysis  → comfortable
python_data_structures → learning
sql_joins           → learning
```

Workspace ve Practice aynı learner profile'ını kullanacaktır.

---

### Phase 5 — Adaptive Practice & Challenges

Detaylı Practice mimarisi için:
`docs/architecture/practice-system.md` 


Workspace sırasında gözlemlenen teknik eksiklere göre kişisel Practice önerileri oluşturmak.

Örnek skill alanları:

* Python data structures
* Pandas
* SQL
* SQL joins
* data quality
* transformation logic
* debugging
* schema analysis
* Data Engineering workflow concepts

Challenge difficulty junior'ın gerçek learning evidence'ına göre adapte edilecektir.

```text
skill status
+
recent attempts
+
success rate
+
assistance level
+
repeated difficulties
↓
next challenge difficulty
```

Practice alanı gerektiğinde daha öğretici olabilir.

Workspace ise gerçek işi gereksiz yere derse dönüştürmez.

---

### Phase 6 — Frontend

Frontend yalnızca backend endpoint'lerinin görsel karşılığı olmayacaktır.

Ana ürün deneyimi:

```text
Workspace
Practice
Progress
```

üzerine kurulacaktır.

Öncelikler:

* temiz ve profesyonel görünüm
* açık information hierarchy
* tek ana aksiyona odaklanan ekranlar
* dataset / task / mentor / progress ilişkisini kolay anlaşılır göstermek
* hazır dashboard template görünümünden kaçınmak
* tekrar kullanılabilir UI primitives kullanırken DataPilot'a özgü bir ürün dili oluşturmak

---

### Phase 7 — Portfolio & Demo Polish

* hazır demo dataset
* 2 dakikalık demo senaryosu
* README
* architecture diagrams
* product explanation
* İngilizce / Hollandaca kısa proje anlatımı
* CV ve LinkedIn proje açıklaması
* interview demo flow
* deployment hazırlığı

V1 tamamlandığında DataPilot yalnızca çalışan bir backend değil, junior Data Engineer'ın gerçek çalışma ve öğrenme döngüsünü gösterebilen portföy seviyesinde bir ürün olacaktır.
