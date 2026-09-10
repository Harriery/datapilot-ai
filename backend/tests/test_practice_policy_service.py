from backend.app.models import (
    PracticeAttemptRequest,
    PracticeAttemptValidation,
    PracticeAttemptRecord,
    PracticeDiagnosis,
    PracticeMentorDecision,
)

from backend.app.practice_policy_service import (
    choose_practice_mentor_decision,
)


# ==================================================
# RECALL
# ==================================================
#
# Junior bu skill'de daha önce başarılı olmuşsa
# ama şimdi tekrar takıldıysa:
#
# hemen TEACH verme
# ↓
# önce NUDGE + recall


def test_previous_success_uses_recall_support():

    previous_attempt = PracticeAttemptRecord(
        attempt_id="attempt-001",
        attempt_number=1,
        attempt=PracticeAttemptRequest(
            learner_id="learner-001",
            challenge_id="old-challenge",
            answer="print(2)",
            execution_output="2",
            execution_error=None,
        ),
        validation=PracticeAttemptValidation(
            success=True,
            feedback="Başarılı.",
        ),
        diagnosis=None,
        mentor_decision=None,
    )

    current_diagnosis = PracticeDiagnosis(
        understood_concept_ids=[
            "iteration",
            "conditional_logic",
        ],
        missing_concept_ids=[
            "dictionary_key_access",
        ],
        primary_missing_concept_id=(
            "dictionary_key_access"
        ),
        understands=[
            "iteration",
        ],
        missing_concepts=[
            "dictionary key access",
        ],
        misconception=(
            "Dictionary değerine attribute gibi erişiyor."
        ),
        needs_concept_teaching=True,
        confidence="high",
    )

    decision = choose_practice_mentor_decision(
        skill_status="practicing",
        diagnosis=current_diagnosis,
        previous_attempts=[
            previous_attempt,
        ],
    )

    assert decision.assistance_level == "NUDGE"
    assert decision.support_strategy == "recall"
    assert decision.needs_micro_check is False


# ==================================================
# NUDGE → GUIDE
# ==================================================


def test_previous_nudge_escalates_to_guide():

    previous_attempt = PracticeAttemptRecord(
        attempt_id="attempt-001",
        attempt_number=1,
        attempt=PracticeAttemptRequest(
            learner_id="learner-001",
            challenge_id="challenge-001",
            answer="wrong",
            execution_output=None,
            execution_error="error",
        ),
        validation=PracticeAttemptValidation(
            success=False,
            feedback="Başarısız.",
        ),
        diagnosis=PracticeDiagnosis(
            understood_concept_ids=[
                "iteration",
            ],
            missing_concept_ids=[
                "dictionary_key_access",
            ],
            primary_missing_concept_id=(
                "dictionary_key_access"
            ),
            understands=[
                "iteration",
            ],
            missing_concepts=[
                "dictionary access",
            ],
            misconception=None,
            needs_concept_teaching=False,
            confidence="high",
        ),
        mentor_decision=PracticeMentorDecision(
            assistance_level="NUDGE",
            support_strategy="recall",
            reason="Hafif hatırlatma verildi.",
            needs_micro_check=False,
        ),
    )

    current_diagnosis = PracticeDiagnosis(
        understood_concept_ids=[
            "iteration",
        ],
        missing_concept_ids=[
            "dictionary_key_access",
        ],
        primary_missing_concept_id=(
            "dictionary_key_access"
        ),
        understands=[
            "iteration",
        ],
        missing_concepts=[
            "Accessing dictionary values via keys",
        ],
        misconception=None,
        needs_concept_teaching=True,
        confidence="high",
    )

    decision = choose_practice_mentor_decision(
        skill_status="learning",
        diagnosis=current_diagnosis,
        previous_attempts=[
            previous_attempt,
        ],
    )

    assert decision.assistance_level == "GUIDE"
    assert decision.support_strategy == "focus"
    assert decision.needs_micro_check is False


# ==================================================
# GUIDE → TEACH
# ==================================================


def test_previous_guide_escalates_to_teach():

    previous_attempt = PracticeAttemptRecord(
        attempt_id="attempt-001",
        attempt_number=1,
        attempt=PracticeAttemptRequest(
            learner_id="learner-001",
            challenge_id="challenge-001",
            answer="wrong",
            execution_output=None,
            execution_error="error",
        ),
        validation=PracticeAttemptValidation(
            success=False,
            feedback="Başarısız.",
        ),
        diagnosis=PracticeDiagnosis(
            understood_concept_ids=[
                "iteration",
            ],
            missing_concept_ids=[
                "dictionary_key_access",
            ],
            primary_missing_concept_id=(
                "dictionary_key_access"
            ),
            understands=[
                "iteration",
            ],
            missing_concepts=[
                "dictionary key lookup",
            ],
            misconception=None,
            needs_concept_teaching=True,
            confidence="high",
        ),
        mentor_decision=PracticeMentorDecision(
            assistance_level="GUIDE",
            support_strategy="focus",
            reason="Yönlendirme verildi.",
            needs_micro_check=False,
        ),
    )

    current_diagnosis = PracticeDiagnosis(
        understood_concept_ids=[
            "iteration",
        ],
        missing_concept_ids=[
            "dictionary_key_access",
        ],
        primary_missing_concept_id=(
            "dictionary_key_access"
        ),
        understands=[
            "iteration",
        ],
        missing_concepts=[
            "Dictionary values via key access",
        ],
        misconception=None,
        needs_concept_teaching=True,
        confidence="high",
    )

    decision = choose_practice_mentor_decision(
        skill_status="learning",
        diagnosis=current_diagnosis,
        previous_attempts=[
            previous_attempt,
        ],
    )

    assert decision.assistance_level == "TEACH"

    assert (
        decision.support_strategy
        == "concept_explanation"
    )

    assert decision.needs_micro_check is True


# ==================================================
# TEACH → DEMONSTRATE
# ==================================================


def test_previous_teach_escalates_to_demonstrate():

    previous_attempt = PracticeAttemptRecord(
        attempt_id="attempt-001",
        attempt_number=1,
        attempt=PracticeAttemptRequest(
            learner_id="learner-001",
            challenge_id="challenge-001",
            answer="wrong",
            execution_output=None,
            execution_error="error",
        ),
        validation=PracticeAttemptValidation(
            success=False,
            feedback="Başarısız.",
        ),
        diagnosis=PracticeDiagnosis(
            understood_concept_ids=[
                "iteration",
            ],
            missing_concept_ids=[
                "dictionary_key_access",
            ],
            primary_missing_concept_id=(
                "dictionary_key_access"
            ),
            understands=[
                "iteration",
            ],
            missing_concepts=[
                "dictionary key access",
            ],
            misconception=None,
            needs_concept_teaching=True,
            confidence="high",
        ),
        mentor_decision=PracticeMentorDecision(
            assistance_level="TEACH",
            support_strategy="concept_explanation",
            reason="Kavram açıklandı.",
            needs_micro_check=True,
        ),
    )

    current_diagnosis = PracticeDiagnosis(
        understood_concept_ids=[
            "iteration",
        ],
        missing_concept_ids=[
            "dictionary_key_access",
        ],
        primary_missing_concept_id=(
            "dictionary_key_access"
        ),
        understands=[
            "iteration",
        ],
        missing_concepts=[
            "Accessing dict values using keys",
        ],
        misconception=None,
        needs_concept_teaching=True,
        confidence="high",
    )

    decision = choose_practice_mentor_decision(
        skill_status="learning",
        diagnosis=current_diagnosis,
        previous_attempts=[
            previous_attempt,
        ],
    )

    assert decision.assistance_level == "DEMONSTRATE"

    assert (
        decision.support_strategy
        == "worked_example"
    )

    assert decision.needs_micro_check is True