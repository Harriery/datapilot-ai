## 1. File Validation

Endpoint önce yüklenen dosyanın CSV olup olmadığını kontrol eder.

Beklenen content type:

`text/csv`

CSV olmayan bir dosya gönderilirse:

`400 Bad Request`

döndürülür.

Mantık:

UploadFile
↓
content_type kontrolü
↓
text/csv ?
├── evet → devam
└── hayır → 400

Bu bölüm doğrudan kodumuzdaki şu kısmı dokümante ediyor:

if file.content_type != "text/csv":


## 2. CSV to DataFrame

CSV dosyası pandas ile okunur:

`pd.read_csv(file.file)`

Bu işlem sonucunda CSV verisi bir pandas DataFrame'e dönüşür.

DataFrame, Python içinde tablo şeklinde veriyle çalışmamızı sağlar.

Örnek:

CSV:

name,age,city  
Ali,30,Den Haag  
Ayse,25,Rotterdam  

↓

DataFrame:

| name | age | city |
|---|---:|---|
| Ali | 30 | Den Haag |
| Ayse | 25 | Rotterdam |

CSV boşsa pandas `EmptyDataError`,
CSV yapısı bozuksa `ParserError` üretir.

Bu hatalar API tarafından yakalanarak `400 Bad Request` cevabına dönüştürülür.

Buradaki akış:

CSV dosyası
↓
pd.read_csv()
↓
DataFrame
↓
profiling işlemleri

Önemli ayrım da şu:

EmptyDataError / ParserError
→ pandas'ın iç hata türleri

HTTPException 400
→ bizim kullanıcıya döndürdüğümüz API cevabı


## 3. Data Profiling

DataFrame oluşturulduktan sonra veri setinin temel profili çıkarılır.

Profil içinde şu bilgiler bulunur:

- `row_count` → toplam satır sayısı
- `column_count` → toplam sütun sayısı
- `columns` → sütun isimleri
- `data_types` → her sütunun veri tipi
- `null_counts` → her sütundaki eksik değer sayısı
- `duplicate_count` → tekrar eden satır sayısı
- `sample_rows` → ilk 5 örnek satır
- `numeric_columns` → sayısal sütunların isimleri
- `numeric_summary` → sayısal sütunların temel istatistikleri

Numeric summary içinde:

- `count` → null olmayan değer sayısı
- `mean` → ortalama
- `min` → en küçük değer
- `max` → en büyük değer

Bu bilgiler, veri üzerinde temizlik veya transformation yapılmadan önce
verinin genel yapısını ve olası veri kalitesi problemlerini anlamak için kullanılır.

Bunu şöyle düşün:

DataFrame
↓
profiling
├── veri ne kadar büyük?
├── hangi kolonlar var?
├── tipleri ne?
├── eksik veri var mı?
├── duplicate var mı?
├── sayısal değerler mantıklı mı?
└── örnek veri nasıl görünüyor?

## 4. JSON Response

Profiling tamamlandıktan sonra sonuçlar JSON olarak API cevabında döndürülür.

Örnek response:

```json
{
  "row_count": 3,
  "column_count": 3,
  "columns": ["name", "age", "city"],
  "data_types": {
    "name": "str",
    "age": "float64",
    "city": "str"
  },
  "null_counts": {
    "name": 0,
    "age": 1,
    "city": 0
  },
  "duplicate_count": 1,
  "numeric_columns": ["age"],
  "numeric_summary": {
    "age": {
      "count": 2,
      "mean": 30.0,
      "min": 30.0,
      "max": 30.0
    }
  }
}

Bu response daha sonraki aşamalarda AI tarafından
cleaning ve transformation önerileri üretmek için kullanılabilir.


Böylece dokümanın genel akışı tamamlanmış olacak:

```text
CSV Upload
↓
File Validation
↓
CSV → DataFrame
↓
Data Profiling
↓
JSON Response
↓
sonraki aşama: AI önerileri