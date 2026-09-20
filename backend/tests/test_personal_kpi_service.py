from backend.app.models import (
    PersonalProjectAnalysisResult,
)

from backend.app.personal_kpi_service import (
    build_personal_kpi_candidates,
)


def test_build_personal_kpi_candidates_for_age_by_city():
    analysis_result = (
        PersonalProjectAnalysisResult(
            measure="age",
            dimension="city",
            overall={
                "count": 4,
                "mean": 29.5,
                "min": 28.0,
                "max": 31.0,
            },
            grouped_results=[],
            source="local",
        )
    )

    result = build_personal_kpi_candidates(
        analysis_result
    )

    assert len(result) == 5

    codes = [
        item.code
        for item in result
    ]

    assert codes == [
        "average_age",
        "count_age",
        "minimum_age",
        "maximum_age",
        "average_age_by_city",
    ]

    grouped_candidate = result[-1]

    assert (
        grouped_candidate.title
        == "Average age by city"
    )

    assert (
        grouped_candidate.measure
        == "age"
    )

    assert (
        grouped_candidate.aggregation
        == "mean"
    )

    assert (
        grouped_candidate.dimension
        == "city"
    )

    assert (
        grouped_candidate.source
        == "local"
    )