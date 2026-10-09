from __future__ import annotations


CANONICAL_MISCONCEPTIONS = (
    "missing_value_means_fill_zero",
    "execution_success_equals_validation",
    "single_metric_validation",
    "assumes_unseen_column_exists",
    "explanation_without_validation_evidence",
    "copies_prior_model_without_current_grain",
    "raw_working_dataset_confusion",
    "filtering_equals_distribution",
    "premature_transformation_before_reasoning",
    "task_scope_filter_missing",
    "grain_confusion",
    "relationship_cardinality_confusion",
    "aggregation_semantics_confusion",
    "non_additive_measure_sum",
    "raw_source_mutation_confusion",
)

MISCONCEPTION_ALIASES = {
    "imputation_with_zero_when_missing":
        "missing_value_means_fill_zero",
    "fill_missing_with_zero":
        "missing_value_means_fill_zero",
    "code_ran_means_valid":
        "execution_success_equals_validation",
    "nulls_removed_means_valid":
        "single_metric_validation",
}


def canonical_misconception_instructions() -> str:
    labels = "\n".join(
        f"- {label}"
        for label in CANONICAL_MISCONCEPTIONS
    )

    return (
        "Use only one of these canonical misconception labels when a clear "
        "reusable misconception is present:\n"
        f"{labels}\n"
        "If none applies, return null. Do not invent a new label."
    )


def normalize_misconception(
    *,
    success: bool | None,
    misconception: str | None,
) -> str | None:
    if success is True:
        return None

    if not isinstance(
        misconception,
        str,
    ):
        return None

    normalized = (
        misconception
        .strip()
        .casefold()
    )

    if not normalized:
        return None

    if normalized in CANONICAL_MISCONCEPTIONS:
        return normalized

    return MISCONCEPTION_ALIASES.get(
        normalized
    )
