import pandas as pd

from backend.app.data_profile_service import build_data_profile
from backend.app.models import MissingValuesValidationResult

# validate_missing_values_transformation()
#
# Görevi:
# Junior bir data transformation yaptıktan sonra,
# ilgili kolondaki eksik değer sayısının gerçekten azalıp azalmadığını kontrol eder.
#
# Örnek:
#
# BEFORE:
# age null_count = 3
#
# AFTER:
# age null_count = 1
#
# Sonuç:
# 1 < 3 olduğu için True döner.
#
# Bu kontrol AI ile yapılmaz.
# Tamamen backend tarafında, gerçek profile verileri üzerinden yapılır.
#
# Neden?
# Çünkü "transformation başarılı mı?" sorusunu sadece kodun mantığına bakarak değil,
# gerçek veri sonucuna bakarak doğrulamak istiyoruz.
#
# null_counts nereden geliyor?
#
# backend/app/data_profile_service.py
# içindeki:
#
# build_data_profile(df)
#
# fonksiyonundan.
#
# O fonksiyon DataFrame'i analiz eder ve şöyle bir profile dict üretir:
#
# profile = {
#     ...
#     "null_counts": {
#         "age": 3,
#         "city": 1,
#     },
#     ...
# }
#
# Yani burada kullandığımız:
#
# before_profile["null_counts"][column]
#
# ve
#
# after_profile["null_counts"][column]
#
# değerleri build_data_profile() tarafından üretilmiş profile sözlüklerinden gelir.

def validate_missing_values_transformation(
    before_profile: dict,
    after_profile: dict,
    column: str,
) -> MissingValuesValidationResult:

    # Dönüşümden önce ilgili kolonda kaç null vardı?
    before_null_count = before_profile["null_counts"][column]

    # Dönüşümden sonra kaç null kaldı?
    after_null_count = after_profile["null_counts"][column]

    # Null sayısı azaldıysa transformation başarılıdır.
    success = after_null_count < before_null_count

    # Artık sadece True / False döndürmüyoruz.
    # Validation'ın hangi sayılara dayanarak karar verdiğini
    # structured olarak geri döndürüyoruz.
    return MissingValuesValidationResult(
        column=column,
        before_null_count=before_null_count,
        after_null_count=after_null_count,
        success=success,
    )


# bu fonksiyon bir orchestrator/helper gibi davranıyor:
#  DataFrame’leri alıyor, 
# profile çeviriyor ve mevcut validation fonksiyonuna gönderiyor
def validate_missing_values_dataframes(
    before_df: pd.DataFrame,
    after_df: pd.DataFrame,
    column: str,
) -> MissingValuesValidationResult:

    # Dönüşümden önceki DataFrame'in profilini çıkarır.
    #
    # build_data_profile()
    # backend/app/data_profile_service.py içindedir.
    before_profile = build_data_profile(before_df)

    # Dönüşümden sonraki DataFrame'in profilini çıkarır.
    after_profile = build_data_profile(after_df)

    # Hazır profile sözlüklerini mevcut validation fonksiyonuna verir.
    #
    # Bu fonksiyon ilgili kolondaki null sayısını karşılaştırır:
    #
    # before null_count = 3
    # after null_count  = 1
    #
    # 1 < 3
    # ↓
    # True
    return validate_missing_values_transformation(
        before_profile=before_profile,
        after_profile=after_profile,
        column=column,
    )