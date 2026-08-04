# RAG Akışı

## Amaç

Bu akış, kullanıcının yüklediği bir belge hakkında soru sormasını ve yalnızca belge içeriğine dayanan bir cevap almasını sağlar.

RAG iki temel işlemi birleştirir:

1. **Retrieval:** Soruyla en ilgili belge parçalarını bulur.
2. **Generation:** Bulunan parçaları kullanarak cevap üretir.

```text
Kullanıcı sorusu
↓
İlgili chunk'ları bulma
↓
Context oluşturma
↓
OpenAI ile cevap üretme
↓
Cevap ve kaynakları döndürme
```

---

## Kullanılan Endpoint

```http
POST /documents/{document_id}/ask
```

### Request body

```json
{
  "question": "Bu belgede veriler nasıl temizleniyor?",
  "top_k": 2
}
```

### Response örneği

```json
{
  "document_id": 2,
  "question": "Bu belgede veriler nasıl temizleniyor?",
  "answer": "Belgede verilerin temizlenmesi için...",
  "sources": [
    {
      "chunk_index": 1,
      "content": "Veri temizleme işlemleri...",
      "similarity": 0.82
    }
  ]
}
```

---

## İlgili Dosyalar

| Dosya | Sorumluluk |
|---|---|
| `document_routes.py` | `/ask` endpoint'ini yönetir ve bütün RAG akışını başlatır. |
| `database.py` | Belgeyi ve belgeye ait chunk'ları SQLite veritabanından getirir. |
| `embedding_service.py` | Kullanıcının sorusunu embedding'e dönüştürür. |
| `retrieval_service.py` | Soru embedding'i ile chunk embedding'lerini karşılaştırır. |
| `rag_service.py` | Context oluşturur ve OpenAI üzerinden cevap üretir. |
| `models.py` | `question` ve `top_k` alanlarını doğrulayan request modelini içerir. |

---

## Genel Kontrol Akışı

```text
document_routes.py
ask_document()
    ↓
database.py
get_document_by_id()
    ↓
database.py
get_chunks_by_document()
    ↓
embedding_service.py
create_embedding()
    ↓
retrieval_service.py
find_relevant_chunks()
    ↓
rag_service.py
build_context()
    ↓
rag_service.py
generate_answer()
    ↓
document_routes.py
JSON response
```

---

## 1. Belge Kontrolü

Akış `document_routes.py` içindeki `ask_document()` fonksiyonunda başlar.

```python
document = get_document_by_id(document_id)
```

URL üzerinden gelen `document_id` ile belge veritabanında aranır.

Belge bulunamazsa endpoint şu hatayı döndürür:

```http
404 Not Found
```

```json
{
  "detail": "Belge bulunamadı."
}
```

Bu kontrol, var olmayan bir belge için retrieval işlemi yapılmasını engeller.

---

## 2. Sorunun Temizlenmesi

Request içindeki soru alınır:

```python
question = request.question.strip()
```

`strip()` metoduyla sorunun başındaki ve sonundaki gereksiz boşluklar temizlenir.

Soru boşsa endpoint şu hatayı döndürür:

```http
400 Bad Request
```

```json
{
  "detail": "Soru boş olamaz."
}
```

---

## 3. Belge Chunk'larının Getirilmesi

Belgeye ait bütün chunk'lar veritabanından alınır:

```python
chunks = get_chunks_by_document(document_id)
```

Her chunk aşağıdaki yapıya sahiptir:

```python
{
    "chunk_index": 0,
    "content": "Belgeden alınan metin parçası.",
    "embedding": [0.12, -0.08, 0.31]
}
```

Veritabanında JSON metni olarak saklanan embedding, `json.loads()` ile tekrar Python listesine dönüştürülür.

---

## 4. Soru Embedding'inin Oluşturulması

Kullanıcının sorusu embedding'e dönüştürülür:

```python
question_embedding = create_embedding(question)
```

Sonuç bir sayı listesidir:

```python
[0.14, -0.03, 0.27]
```

Bu vektör, sorunun anlamsal temsilidir.

```text
"Veriler nasıl temizleniyor?"
↓
OpenAI Embedding API
↓
[0.14, -0.03, 0.27, ...]
```

---

## 5. İlgili Chunk'ların Bulunması

Soru embedding'i ile belge chunk'larının embedding'leri karşılaştırılır:

```python
relevant_chunks = find_relevant_chunks(
    question_embedding=question_embedding,
    chunks=chunks,
    top_k=request.top_k,
)
```

`find_relevant_chunks()` fonksiyonu her chunk için şu işlemleri yapar:

1. Soru ve chunk embedding'leri arasında cosine similarity hesaplar.
2. Chunk'a similarity puanı ekler.
3. Sonuçları en yüksek puandan en düşük puana sıralar.
4. İlk `top_k` sonucu döndürür.

Örnek sonuç:

```python
[
    {
        "chunk_index": 2,
        "content": "Eksik değerler doldurulur...",
        "similarity": 0.82,
    },
    {
        "chunk_index": 4,
        "content": "Geçersiz kayıtlar filtrelenir...",
        "similarity": 0.71,
    },
]
```

Similarity puanı cevabın doğruluk yüzdesi değildir. Chunk'ların soruyla olan anlamsal yakınlığını karşılaştırmak için kullanılır.

---

## 6. Context Oluşturulması

Bulunan ilgili chunk metinleri tek bir metinde birleştirilir:

```python
context = build_context(
    relevant_chunks=relevant_chunks
)
```

`build_context()` yalnızca chunk'ların `content` alanlarını kullanır:

```python
context_parts = []

for chunk in relevant_chunks:
    content = chunk["content"]
    context_parts.append(content)

context = "\n\n".join(context_parts)
```

Örnek:

```text
Eksik değerler uygun yöntemlerle doldurulur.

Geçersiz kayıtlar ve tekrar eden satırlar filtrelenir.
```

İki satır sonu kullanılması, farklı chunk'ların birbirinden ayrılmasını sağlar.

---

## 7. Belgeye Dayalı Cevap Üretilmesi

Soru ve context, `generate_answer()` fonksiyonuna gönderilir:

```python
answer = generate_answer(
    question=question,
    context=context,
)
```

Fonksiyon OpenAI'ye iki temel bilgi verir:

```text
Belge bağlamı:
{context}

Kullanıcının sorusu:
{question}
```

Model talimatı:

```text
Yalnızca verilen belge bağlamına dayanarak cevap ver.
Cevap bağlamda yoksa bunu açıkça belirt.
```

OpenAI cevabı bir Response nesnesi içinde döner:

```python
response = client.responses.create(...)
```

Üretilen metin şu alan üzerinden alınır:

```python
response.output_text
```

`generate_answer()` sonuç olarak bir string döndürür:

```python
"Belgede eksik değerlerin doldurulduğu ve geçersiz kayıtların filtrelendiği açıklanmaktadır."
```

---

## 8. Endpoint Cevabının Döndürülmesi

Son olarak endpoint şu bilgileri JSON olarak döndürür:

```python
return {
    "document_id": document_id,
    "question": question,
    "answer": answer,
    "sources": relevant_chunks,
}
```

Alanların görevleri:

| Alan | Açıklama |
|---|---|
| `document_id` | Sorunun hangi belgeye yöneltildiğini gösterir. |
| `question` | Temizlenmiş kullanıcı sorusudur. |
| `answer` | Belge bağlamına dayanarak üretilen cevaptır. |
| `sources` | Cevabın oluşturulmasında kullanılan chunk'ları gösterir. |

`sources` alanı sayesinde kullanıcı cevabın hangi belge parçalarına dayandığını görebilir.

---

## Tam RAG Akışı

```text
POST /documents/{document_id}/ask
↓
ask_document()
↓
Belge mevcut mu?
├── Hayır → 404
└── Evet
    ↓
Soru boş mu?
├── Evet → 400
└── Hayır
    ↓
Belge chunk'larını getir
↓
Sorunun embedding'ini oluştur
↓
Her chunk ile cosine similarity hesapla
↓
En ilgili top_k chunk'ı seç
↓
Chunk içeriklerini context olarak birleştir
↓
Soru + context ile OpenAI cevabı üret
↓
answer + sources döndür
```

---

## Retrieval ve Generation Arasındaki Fark

### Retrieval

Retrieval bölümünün görevi cevap yazmak değildir.

Görevi:

```text
Soruyu anlamlandır
↓
Belgedeki en ilgili parçaları bul
↓
Bu parçaları sırala
```

İlgili fonksiyonlar:

```python
create_embedding()
find_relevant_chunks()
cosine_similarity()
```

### Generation

Generation bölümünün görevi bulunan kaynak parçalarını kullanarak doğal dilde cevap üretmektir.

İlgili fonksiyonlar:

```python
build_context()
generate_answer()
```

Birlikte çalıştıklarında RAG sistemi oluşur:

```text
Retrieval + Augmented Context + Generation
```

---

## Testler

### `test_build_context_combines_chunk_contents`

Bu test, ilgili chunk içeriklerinin doğru sırayla birleştirildiğini kontrol eder.

```text
Chunk 1 + Chunk 2
↓
"Chunk 1\n\nChunk 2"
```

### `test_generate_answer_returns_output_text`

Bu test gerçek OpenAI çağrısı yapmaz.

```python
patch(
    "backend.app.rag_service.client.responses.create"
)
```

Sahte bir OpenAI Response nesnesi oluşturulur ve `output_text` alanının doğru döndürüldüğü kontrol edilir.

### `test_ask_uploaded_document`

Bu test bütün `/ask` endpoint akışını kontrol eder.

Test sırasında şu fonksiyonlar mock edilir:

```python
create_embeddings()
create_embedding()
generate_answer()
```

Test akışı:

```text
Sahte embedding ile TXT belge yükle
↓
document_id al
↓
Sahte soru embedding'i oluştur
↓
Sahte AI cevabı oluştur
↓
POST /documents/{document_id}/ask
↓
Status code 200 mü?
↓
answer alanı beklenen cevap mı?
```

Mock kullanılması sayesinde:

- Gerçek OpenAI çağrısı yapılmaz.
- API maliyeti oluşmaz.
- Test internet bağlantısına bağlı olmaz.
- Test sonucu her çalıştırmada aynı olur.

---