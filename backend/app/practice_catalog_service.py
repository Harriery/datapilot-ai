from __future__ import annotations

from backend.app.models import (
    PracticeCatalogResponse,
    PracticeSourceDescriptor,
    PracticeTopicDescriptor,
)


PRACTICE_LEVEL_TARGET = 15
PRACTICE_THEORY_TARGET = 5
PRACTICE_APPLIED_TARGET = 10


PRACTICE_SOURCES = (
    PracticeSourceDescriptor(
        source_id="exercism-python",
        name="Exercism Python Track",
        repository="exercism/python",
        license="MIT",
        import_policy="allowed_with_attribution",
        delivery="on_demand",
        topics=["python"],
    ),
    PracticeSourceDescriptor(
        source_id="pandas-exercises",
        name="pandas_exercises",
        repository="guipsamora/pandas_exercises",
        license="BSD-3-Clause",
        import_policy="allowed_with_attribution",
        delivery="on_demand",
        topics=["data_cleaning_transform"],
    ),
    PracticeSourceDescriptor(
        source_id="100-pandas-puzzles",
        name="100 pandas puzzles",
        repository="ajcr/100-pandas-puzzles",
        license="MIT",
        import_policy="allowed_with_attribution",
        delivery="on_demand",
        topics=["python", "data_cleaning_transform"],
    ),
    PracticeSourceDescriptor(
        source_id="sql-practice-reference",
        name="SQL Practice curriculum",
        repository="ianfinkdata/sql-practice",
        license="GPL-3.0",
        import_policy="reference_only_copyleft_review",
        delivery="metadata_only",
        topics=["sql"],
    ),
    PracticeSourceDescriptor(
        source_id="de-zoomcamp-reference",
        name="Data Engineering Zoomcamp",
        repository="DataTalksClub/data-engineering-zoomcamp",
        license="license_review_required",
        import_policy="reference_only_pending_license_review",
        delivery="metadata_only",
        topics=["data_engineering", "sql", "data_modeling"],
    ),
)


PRACTICE_TOPICS = (
    PracticeTopicDescriptor(
        topic_id="python",
        title="Python",
        description=(
            "Refresh Python fundamentals used in data work, from control flow "
            "and collections to functions and practical data-processing code."
        ),
        modes=["theory", "code", "mixed"],
        difficulties=["easy", "medium", "hard"],
        subtopics=[
            "variables_types",
            "conditionals",
            "loops",
            "lists_dictionaries",
            "functions",
            "comprehensions",
            "exceptions",
        ],
        level_target=PRACTICE_LEVEL_TARGET,
        theory_target=PRACTICE_THEORY_TARGET,
        applied_target=PRACTICE_APPLIED_TARGET,
        mini_project_target=4,
        source_ids=[
            "exercism-python",
            "100-pandas-puzzles",
        ],
    ),
    PracticeTopicDescriptor(
        topic_id="sql",
        title="SQL",
        description=(
            "Practice querying and reasoning with relational data, progressing "
            "from SELECT and filtering to joins, CTEs and window functions."
        ),
        modes=["theory", "sql", "mixed"],
        difficulties=["easy", "medium", "hard"],
        subtopics=[
            "select_filter_sort",
            "aggregations",
            "joins",
            "subqueries",
            "ctes",
            "window_functions",
            "data_quality_queries",
        ],
        level_target=PRACTICE_LEVEL_TARGET,
        theory_target=PRACTICE_THEORY_TARGET,
        applied_target=PRACTICE_APPLIED_TARGET,
        mini_project_target=4,
        source_ids=[
            "sql-practice-reference",
            "de-zoomcamp-reference",
        ],
    ),
    PracticeTopicDescriptor(
        topic_id="data_cleaning_transform",
        title="Data Cleaning & Transformation",
        description=(
            "Exercise the same reasoning used in real preparation work: nulls, "
            "duplicates, types, filtering, derived columns and safe validation."
        ),
        modes=["theory", "code", "transformation", "mixed"],
        difficulties=["easy", "medium", "hard"],
        subtopics=[
            "missing_values",
            "duplicates",
            "data_types",
            "filtering",
            "string_cleanup",
            "derived_columns",
            "before_after_validation",
        ],
        level_target=PRACTICE_LEVEL_TARGET,
        theory_target=PRACTICE_THEORY_TARGET,
        applied_target=PRACTICE_APPLIED_TARGET,
        mini_project_target=4,
        source_ids=[
            "pandas-exercises",
            "100-pandas-puzzles",
        ],
    ),
    PracticeTopicDescriptor(
        topic_id="data_modeling",
        title="Data Modeling",
        description=(
            "Build confidence with grain, facts, dimensions, keys, relationships "
            "and semantic-model decisions."
        ),
        modes=["theory", "design", "mixed"],
        difficulties=["easy", "medium", "hard"],
        subtopics=[
            "grain",
            "facts_dimensions",
            "keys",
            "relationships",
            "star_schema",
            "semantic_columns",
        ],
        level_target=PRACTICE_LEVEL_TARGET,
        theory_target=PRACTICE_THEORY_TARGET,
        applied_target=PRACTICE_APPLIED_TARGET,
        mini_project_target=3,
        source_ids=[
            "de-zoomcamp-reference",
        ],
    ),
    PracticeTopicDescriptor(
        topic_id="data_engineering",
        title="Data Engineering",
        description=(
            "Practice pipeline thinking, ingestion, validation, orchestration, "
            "warehousing and end-to-end project decisions."
        ),
        modes=["theory", "design", "project", "mixed"],
        difficulties=["easy", "medium", "hard"],
        subtopics=[
            "ingestion",
            "etl_elt",
            "pipeline_validation",
            "orchestration",
            "warehousing",
            "batch_processing",
            "end_to_end_pipeline",
        ],
        level_target=PRACTICE_LEVEL_TARGET,
        theory_target=PRACTICE_THEORY_TARGET,
        applied_target=PRACTICE_APPLIED_TARGET,
        mini_project_target=4,
        source_ids=[
            "de-zoomcamp-reference",
        ],
    ),
)


def get_practice_catalog(
    *,
    learner_id: str,
) -> PracticeCatalogResponse:
    return PracticeCatalogResponse(
        learner_id=learner_id,
        level_completion_rule=(
            "A difficulty level completes after 15 successful exercises, "
            "including at least 5 theory and 10 applied exercises."
        ),
        project_unlock_rule=(
            "Mini projects unlock after easy, medium and hard levels for the "
            "topic are completed."
        ),
        topics=list(PRACTICE_TOPICS),
        sources=list(PRACTICE_SOURCES),
    )
