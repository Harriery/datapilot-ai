from unittest.mock import patch

from backend.app.data_ai_service import (
    build_recommendation_prompt,
    generate_data_recommendations,
)


def test_build_recommendation_prompt():
    profile = {
        "row_count": 4,
        "null_counts": {
            "age": 1
        },
        "duplicate_count": 1,
    }

    prompt = build_recommendation_prompt(profile)

    assert "row_count" in prompt
    assert "age" in prompt
    assert "duplicate_count" in prompt


def test_generate_data_recommendations():
    profile = {
        "row_count": 4,
        "null_counts": {
            "age": 1
        },
        "duplicate_count": 1,
    }

    with patch(
    "backend.app.data_ai_service.client.responses.create"
    ) as mock_create:
        mock_create.return_value.output_text = (
            "Age kolonundaki eksik değeri inceleyin."
        )
        recommendations = generate_data_recommendations(profile)

        assert recommendations == (
            "Age kolonundaki eksik değeri inceleyin."
        )