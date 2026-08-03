# Retrieval Akışı

## Amaç

Kullanıcının sorusuna anlam olarak en yakın belge parçalarını (**chunk**) bulmak.

Retrieval katmanı cevap üretmez. Görevi, veritabanındaki chunk’ları karşılaştırarak soruyla en ilgili olanları seçmektir.

---

## Dosyaların sorumlulukları

### `retrieval_service.py`

- Soru embedding’i ile chunk embedding’ini karşılaştırır.
- Her chunk için bir benzerlik puanı hesaplar.
- Chunk’ları benzerlik puanına göre sıralar.
- En ilgili ilk `top_k` chunk’ı geri döndürür.

### `embedding_service.py`

- Kullanıcının sorusunu embedding vektörüne dönüştürür.
- `create_embedding()` fonksiyonu tek bir metin alır.
- Sonuç olarak `list[float]` döndürür.

### `database.py`

- Belgeye ait chunk’ları SQLite veritabanından getirir.
- Veritabanında JSON metni olarak saklanan embedding’i tekrar Python listesine dönüştürür.

### `document_routes.py`

- Arama isteğini karşılar.
- Belgenin var olup olmadığını kontrol eder.
- Kullanıcının sorusunu alır.
- Belgenin chunk’larını getirir.
- Retrieval fonksiyonlarını çağırır.
- En ilgili chunk’ları JSON cevabı olarak döndürür.

---

## Temel kavramlar

### Soru embedding’i

```text
question_embedding
→ Kullanıcının sorusunun sayı listesine dönüştürülmüş hâli
```

Örnek:

```python
question_embedding = create_embedding(
    "Bu kodda veriler nasıl temizleniyor?"
)
```

### Chunk embedding’i

```text
chunk_embedding
→ Veritabanındaki tek bir chunk’ın sayı listesi
```

Örnek chunk:

```python
chunk = {
    "chunk_index": 0,
    "content": "Veri temizleme işlemleri...",
    "embedding": [0.12, -0.04, 0.08],
}
```

Chunk embedding’ine şu şekilde erişilir:

```python
chunk_embedding = chunk["embedding"]
```

---

## `cosine_similarity()` fonksiyonu

`cosine_similarity()` fonksiyonu bir soru embedding’i ile bir chunk embedding’i arasındaki yön benzerliğini hesaplar.

```python
similarity = cosine_similarity(
    question_embedding,
    chunk_embedding,
)
```

Fonksiyon bir `float` değer döndürür:

```text
1.0
→ Aynı yön, çok yüksek benzerlik

0.0
→ Belirgin bir yön benzerliği yok

-1.0
→ Zıt yön
```

> Benzerlik puanı, cevabın yüzde kaç doğru olduğunu göstermez. Chunk’ları kendi aralarında sıralamak için kullanılır.

---

## Cosine similarity işlem sırası

```text
1. Aynı index’teki sayılar eşleştirilir
              ↓
2. Eşleşen sayılar çarpılır
              ↓
3. Çarpımlar toplanır
   dot_product oluşur
              ↓
4. Soru embedding’inin büyüklüğü hesaplanır
              ↓
5. Chunk embedding’inin büyüklüğü hesaplanır
              ↓
6. Benzerlik puanı hesaplanır
```

Formül:

```text
similarity =
dot_product /
(question_magnitude × chunk_magnitude)
```

### Küçük örnek

```python
question_embedding = [1, 2]
chunk_embedding = [2, 4]
```

Aynı index’teki değerler eşleştirilir:

```text
1 ↔ 2
2 ↔ 4
```

Çarpım toplamı:

```text
dot_product
= (1 × 2) + (2 × 4)
= 10
```

Vektör büyüklükleri:

```text
question_magnitude = √5
chunk_magnitude = √20
```

Benzerlik:

```text
similarity
= 10 / (√5 × √20)
= 1.0
```

Bu iki vektör aynı yöne baktığı için benzerlik puanı `1.0` olur.

---

## `find_relevant_chunks()` fonksiyonu

`cosine_similarity()` yalnızca **bir soru embedding’i ile bir chunk embedding’ini** karşılaştırır.

`find_relevant_chunks()` ise belgedeki bütün chunk’ları gezer.

Fonksiyonun aldığı veriler:

```text
question_embedding
→ Kullanıcının sorusunun embedding’i

chunks
→ Belgeye ait bütün chunk’lar

top_k
→ Kaç tane en ilgili chunk döndürülecek?
```

Fonksiyon çağrısı:

```python
relevant_chunks = find_relevant_chunks(
    question_embedding=question_embedding,
    chunks=chunks,
    top_k=request.top_k,
)
```

### İşlem sırası

```text
question_embedding
              ↓
chunk 0 ile karşılaştır → similarity puanı
chunk 1 ile karşılaştır → similarity puanı
chunk 2 ile karşılaştır → similarity puanı
              ↓
Puanları scored_chunks listesine ekle
              ↓
Similarity değerine göre yüksekten düşüğe sırala
              ↓
İlk top_k sonucu döndür
```

### Puanlanmış chunk örneği

```python
{
    "chunk_index": 0,
    "content": "Veri temizleme işlemleri...",
    "similarity": 0.81,
}
```

### Sıralama

```python
sorted_chunks = sorted(
    scored_chunks,
    key=lambda chunk: chunk["similarity"],
    reverse=True,
)
```

Burada:

```text
key=lambda chunk: chunk["similarity"]
→ Her chunk’ın similarity değerine bakar

reverse=True
→ Büyük puandan küçük puana sıralar
```

En iyi sonuçlar:

```python
return sorted_chunks[:top_k]
```

`top_k = 3` ise yalnızca ilk üç chunk döndürülür.

---

## Search endpoint akışı

Endpoint:

```text
POST /documents/{document_id}/search
```

Örnek istek:

```json
{
  "question": "Bu kodda veriler nasıl temizleniyor?",
  "top_k": 2
}
```

### İşlem sırası

```text
1. Kullanıcı search endpoint’ine soru gönderir
              ↓
2. document_routes.py
   search_document() çalışır
              ↓
3. get_document_by_id(document_id)
   Belgenin varlığı kontrol edilir
              ↓
4. request.question.strip()
   Soru temizlenir ve boş olup olmadığı kontrol edilir
              ↓
5. get_chunks_by_document(document_id)
   Belgenin chunk’ları veritabanından alınır
              ↓
6. create_embedding(question)
   Kullanıcının sorusu embedding’e çevrilir
              ↓
7. find_relevant_chunks(...)
   Soru bütün chunk’larla karşılaştırılır
              ↓
8. En ilgili top_k chunk seçilir
              ↓
9. JSON cevap kullanıcıya döndürülür
```

### Dosyalar arası akış

```text
document_routes.py
search_document()
        ↓
database.py
get_document_by_id()
get_chunks_by_document()
        ↓
embedding_service.py
create_embedding(question)
        ↓
retrieval_service.py
find_relevant_chunks()
        ↓
retrieval_service.py
cosine_similarity()
        ↓
document_routes.py
JSON cevap
```

---

## Endpoint cevabı

Örnek cevap:

```json
{
  "document_id": 2,
  "question": "Bu kodda veriler nasıl temizleniyor?",
  "results": [
    {
      "chunk_index": 0,
      "content": "Veri temizleme ve dönüşüm işlemleri...",
      "similarity": 0.49
    },
    {
      "chunk_index": 1,
      "content": "Veri zenginleştirme işlemleri...",
      "similarity": 0.31
    }
  ]
}
```

Burada:

```text
document_id
→ Arama yapılan belge

question
→ Kullanıcının gönderdiği temizlenmiş soru

results
→ Benzerlik puanına göre sıralanan chunk’lar
```

---

## Testler

### `test_retrieval.py`

Bu testler şunları doğrular:

- Aynı yöndeki embedding’lerin benzerlik puanının `1.0` olması.
- Chunk’ların similarity değerine göre doğru sıralanması.
- `top_k` kadar sonuç döndürülmesi.

### `test_documents.py`

Search endpoint testi şu akışı doğrular:

```text
Sahte chunk embedding’i
→ [1.0, 0.0]

Sahte soru embedding’i
→ [1.0, 0.0]

cosine_similarity()
→ 1.0

find_relevant_chunks()
→ İlgili chunk ilk sırada

Search endpoint
→ 200 cevabı
```

Gerçek OpenAI isteği göndermemek için `create_embedding()` ve `create_embeddings()` fonksiyonları test sırasında `mock` ile değiştirilir.

---

## Retrieval ve RAG arasındaki fark

```text
Retrieval
→ Kullanıcının sorusuyla ilgili bilgileri bulur.

Generation
→ Bulunan bilgileri kullanarak cevap üretir.
```

Birlikte:

```text
Retrieval-Augmented Generation
→ RAG
```

Şu anda tamamlanan bölüm:

```text
Soru
→ Soru embedding’i
→ Chunk karşılaştırması
→ Benzerlik puanları
→ En ilgili chunk’ların seçilmesi
```

Sıradaki aşama:

```text
Kullanıcının sorusu
+
En ilgili chunk metinleri
              ↓
OpenAI’ye bağlam olarak gönderilir
              ↓
Belgeye dayalı cevap üretilir
```