from unittest.mock import patch

from backend.app.progress_service import (
    get_learner_progress,
     calculate_independence_trend,
     calculate_practice_priority,
)


def test_get_learner_progress_builds_skill_summary():

    fake_skill_states = [
        {
            "skill_name": "null_analysis",
            "status": "practicing",
            "attempts": 6,
            "successful_attempts": 5,
        }
    ]

    fake_evidence = [
        {
            "assistance_level": "GUIDE",
        },
        {
            "assistance_level": "NUDGE",
        },
    ]

    with patch(
        "backend.app.progress_service."
        "database.get_skill_states_by_learner",
        return_value=fake_skill_states,
    ) as mock_get_skills, patch(
        "backend.app.progress_service."
        "database.get_learning_evidence_by_skill",
        return_value=fake_evidence,
    ) as mock_get_evidence:

        result = get_learner_progress(
            learner_id="learner-001"
        )

    assert result.learner_id == "learner-001"
    assert len(result.skills) == 1

    skill = result.skills[0]

    assert skill.skill_name == "null_analysis"
    assert skill.status == "practicing"
    assert skill.attempts == 6
    assert skill.successful_attempts == 5
    assert skill.success_rate == 0.83
    assert skill.last_assistance_level == "NUDGE"

    mock_get_skills.assert_called_once_with(
        "learner-001"
    )

    mock_get_evidence.assert_called_once_with(
        learner_id="learner-001",
        skill_name="null_analysis",
    )

def test_get_learner_progress_handles_no_attempts_and_no_evidence():

    fake_skill_states = [
        {
            "skill_name": "sql_joins",
            "status": "new",
            "attempts": 0,
            "successful_attempts": 0,
        }
    ]

    with patch(
        "backend.app.progress_service."
        "database.get_skill_states_by_learner",
        return_value=fake_skill_states,
    ), patch(
        "backend.app.progress_service."
        "database.get_learning_evidence_by_skill",
        return_value=[],
    ):

        result = get_learner_progress(
            learner_id="learner-001"
        )

    skill = result.skills[0]

    assert skill.skill_name == "sql_joins"
    assert skill.status == "new"
    assert skill.attempts == 0
    assert skill.successful_attempts == 0

    assert skill.success_rate == 0.0
    assert skill.last_assistance_level is None


def test_get_learner_progress_returns_multiple_skills():

    fake_skill_states = [
        {
            "skill_name": "null_analysis",
            "status": "practicing",
            "attempts": 4,
            "successful_attempts": 3,
        },
        {
            "skill_name": "duplicate_analysis",
            "status": "learning",
            "attempts": 2,
            "successful_attempts": 2,
        },
    ]

    def fake_get_evidence(
        learner_id: str,
        skill_name: str,
    ):
        if skill_name == "null_analysis":
            return [
                {
                    "assistance_level": "GUIDE",
                },
                {
                    "assistance_level": "NUDGE",
                },
            ]

        if skill_name == "duplicate_analysis":
            return [
                {
                    "assistance_level": "GUIDE",
                }
            ]

        return []

    with patch(
        "backend.app.progress_service."
        "database.get_skill_states_by_learner",
        return_value=fake_skill_states,
    ), patch(
        "backend.app.progress_service."
        "database.get_learning_evidence_by_skill",
        side_effect=fake_get_evidence,
    ):

        result = get_learner_progress(
            learner_id="learner-001"
        )

    assert len(result.skills) == 2

    null_skill = result.skills[0]
    duplicate_skill = result.skills[1]

    assert null_skill.skill_name == "null_analysis"
    assert null_skill.success_rate == 0.75
    assert null_skill.last_assistance_level == "NUDGE"

    assert duplicate_skill.skill_name == "duplicate_analysis"
    assert duplicate_skill.success_rate == 1.0
    assert duplicate_skill.last_assistance_level == "GUIDE"

def test_calculate_independence_trend_improving():

    evidence = [
        {"assistance_level": "GUIDE"},
        {"assistance_level": "NUDGE"},
    ]

    result = calculate_independence_trend(evidence)

    assert result == "improving"


def test_calculate_independence_trend_declining():

    evidence = [
        {"assistance_level": "NUDGE"},
        {"assistance_level": "GUIDE"},
    ]

    result = calculate_independence_trend(evidence)

    assert result == "declining"


def test_calculate_independence_trend_stable():

    evidence = [
        {"assistance_level": "GUIDE"},
        {"assistance_level": "GUIDE"},
    ]

    result = calculate_independence_trend(evidence)

    assert result == "stable"


def test_calculate_independence_trend_insufficient_data():

    evidence = [
        {"assistance_level": "NUDGE"},
    ]

    result = calculate_independence_trend(evidence)

    assert result == "insufficient_data"

def test_calculate_practice_priority_high_for_new_skill():
    result = calculate_practice_priority(
        status="new",
        success_rate=0.0,
        independence_trend="insufficient_data",
    )

    assert result == "high"


def test_calculate_practice_priority_high_for_low_success_learning():
    result = calculate_practice_priority(
        status="learning",
        success_rate=0.5,
        independence_trend="stable",
    )

    assert result == "high"


def test_calculate_practice_priority_medium_for_learning_skill():
    result = calculate_practice_priority(
        status="learning",
        success_rate=1.0,
        independence_trend="improving",
    )

    assert result == "medium"


def test_calculate_practice_priority_medium_for_declining_practicing_skill():
    result = calculate_practice_priority(
        status="practicing",
        success_rate=0.9,
        independence_trend="declining",
    )

    assert result == "medium"


def test_calculate_practice_priority_low_for_improving_practicing_skill():
    result = calculate_practice_priority(
        status="practicing",
        success_rate=1.0,
        independence_trend="improving",
    )

    assert result == "low"


def test_calculate_practice_priority_none_for_comfortable_skill():
    result = calculate_practice_priority(
        status="comfortable",
        success_rate=1.0,
        independence_trend="stable",
    )

    assert result == "none"