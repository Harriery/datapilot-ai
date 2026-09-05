from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_mentor_data_quality_returns_mentor_response():
    request_body = {
        "learner_id": "demo-learner",
        "finding": {
            "issue_type": "missing_values",
            "column": "age",
            "severity": "medium",
            "observation": "age sütununda eksik değer var.",
            "suggested_action": "Eksik değerin nedenini inceleyin.",
        },
    }

    # Gerçek AI çağrısı yapmıyoruz.
    # mentor_routes.py içindeki service fonksiyonunu mock'luyoruz.
    with patch(
        "backend.app.mentor_routes.get_mentor_response_for_data_quality_finding",
        return_value="Test mentor cevabı.",
    ) as mock_mentor:

        response = client.post(
            "/mentor/data-quality",
            json=request_body,
        )

        assert response.status_code == 200

        assert response.json() == {
            "mentor_response": "Test mentor cevabı."
        }

        # Endpoint service fonksiyonunu gerçekten çağırdı mı?
        mock_mentor.assert_called_once()

        call_arguments = mock_mentor.call_args.kwargs

        assert call_arguments["learner_id"] == "demo-learner"
        assert call_arguments["finding"].issue_type == "missing_values"
        assert call_arguments["finding"].column == "age"
        assert call_arguments["finding"].severity == "medium"