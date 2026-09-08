import pandas as pd

from backend.app.data_profile_service import build_data_profile
from backend.app.models import (
    DataQualityFinding,
    MissingValuesValidationResult,
    DuplicateRowsValidationResult,
)

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


# validate_duplicate_rows_transformation()
#
# Görevi:
# Transformation sonrasında duplicate row sayısının
# gerçekten azalıp azalmadığını kontrol eder.
#
# Örnek:
#
# BEFORE:
# duplicate_count = 4
#
# AFTER:
# duplicate_count = 1
#
# 1 < 4
# ↓
# success = True
#
# Bu karar AI tarafından verilmez.
# Gerçek profile sonuçları karşılaştırılır.
def validate_duplicate_rows_transformation(
    before_profile: dict,
    after_profile: dict,
) -> DuplicateRowsValidationResult:

    before_duplicate_count = before_profile["duplicate_count"]
    after_duplicate_count = after_profile["duplicate_count"]

    success = (
        after_duplicate_count
        < before_duplicate_count
    )

    return DuplicateRowsValidationResult(
        before_duplicate_count=before_duplicate_count,
        after_duplicate_count=after_duplicate_count,
        success=success,
    )


# DataFrame seviyesindeki helper/orchestrator.
#
# before_df ve after_df alınır,
# ikisinin de profile'ı çıkarılır,
# ardından duplicate validator çalıştırılır.
def validate_duplicate_rows_dataframes(
    before_df: pd.DataFrame,
    after_df: pd.DataFrame,
) -> DuplicateRowsValidationResult:

    before_profile = build_data_profile(before_df)
    after_profile = build_data_profile(after_df)

    return validate_duplicate_rows_transformation(
        before_profile=before_profile,
        after_profile=after_profile,
    )


# validate_transformation_for_finding()
#
# Görevi:
# DataQualityFinding'e bakarak hangi validation'ın
# çalıştırılması gerektiğine karar verir.
#
# Şimdilik yalnızca:
#
# missing_values
# ↓
# validate_missing_values_dataframes()
#
# destekliyoruz.
#
# İleride:
# duplicate_rows
# suspicious_values
# data_type_issue
#
# gibi validation'lar da buraya bağlanabilir.
#
# Böylece caller ayrıca:
# column="age"
#
# demek zorunda kalmaz.
# Kolon bilgisi finding içinden gelir.
def validate_transformation_for_finding(
    before_df: pd.DataFrame,
    after_df: pd.DataFrame,
    finding: DataQualityFinding,
) -> (
    MissingValuesValidationResult
    | DuplicateRowsValidationResult
    | None
):

    if finding.issue_type == "missing_values":

        if finding.column is None:
            raise ValueError(
                "Missing values validation için column gerekli."
            )

        return validate_missing_values_dataframes(
            before_df=before_df,
            after_df=after_df,
            column=finding.column,
        )

    if finding.issue_type == "duplicate_rows":
        return validate_duplicate_rows_dataframes(
            before_df=before_df,
            after_df=after_df,
        )

    return None