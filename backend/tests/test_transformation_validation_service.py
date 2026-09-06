from backend.app.transformation_validation_service import (
    validate_missing_values_transformation,
    validate_missing_values_dataframes,
)
import pandas as pd

from backend.app.data_profile_service import build_data_profile


def test_validate_missing_values_transformation_returns_true_when_nulls_decrease():

    # Dönüşümden önce age kolonunda 3 eksik değer var.
    before_profile = {
        "null_counts": {
            "age": 3,
        }
    }

    # Dönüşümden sonra age kolonunda sadece 1 eksik değer kalmış.
    after_profile = {
        "null_counts": {
            "age": 1,
        }
    }

    result = validate_missing_values_transformation(
        before_profile=before_profile,
        after_profile=after_profile,
        column="age",
    )

    # 1 < 3 olduğu için transformation başarılı kabul edilir.
    assert result is True

def test_validate_missing_values_transformation_returns_false_when_nulls_do_not_decrease():

    before_profile = {
        "null_counts": {
            "age": 3,
        }
    }

    after_profile = {
        "null_counts": {
            "age": 3,
        }
    }

    result = validate_missing_values_transformation(
        before_profile=before_profile,
        after_profile=after_profile,
        column="age",
    )

    assert result is False

def test_validate_missing_values_transformation_with_real_profiles():

    # Dönüşümden önce age kolonunda 2 null var.
    before_df = pd.DataFrame(
        {
            "name": ["Ali", "Ayse", "Mehmet"],
            "age": [30, None, None],
        }
    )

    # Dönüşümden sonra null değerlerden biri giderilmiş.
    after_df = pd.DataFrame(
        {
            "name": ["Ali", "Ayse", "Mehmet"],
            "age": [30, 25, None],
        }
    )

    # Gerçek profiling service'i kullanıyoruz.
    before_profile = build_data_profile(before_df)
    after_profile = build_data_profile(after_df)

    result = validate_missing_values_transformation(
        before_profile=before_profile,
        after_profile=after_profile,
        column="age",
    )

    assert result is True

def test_validate_missing_values_dataframes_returns_true_when_nulls_decrease():

    before_df = pd.DataFrame(
        {
            "name": ["Ali", "Ayse", "Mehmet"],
            "age": [30, None, None],
        }
    )

    after_df = pd.DataFrame(
        {
            "name": ["Ali", "Ayse", "Mehmet"],
            "age": [30, 25, None],
        }
    )

    result = validate_missing_values_dataframes(
        before_df=before_df,
        after_df=after_df,
        column="age",
    )

    assert result is True

def test_validate_missing_values_dataframes_returns_false_when_nulls_do_not_decrease():

    before_df = pd.DataFrame(
        {
            "name": ["Ali", "Ayse", "Mehmet"],
            "age": [30, None, None],
        }
    )

    after_df = pd.DataFrame(
        {
            "name": ["Ali", "Ayse", "Mehmet"],
            "age": [30, None, None],
        }
    )

    result = validate_missing_values_dataframes(
        before_df=before_df,
        after_df=after_df,
        column="age",
    )

    assert result is False