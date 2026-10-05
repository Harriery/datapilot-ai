from __future__ import annotations

from backend.app.mentor_misconception_taxonomy import (
    canonical_misconception_instructions,
)


def learning_evidence_classifier_rules() -> str:
    return f"""
    - A pure help request or clarification question with no proposed answer,
      action, explanation, or hypothesis is not learning evidence.
    - A learner claim, proposed decision, explanation, hypothesis, or attempted
      answer IS learning evidence even when it is wrong.
    - A proposed decision or attempted answer remains learning evidence when
      phrased as a question.
    - Interrogative wording does not make a proposed decision non-evidence.
      For example, "Should I fill missing values with 0?" is a proposed action,
      so classify it as evidence and evaluate whether that proposal is sound.
    - For genuine evidence, set success true or false from the supplied context
      AND the current learning phase.
    - For non-evidence, set success=null.
    - If success=true, misconception must be null.
    - {canonical_misconception_instructions()}
    - Do not invent dataset facts.
    """.strip()


def strict_validation_classifier_rules() -> str:
    return """
    - Validation phase is strict: code running without error is NOT sufficient
      validation. Compare before/after evidence and the intended operation.
      Unexpected row loss, row gain, or other unintended side effects mean
      success=false until reconciled.
    - In validation, checking only one metric is insufficient when another
      supplied metric contradicts success. A single metric is not enough.
      For example, checking only null_count=0 is not enough when row-count
      evidence shows an unintended change.
    """.strip()
