# Data AI Recommendation Flow

DataPilot AI, CSV profiling sonucunu kullanarak
Data Engineering odaklı veri kalitesi ve transformation önerileri üretir.

## Flow

CSV
↓
Data Profiling
↓
Profile Dictionary
↓
Prompt Preparation
↓
OpenAI Responses API
↓
AI Recommendations
↓
API Response

Buradaki çok önemli ayrım:

pandas
→ veride NE VAR onu bulur

AI
→ bulunan bilgilerin NE ANLAMA GELEBİLECEĞİNİ yorumlar

Örneğin:

Pandas:
age max = 999

AI:
999 şüpheli olabilir,
ama domain bilgisi olmadan hatalı kabul edilmemeli.


## 1. Profile Dictionary

CSV dosyası önce `data_routes.py` içinde pandas ile analiz edilir.

Bu analiz sonucunda tek bir `profile` dictionary oluşturulur.

Profile içinde örneğin şu bilgiler bulunur:

- `row_count`
- `column_count`
- `columns`
- `data_types`
- `null_counts`
- `duplicate_count`
- `sample_rows`
- `numeric_columns`
- `numeric_summary`

Örnek:

```json
{
  "row_count": 4,
  "null_counts": {
    "age": 1
  },
  "duplicate_count": 1,
  "numeric_summary": {
    "age": {
      "mean": 353,
      "min": 30,
      "max": 999
    }
  }
}

Bu profile, AI'nın doğrudan CSV dosyasını değil,
önceden çıkarılmış yapılandırılmış veri özetini analiz etmesini sağlar.


Buradaki ana fikir şu:

```text
CSV'nin tamamı
↓
AI'ya gitmiyor

önce pandas analiz ediyor
↓
profile oluşturuyor
↓
AI profile'ı yorumluyor

## 2. Prompt Preparation

`data_ai_service.py` içinde profile dictionary önce metne çevrilir.

Python dictionary:

```python
{
    "duplicate_count": 1,
    "null_counts": {
        "age": 1
    }
}

↓

json.dumps(...)

↓

Metin:

{
  "duplicate_count": 1,
  "null_counts": {
    "age": 1
  }
}

Bu metin daha sonra AI'ya gönderilecek input içine yerleştirilir.

Akış:

Profile Dictionary
↓
json.dumps()
↓
profile_text
↓
Prompt

```markdown
`profile_text` yalnızca profiling verisinin metin halidir.

Prompt ise AI'ya gönderilecek input metnidir ve `profile_text` bu prompt'un içine eklenir.

profile
→ Python dict

profile_text
→ aynı verinin string hali

prompt
→ AI'ya gidecek metin


## 3. OpenAI Request

Hazırlanan prompt, `generate_data_recommendations()` fonksiyonu içinde OpenAI'ya gönderilir.

OpenAI çağrısında üç ana parça kullanılır:

- `model` → hangi modelin kullanılacağını belirler
- `instructions` → AI'nın nasıl davranacağını ve hangi kurallara uymasını söyler
- `input` → AI'nın inceleyeceği gerçek prompt metnidir

Akış:

profile
↓
build_recommendation_prompt(profile)
↓
prompt
↓
client.responses.create(...)
↓
OpenAI response

`instructions` sabit davranış kurallarını içerir.

Örneğin AI'dan:

- yalnızca profile dayanması
- kesin varsayımlar yapmaması
- şüpheli değerleri otomatik olarak hatalı kabul etmemesi
- veriyi değiştirmemesi
- yalnızca kısa ve öncelikli öneriler üretmesi

istenir.

`input` ise profile bilgisini içeren gerçek prompt'tur.


OpenAI cevabı doğrudan string değildir.

AI tarafından üretilen gerçek metin:

`response.output_text`

üzerinden alınır.

Bu metin `recommendations` değişkenine kaydedilir.

instructions
→ AI NASIL davranacak?

input
→ AI NEYİ inceleyecek?

output_text
→ AI NE CEVAP verdi?


## 4. API Response

AI tarafından üretilen öneriler tekrar `data_routes.py` tarafına döner.

Önce profiling sonucu oluşturulur:

`profile`

Sonra AI recommendation fonksiyonu çağrılır:

`generate_data_recommendations(profile)`

Bu fonksiyonun döndürdüğü metin:

`recommendations`

değişkenine alınır.

Profile verisini korumak için bir kopyası oluşturulur:

`response_body = profile.copy()`

Daha sonra AI cevabı bu dictionary içine yeni bir alan olarak eklenir:

`response_body["recommendations"] = recommendations`

Son olarak:

`return response_body`

ile profiling bilgileri ve AI önerileri birlikte API cevabında döndürülür.


profile
↓
AI analysis
↓
recommendations

profile.copy()
↓
response_body
↓
response_body["recommendations"] = recommendations
↓
JSON Response



{
  "row_count": 4,
  "null_counts": {
    "age": 1
  },
  "duplicate_count": 1,
  "numeric_summary": {
    "age": {
      "mean": 353,
      "min": 30,
      "max": 999
    }
  },
  "recommendations": "Age kolonundaki 999 değeri şüpheli görünüyor..."
}



CSV
↓
Pandas Profiling
↓
Profile Dictionary
↓
JSON text
↓
Prompt
↓
OpenAI
↓
Recommendations
↓
Profile + Recommendations
↓
API Response