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

Şu anda **V1** geliştirilmektedir.

Mevcut durumda tamamlanan ana parçalar:
- FastAPI
- SQLite
- Session
- Chat history
- TXT/PDF upload
- Chunking
- Embeddings
- Semantic retrieval
- RAG answer
- Testler
- Temel hata yönetimi

Bir sonraki ana adımlar:
1. RAG + session/history entegrasyonu
2. CSV upload ve data profiling
3. Data Engineer odaklı assistant davranışının güçlendirilmesi
4. Basit frontend
5. V1 test ve dokümantasyonunun tamamlanması
