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

def test_mentor_data_quality_attempt_returns_review():
    request_body = {
        "learner_id": "demo-learner",
        "finding": {
            "issue_type": "missing_values",
            "column": "age",
            "severity": "medium",
            "observation": "age sütununda eksik değer var.",
            "suggested_action": "Eksik değerin nedenini inceleyin.",
        },
        "attempt": "df['age'].isna().sum() ile eksik sayısını kontrol ederim.",
    }

    fake_result = {
        "mentor_response": "Doğru. Şimdi null oranını kontrol et.",
        "skill_name": "null_analysis",
        "skill_status": "learning",
        "evidence": {
            "is_evidence": True,
            "evidence_type": "application",
            "success": True,
            "note": "Junior uygun bir null kontrolü önerdi.",
        },
    }

    with patch(
        "backend.app.mentor_routes.review_data_quality_attempt",
        return_value=fake_result,
    ) as mock_review:

        response = client.post(
            "/mentor/data-quality/attempt",
            json=request_body,
        )

        assert response.status_code == 200
        assert response.json() == fake_result

        mock_review.assert_called_once()

def test_mentor_data_quality_transformation_returns_validation_result():

    request_body = {
        "learner_id": "demo-learner",
        "finding": {
            "issue_type": "missing_values",
            "column": "age",
            "severity": "medium",
            "observation": "age sütununda eksik değer var.",
            "suggested_action": "Eksik değerleri inceleyin.",
        },
        "before_rows": [
            {"name": "Ali", "age": 30},
            {"name": "Ayse", "age": None},
            {"name": "Mehmet", "age": None},
        ],
        "after_rows": [
            {"name": "Ali", "age": 30},
            {"name": "Ayse", "age": 25},
            {"name": "Mehmet", "age": None},
        ],
    }

    fake_result = {
        "skill_name": "null_analysis",
        "skill_status": "learning",
        "validation": {
            "column": "age",
            "before_null_count": 2,
            "after_null_count": 1,
            "success": True,
        },
        "evidence": {
            "is_evidence": True,
            "evidence_type": "application",
            "success": True,
            "note": (
                "age kolonundaki null sayısı "
                "2 değerinden 1 değerine değişti."
            ),
        },
    }

    with patch(
        "backend.app.mentor_routes.review_data_quality_transformation",
        return_value=fake_result,
    ) as mock_review:

        response = client.post(
            "/mentor/data-quality/transformation",
            json=request_body,
        )

        assert response.status_code == 200
        assert response.json() == fake_result

        mock_review.assert_called_once()

        call_arguments = mock_review.call_args.kwargs

        assert call_arguments["learner_id"] == "demo-learner"
        assert call_arguments["finding"].issue_type == "missing_values"
        assert call_arguments["finding"].column == "age"

        # Route'un JSON row listelerini gerçekten
        # pandas DataFrame'e çevirdiğini kontrol ediyoruz.
        before_df = call_arguments["before_df"]
        after_df = call_arguments["after_df"]

        assert before_df.shape == (3, 2)
        assert after_df.shape == (3, 2)

        assert before_df["age"].isna().sum() == 2
        assert after_df["age"].isna().sum() == 1