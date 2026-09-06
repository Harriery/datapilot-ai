
from backend.app.transformation_validation_service import (
    validate_missing_values_transformation,
    validate_missing_values_dataframes,
    validate_transformation_for_finding,
)
from backend.app.mentor_service import build_learning_evidence_from_validation

from backend.app.models import (
    DataQualityFinding,
    MissingValuesValidationResult
)

from backend.app.data_profile_service import build_data_profile

import pandas as pd
import pytest


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

    assert result.column == "age"
    assert result.before_null_count == 3
    assert result.after_null_count == 1
    assert result.success is True


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

    assert result.column == "age"
    assert result.before_null_count == 3
    assert result.after_null_count == 3
    assert result.success is False


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

    assert result.column == "age"
    assert result.before_null_count == 2
    assert result.after_null_count == 1
    assert result.success is True


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

    assert result.column == "age"
    assert result.before_null_count == 2
    assert result.after_null_count == 1
    assert result.success is True


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

    assert result.column == "age"
    assert result.before_null_count == 2
    assert result.after_null_count == 2
    assert result.success is False




def test_validate_transformation_for_missing_values_finding():

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

    finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="age sütununda eksik değerler var.",
        suggested_action="Eksik değerleri inceleyin.",
    )

    result = validate_transformation_for_finding(
        before_df=before_df,
        after_df=after_df,
        finding=finding,
    )

    assert result is not None
    assert result.column == "age"
    assert result.before_null_count == 2
    assert result.after_null_count == 1
    assert result.success is True

def test_validate_transformation_for_missing_values_requires_column():

    before_df = pd.DataFrame(
        {
            "age": [30, None],
        }
    )

    after_df = pd.DataFrame(
        {
            "age": [30, 25],
        }
    )

    finding = DataQualityFinding(
        issue_type="missing_values",
        column=None,
        severity="medium",
        observation="Eksik değer problemi var.",
        suggested_action="Eksik değerleri inceleyin.",
    )

    with pytest.raises(
        ValueError,
        match="Missing values validation için column gerekli.",
    ):
        validate_transformation_for_finding(
            before_df=before_df,
            after_df=after_df,
            finding=finding,
        )

def test_validate_transformation_for_unsupported_finding_returns_none():

    before_df = pd.DataFrame(
        {
            "name": ["Ali", "Ali"],
        }
    )

    after_df = pd.DataFrame(
        {
            "name": ["Ali"],
        }
    )

    finding = DataQualityFinding(
        issue_type="duplicate_rows",
        column=None,
        severity="medium",
        observation="Tekrar eden satırlar var.",
        suggested_action="Duplicate satırları inceleyin.",
    )

    result = validate_transformation_for_finding(
        before_df=before_df,
        after_df=after_df,
        finding=finding,
    )

    assert result is None

def test_build_learning_evidence_from_successful_validation():

    validation = MissingValuesValidationResult(
        column="age",
        before_null_count=3,
        after_null_count=1,
        success=True,
    )

    evidence = build_learning_evidence_from_validation(validation)

    assert evidence.is_evidence is True
    assert evidence.evidence_type == "application"
    assert evidence.success is True
    assert evidence.note == (
        "age kolonundaki null sayısı "
        "3 değerinden 1 değerine değişti."
    )


def test_build_learning_evidence_from_failed_validation():

    validation = MissingValuesValidationResult(
        column="age",
        before_null_count=3,
        after_null_count=3,
        success=False,
    )

    evidence = build_learning_evidence_from_validation(validation)

    assert evidence.is_evidence is True
    assert evidence.evidence_type == "application"
    assert evidence.success is False
    assert evidence.note == (
        "age kolonundaki null sayısı "
        "3 değerinden 3 değerine değişti."
    )