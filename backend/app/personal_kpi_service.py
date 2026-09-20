from backend.app.models import (
    PersonalProjectAnalysisResult,
    PersonalProjectKPIDefinition,
)


def _normalize_code_part(
    value: str,
) -> str:
    return (
        value
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def build_personal_kpi_candidates(
    analysis_result: PersonalProjectAnalysisResult,
) -> list[PersonalProjectKPIDefinition]:

    measure = analysis_result.measure
    dimension = analysis_result.dimension

    measure_code = _normalize_code_part(
        measure
    )

    candidates: list[
        PersonalProjectKPIDefinition
    ] = [
        PersonalProjectKPIDefinition(
            code=f"average_{measure_code}",
            title=f"Average {measure}",
            measure=measure,
            aggregation="mean",
            dimension=None,
            description=(
                f"Average value of {measure} "
                "across the validated dataset."
            ),
            source="local",
        ),

        PersonalProjectKPIDefinition(
            code=f"count_{measure_code}",
            title=f"Count of {measure}",
            measure=measure,
            aggregation="count",
            dimension=None,
            description=(
                f"Number of non-missing "
                f"{measure} values."
            ),
            source="local",
        ),

        PersonalProjectKPIDefinition(
            code=f"minimum_{measure_code}",
            title=f"Minimum {measure}",
            measure=measure,
            aggregation="min",
            dimension=None,
            description=(
                f"Minimum observed value "
                f"of {measure}."
            ),
            source="local",
        ),

        PersonalProjectKPIDefinition(
            code=f"maximum_{measure_code}",
            title=f"Maximum {measure}",
            measure=measure,
            aggregation="max",
            dimension=None,
            description=(
                f"Maximum observed value "
                f"of {measure}."
            ),
            source="local",
        ),
    ]

    if dimension is not None:

        dimension_code = (
            _normalize_code_part(
                dimension
            )
        )

        candidates.append(
            PersonalProjectKPIDefinition(
                code=(
                    f"average_{measure_code}"
                    f"_by_{dimension_code}"
                ),
                title=(
                    f"Average {measure} "
                    f"by {dimension}"
                ),
                measure=measure,
                aggregation="mean",
                dimension=dimension,
                description=(
                    f"Compare average {measure} "
                    f"across {dimension} groups."
                ),
                source="local",
            )
        )

    return candidates