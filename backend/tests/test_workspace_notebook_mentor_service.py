from backend.app.models import (
    DataQualityAnalysis,
    DataQualityFinding,
)

from backend.app.workspace_notebook_mentor_service import (
    build_notebook_mentor_guidance,
)


def test_notebook_mentor_warns_about_dropna_with_profile_context():
    guidance = build_notebook_mentor_guidance(
        code="df = df.dropna()",
        dataset_profile={
            "null_counts": {
                "BuildingArea": 6450,
                "YearBuilt": 5375,
                "Car": 62,
            }
        },
        dataset_analysis=(
            DataQualityAnalysis(
                findings=[
                    DataQualityFinding(
                        issue_type="missing_values",
                        column="BuildingArea",
                        severity="medium",
                        observation="Missing.",
                        suggested_action="Review.",
                    )
                ]
            )
        ),
    )

    assert any(
        "BuildingArea (6450)"
        in item
        for item in guidance
    )

    assert any(
        "dropna()"
        in item
        for item in guidance
    )


def test_notebook_mentor_warns_about_type_conversion():
    guidance = build_notebook_mentor_guidance(
        code=(
            "df['Date'] = "
            "pd.to_datetime("
            "df['Date'], "
            "errors='coerce'"
            ")"
        ),
        dataset_profile={
            "null_counts": {}
        },
        dataset_analysis=None,
    )

    assert any(
        "Type conversion"
        in item
        for item in guidance
    )


def test_notebook_mentor_returns_generic_review_when_no_rule_matches():
    guidance = build_notebook_mentor_guidance(
        code="df['x2'] = df['x'] * 2",
        dataset_profile={
            "null_counts": {}
        },
        dataset_analysis=None,
    )

    assert guidance == [
        (
            "State what you expect this cell to change, "
            "then compare row count, schema and a small "
            "preview before promoting it to the pipeline."
        )
    ]
