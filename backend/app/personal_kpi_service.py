from backend.app.models import (
    PersonalProjectAnalysisPlan,
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


def _build_candidates_for_measure(
    measure: str,
    dimension: str | None = None,
) -> list[PersonalProjectKPIDefinition]:

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
        dimension_code = _normalize_code_part(
            dimension
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


def build_personal_kpi_candidates_from_plan(
    analysis_plan: PersonalProjectAnalysisPlan,
) -> list[PersonalProjectKPIDefinition]:
    """
    Build deterministic KPI suggestions from validated
    dataset discovery metadata.

    The KPI stage therefore no longer depends on running
    Analysis first. The first discovered dimension is used
    as a lightweight grouped suggestion until the dedicated
    KPI Builder is implemented.
    """

    first_dimension = (
        analysis_plan.dimension_candidates[0]
        if analysis_plan.dimension_candidates
        else None
    )

    candidates_by_code: dict[
        str,
        PersonalProjectKPIDefinition,
    ] = {}

    for measure in analysis_plan.measure_candidates:
        for candidate in _build_candidates_for_measure(
            measure=measure,
            dimension=first_dimension,
        ):
            candidates_by_code[
                candidate.code
            ] = candidate

    return list(
        candidates_by_code.values()
    )


def build_personal_kpi_candidates(
    analysis_result: PersonalProjectAnalysisResult,
) -> list[PersonalProjectKPIDefinition]:
    """
    Backward-compatible helper for callers that already
    have an analysis result.
    """

    return _build_candidates_for_measure(
        measure=analysis_result.measure,
        dimension=analysis_result.dimension,
    )
