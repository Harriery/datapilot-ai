import pandas as pd

from backend.app.local_data_quality_service import (
    analyze_dataframe_locally,
)


def test_local_analysis_detects_missing_values():

    df = pd.DataFrame(
        {
            "age": [
                20,
                None,
                30,
            ]
        }
    )

    result = analyze_dataframe_locally(
        df
    )

    findings = result.findings

    assert any(
        finding.issue_type
        == "missing_values"
        and finding.column == "age"
        for finding in findings
    )


def test_local_analysis_detects_duplicates():

    df = pd.DataFrame(
        {
            "id": [
                1,
                2,
                2,
            ],
            "city": [
                "A",
                "B",
                "B",
            ],
        }
    )

    result = analyze_dataframe_locally(
        df
    )

    assert any(
        finding.issue_type
        == "duplicate_rows"
        for finding in result.findings
    )


def test_local_analysis_detects_string_quality_issues():

    df = pd.DataFrame(
        {
            "city": [
                "Amsterdam",
                " amsterdam ",
                "",
                "Rotterdam",
            ]
        }
    )

    result = analyze_dataframe_locally(
        df
    )

    findings = result.findings

    assert any(
        finding.issue_type
        == "missing_values"
        for finding in findings
    )

    assert any(
        finding.issue_type
        == "suspicious_values"
        for finding in findings
    )


def test_local_analysis_detects_possible_outlier():

    df = pd.DataFrame(
        {
            "age": [
                20,
                21,
                22,
                23,
                24,
                200,
            ]
        }
    )

    result = analyze_dataframe_locally(
        df
    )

    assert any(
        finding.issue_type
        == "suspicious_values"
        and finding.column == "age"
        for finding in result.findings
    )


def test_clean_dataset_can_return_no_findings():

    df = pd.DataFrame(
        {
            "id": [
                1,
                2,
                3,
            ],
            "city": [
                "Amsterdam",
                "Rotterdam",
                "Utrecht",
            ],
        }
    )

    result = analyze_dataframe_locally(
        df
    )

    assert result.findings == []