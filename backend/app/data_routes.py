from fastapi import APIRouter, HTTPException, UploadFile
import pandas as pd
from backend.app.data_ai_service import generate_data_recommendations

router = APIRouter()



# UploadFile → FastAPI'nin yüklenen dosyayı temsil eden nesnesi.
#
# file
# ├── filename      → "sales.csv"
# ├── content_type  → "text/csv"
# └── file          → gerçek okunabilir dosya akışı
#
# file.file yazmamızın sebebi:
# ilk file   → profile_data(file: UploadFile) içindeki UploadFile nesnesi
# ikinci .file → UploadFile'ın içindeki gerçek dosya
@router.post("/data/profile") #"/data/profile" → endpoint adresi
def profile_data(file: UploadFile): # → kullanıcıdan yüklenen dosyayı al
    if file.content_type != "text/csv":
        raise HTTPException(
            status_code=400,
            detail = "Yalnızca CSV dosyası yükleyebilirsiniz."
        )

# pd.read_csv(file.file)
# ↓
# CSV dosyasını okur
# ↓
# pandas DataFrame oluşturur
#
# DataFrame = Python içinde tablo
#
# CSV:
# name,age,city
# Ali,30,Den Haag
# Ayse,25,Rotterdam
# Mehmet,40,Utrecht
#
# DataFrame (df):
#
#       name  age       city
# 0      Ali   30   Den Haag
# 1     Ayse   25  Rotterdam
# 2   Mehmet   40    Utrecht


# CSV dosyasını okumayı deneriz.
#
# try:
# → hata çıkabilecek kod burada çalışır.
#
# except:
# → belirli bir hata oluşursa ne yapacağımızı söyler.
#
# Boş CSV yüklenirse pandas:
# pd.errors.EmptyDataError
# hatasını üretir.
#
# Bu kullanıcıdan gelen geçersiz veri olduğu için
# 500 yerine 400 Bad Request döndürüyoruz.
    try:
        df = pd.read_csv(file.file)

    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=400,
            detail="CSV dosyası boş.",
        )
# ParserError:
# CSV içinde veri vardır fakat satır/sütun yapısı
# pandas tarafından doğru şekilde okunamaz.
#
# Örn:
# kapanmamış tırnak, bozuk CSV formatı vb.
#
# Bu da kullanıcıdan gelen geçersiz veri olduğu için
# 400 Bad Request döndürüyoruz.
    
    except pd.errors.ParserError:
        raise HTTPException(
            status_code=400,
            detail="CSV dosyası geçersiz veya bozuk."
        )




# df.shape → (satır sayısı, sütun sayısı)
# Örn: (3, 5)
#
# Tuple içindeki iki değeri ayrı değişkenlere ayırıyoruz:
# row_count    → 3
# column_count → 5
#
# Böylece API cevabında "3" ve "5" yerine
# neyi temsil ettikleri açıkça belli olur.
    row_count, column_count = df.shape


# df.columns → DataFrame'deki kolon isimlerini verir.
#
# Örn:
# df.columns
# ↓
# Index(["name", "age", "city"])
#
# .tolist() ile pandas Index yapısını
# normal Python listesine çeviririz.
#
# columns
# ↓
# ["name", "age", "city"]
    columns = df.columns.tolist()


# df.dtypes → her kolonun veri tipini verir.
#
# Örn:
# name    object
# age      int64
# city    object
#
# .astype(str) → veri tiplerini string'e çevirir.
# .to_dict()   → normal Python sözlüğüne çevirir.
#
# Sonuç:
# {
#   "name": "object",
#   "age": "int64",
#   "city": "object"
# }
    data_types = df.dtypes.astype(str).to_dict()


# df.isnull() → her hücrede eksik değer var mı kontrol eder.
#
# Örn:
#          name    age   city
# 0       False  False  False
# 1       False   True  False
# 2       False  False   True
#
# .sum() → her kolondaki True değerlerini sayar.
# .to_dict() → sonucu normal Python sözlüğüne çevirir.
#
# Sonuç:
# {
#   "name": 0,
#   "age": 1,
#   "city": 1
# }
# Önce her kolondaki null sayısını alır.
    raw_null_counts = df.isnull().sum().to_dict()

# JSON'a uygun normal Python int değerlerini burada toplayacağız.
    null_counts = {}

    for column, count in raw_null_counts.items():
        null_counts[column] = int(count)



# df.duplicated() → bir satır daha önce aynen görülmüş mü kontrol eder.
# Yani tek bir kolon değil, satırdaki bütün değerler aynı mı diye bakar.
#
# Örn:
# 0    False
# 1    False
# 2     True
#
# .sum() → True değerlerini sayar.
#
# duplicate_count
# ↓
# 1
# Pandas bazı sayıları numpy.int64 olarak döndürür.
# FastAPI JSON cevabında normal Python int kullanmak daha güvenlidir.
# Bu yüzden int(...) ile dönüştürüyoruz.
    duplicate_count = int(df.duplicated().sum())


# DataFrame içindeki sayısal kolonları otomatik bulur.
#
# Örn:
# name          → str
# age           → int64
# salary        → float64
#
# numeric_columns:
# ["age", "salary"]
    numeric_columns = df.select_dtypes(include="number").columns.tolist()








# Sayısal kolonlar için temel istatistikleri çıkarıyoruz.
#
# NEDEN?
# Bir Data Engineer veri setine ilk baktığında,
# sayısal kolonlarda mantıksız / şüpheli değerler var mı görmek ister.
#
# Örn:
# age
# 25
# 30
# 999   ← şüpheli olabilir
#
# Bu yüzden her sayısal kolon için:
# count → kaç tane dolu değer var
# mean  → ortalama
# min   → en küçük değer
# max   → en büyük değer
#
# numeric_columns örneği:
# ["age", "salary"]
#
# Döngü:
# 1. tur → column = "age"
# 2. tur → column = "salary"
#
# df[column]
# → o kolonu tek başına alır
# → pandas'ta buna Series denir
#
# Sonuçta numeric_summary şu yapıya dönüşür:
#
# {
#     "age": {
#         "count": 100,
#         "mean": 34.5,
#         "min": 18.0,
#         "max": 72.0
#     },
#     "salary": {
#         "count": 98,
#         "mean": 3200.0,
#         "min": 1200.0,
#         "max": 8500.0
#     }
# }
#
# int(...) ve float(...) kullanmamızın nedeni:
# Pandas / NumPy bazı sonuçları kendi veri tiplerinde döndürebilir.
# API cevabında normal Python int ve float tiplerini kullanmak daha güvenlidir.
    numeric_summary = {}

    for column in numeric_columns:
        series = df[column]

        count = int(series.count())
        mean = float(series.mean())
        min_value = float(series.min())
        max_value = float(series.max())
        numeric_summary[column] = {
            "count": count,
            "mean": mean,
            "min": min_value,
            "max": max_value,
        }





# Pandas boş değerleri NaN olarak tutabilir.
# JSON NaN kabul etmez, null kabul eder.
# Bu yüzden:
# NaN → None → JSON'da null

# İlk 5 satırı ayrı bir küçük DataFrame olarak alır.
    sample_df = df.head(5)

# Pandas'taki NaN değerlerini JSON'un anlayacağı None değerine çevirir.
# Python None → JSON tarafında null olur.
    sample_df = sample_df.astype(object).where(pd.notnull(sample_df), None)

# DataFrame'i JSON'a uygun list[dict] yapısına çevirir.
    sample_rows = sample_df.to_dict(orient="records")






    # = AI'nın analiz ettiği veri
    profile = { 
        "row_count": row_count,
        "column_count": column_count,
        "columns": columns,
        "data_types": data_types,
        "null_counts": null_counts,
        "duplicate_count": duplicate_count,
        "sample_rows": sample_rows,
        "numeric_columns": numeric_columns,
        "numeric_summary": numeric_summary,
    }

    # = AI'nın ürettiği cevap
    recommendations = generate_data_recommendations(profile) 

    response_body = profile.copy()
    response_body["recommendations"] = recommendations

    return response_body    # = ikisini kullanıcıya birlikte verdiğimiz API cevabı

# --------ORNEK------
# {
#   "row_count": 8807,
#   "column_count": 12,
#   "null_counts": {
#     "director": 2634
#   },
#   "duplicate_count": 0,
#   "numeric_summary": {
#     "release_year": {
#       "min": 1925,
#       "max": 2021
#     }
#   },
#   "recommendations": "Director kolonunda yüksek miktarda eksik veri bulunmaktadır..."
# }