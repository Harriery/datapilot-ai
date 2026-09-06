from fastapi import APIRouter, HTTPException, UploadFile
import pandas as pd
from backend.app.data_ai_service import generate_data_recommendations
from backend.app.data_profile_service import build_data_profile
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

    profile = build_data_profile(df)
    # = AI'nın ürettiği cevap
    analysis = generate_data_recommendations(profile) 

    response_body = profile.copy()
    response_body["analysis"] = analysis.model_dump() # Pydantic nesnesini normal Python dict yapısına çevir.

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