from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app

from backend.app.models import (
    DataEngineeringTask,
    DataEngineeringTaskStep,
    DataQualityFinding,
)

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

        before_df = call_arguments["before_df"]
        after_df = call_arguments["after_df"]

        assert before_df.shape == (3, 2)
        assert after_df.shape == (3, 2)

        assert before_df["age"].isna().sum() == 2
        assert after_df["age"].isna().sum() == 1


def test_mentor_task_transformation_returns_updated_task():

    # -------------------------------------------------
    # API'YE GÖNDERİLEN REQUEST
    # -------------------------------------------------
    #
    # Artık task'ın tamamını göndermiyoruz.
    # Sadece task_id gönderiyoruz.
    #
    # Backend bu task_id ile task'ı DB'den bulacak.
    request_body = {
        "learner_id": "demo-learner",
        "task_id": "task-001",

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

    # -------------------------------------------------
    # DB'DE VARMIŞ GİBİ DAVRANACAĞIMIZ TASK
    # -------------------------------------------------

    first_finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="age kolonunda eksik değer var.",
        suggested_action="Eksik değerleri incele.",
    )

    second_finding = DataQualityFinding(
        issue_type="duplicate_rows",
        column=None,
        severity="medium",
        observation="Duplicate satırlar var.",
        suggested_action="Duplicate satırları incele.",
    )

    first_step = DataEngineeringTaskStep(
        step_number=1,
        title="Missing values problemini çöz",
        finding=first_finding,
        status="active",
    )

    second_step = DataEngineeringTaskStep(
        step_number=2,
        title="Duplicate rows problemini çöz",
        finding=second_finding,
        status="pending",
    )

    stored_task = DataEngineeringTask(
        task_id="task-001",
        title="Dataset problemlerini çöz",
        steps=[
            first_step,
            second_step,
        ],
        current_step_number=1,
        status="active",
    )

    # -------------------------------------------------
    # SERVICE'TEN DÖNMÜŞ GİBİ DAVRANACAĞIMIZ SONUÇ
    # -------------------------------------------------

    fake_result = {
        "task": {
            "task_id": "task-001",
            "title": "Dataset problemlerini çöz",

            "steps": [
                {
                    "step_number": 1,
                    "title": "Missing values problemini çöz",
                    "finding": {
                        "issue_type": "missing_values",
                        "column": "age",
                        "severity": "medium",
                        "observation": "age kolonunda eksik değer var.",
                        "suggested_action": "Eksik değerleri incele.",
                    },
                    "status": "completed",
                },

                {
                    "step_number": 2,
                    "title": "Duplicate rows problemini çöz",
                    "finding": {
                        "issue_type": "duplicate_rows",
                        "column": None,
                        "severity": "medium",
                        "observation": "Duplicate satırlar var.",
                        "suggested_action": "Duplicate satırları incele.",
                    },
                    "status": "active",
                },
            ],

            "current_step_number": 2,
            "status": "active",
        },

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
            "note": "Null sayısı azaldı.",
        },
    }

    # -------------------------------------------------
    # MOCK'LAR
    # -------------------------------------------------
    #
    # Gerçek DB'ye gitmiyoruz.
    #
    # get_data_engineering_task()
    # çağrıldığında stored_task döndürüyoruz.
    #
    # Gerçek transformation service'i de çalıştırmıyoruz.
    # fake_result döndürüyoruz.
    with patch(
        "backend.app.mentor_routes.database.get_data_engineering_task",
        return_value=stored_task,
    ) as mock_get_task, patch(
        "backend.app.mentor_routes.review_data_engineering_task_transformation",
        return_value=fake_result,
    ) as mock_review:

        response = client.post(
            "/mentor/task/transformation",
            json=request_body,
        )

    # -------------------------------------------------
    # RESPONSE KONTROLÜ
    # -------------------------------------------------

    assert response.status_code == 200
    assert response.json() == fake_result

    # -------------------------------------------------
    # TASK DB'DEN DOĞRU BİLGİLERLE İSTENDİ Mİ?
    # -------------------------------------------------

    mock_get_task.assert_called_once_with(
        task_id="task-001",
        learner_id="demo-learner",
    )

    # -------------------------------------------------
    # SERVICE DOĞRU ÇAĞRILDI MI?
    # -------------------------------------------------

    mock_review.assert_called_once()

    call_arguments = mock_review.call_args.kwargs

    assert call_arguments["learner_id"] == "demo-learner"

    # DB'den yüklenen task service'e gönderilmiş olmalı.
    assert call_arguments["task"] is stored_task

    # -------------------------------------------------
    # JSON ROWS → PANDAS DATAFRAME KONTROLÜ
    # -------------------------------------------------

    before_df = call_arguments["before_df"]
    after_df = call_arguments["after_df"]

    assert before_df.shape == (3, 2)
    assert after_df.shape == (3, 2)

    assert before_df["age"].isna().sum() == 2
    assert after_df["age"].isna().sum() == 1


def test_create_data_engineering_task_saves_task():

    request_body = {
        "learner_id": "demo-learner",
        "task": {
            "task_id": "task-create-001",
            "title": "Dataset quality task",
            "steps": [
                {
                    "step_number": 1,
                    "title": "Fix missing values",
                    "finding": {
                        "issue_type": "missing_values",
                        "column": "age",
                        "severity": "medium",
                        "observation": "age kolonunda eksik değer var.",
                        "suggested_action": "Eksik değerleri incele."
                    },
                    "status": "active"
                }
            ],
            "current_step_number": 1,
            "status": "active"
        }
    }

    fake_profile = {
        "learner_id": "demo-learner",
        "answer_length": "concise",
        "learning_style": "guided",
        "code_support": "medium",
    }

    with patch(
        "backend.app.mentor_routes.database.get_learner_profile_by_id",
        return_value=fake_profile,
    ) as mock_get_profile, patch(
        "backend.app.mentor_routes.database.save_data_engineering_task",
    ) as mock_save:

        response = client.post(
            "/mentor/task",
            json=request_body,
        )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["task_id"] == "task-create-001"
    assert response_data["status"] == "active"
    assert response_data["current_step_number"] == 1
    assert response_data["steps"][0]["status"] == "active"

    mock_get_profile.assert_called_once_with(
        "demo-learner"
    )

    mock_save.assert_called_once()

    save_arguments = mock_save.call_args.kwargs

    assert save_arguments["learner_id"] == "demo-learner"
    assert save_arguments["task"].task_id == "task-create-001"

def test_get_data_engineering_task_returns_saved_task():

    finding = DataQualityFinding(
        issue_type="missing_values",
        column="age",
        severity="medium",
        observation="age kolonunda eksik değer var.",
        suggested_action="Eksik değerleri incele.",
    )

    step = DataEngineeringTaskStep(
        step_number=1,
        title="Missing values problemini çöz",
        finding=finding,
        status="active",
    )

    stored_task = DataEngineeringTask(
        task_id="task-001",
        title="Dataset problemlerini çöz",
        steps=[step],
        current_step_number=1,
        status="active",
    )

    with patch(
        "backend.app.mentor_routes.database.get_data_engineering_task",
        return_value=stored_task,
    ) as mock_get_task:

        response = client.get(
            "/mentor/task/task-001",
            params={
                "learner_id": "demo-learner",
            },
        )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["task_id"] == "task-001"
    assert response_data["current_step_number"] == 1
    assert response_data["status"] == "active"
    assert response_data["steps"][0]["status"] == "active"

    mock_get_task.assert_called_once_with(
        task_id="task-001",
        learner_id="demo-learner",
    )

def test_get_progress_returns_learner_progress():

    fake_progress = {
        "learner_id": "demo-learner",
        "skills": [
            {
                "skill_name": "null_analysis",
                "status": "practicing",
                "attempts": 6,
                "successful_attempts": 5,
                "success_rate": 0.83,
                "last_assistance_level": "NUDGE",
                "independence_trend": "improving",
                "practice_priority": "low",
            }
        ],
    }

    with patch(
        "backend.app.mentor_routes.database.get_learner_profile_by_id",
        return_value={"learner_id": "demo-learner"},
    ) as mock_get_profile, patch(
        "backend.app.mentor_routes.get_learner_progress",
        return_value=fake_progress,
    ) as mock_get_progress:

        response = client.get(
            "/mentor/progress/demo-learner"
        )

    assert response.status_code == 200
    assert response.json() == fake_progress

    mock_get_profile.assert_called_once_with(
        "demo-learner"
    )

    mock_get_progress.assert_called_once_with(
        learner_id="demo-learner"
    )

def test_get_progress_returns_404_for_missing_learner():

    with patch(
        "backend.app.mentor_routes.database.get_learner_profile_by_id",
        return_value=None,
    ) as mock_get_profile, patch(
        "backend.app.mentor_routes.get_learner_progress",
    ) as mock_get_progress:

        response = client.get(
            "/mentor/progress/missing-learner"
        )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Learner profile bulunamadı."
    }

    mock_get_profile.assert_called_once_with(
        "missing-learner"
    )

    mock_get_progress.assert_not_called()

def test_get_practice_recommendation_returns_recommendation():

    fake_recommendation = {
        "learner_id": "demo-learner",
        "recommendation": {
            "skill_name": "python_data_structures",
            "priority": "medium",
            "difficulty": "easy",
            "reason": (
                "python_data_structures skill'i "
                "learning seviyesinde ve "
                "practice priority medium."
            ),
        },
    }

    with patch(
        "backend.app.mentor_routes.database.get_learner_profile_by_id",
        return_value={"learner_id": "demo-learner"},
    ) as mock_get_profile, patch(
        "backend.app.mentor_routes.get_practice_recommendation",
        return_value=fake_recommendation,
    ) as mock_get_recommendation:

        response = client.get(
            "/mentor/practice/recommendation/demo-learner"
        )

    assert response.status_code == 200
    assert response.json() == fake_recommendation

    mock_get_profile.assert_called_once_with(
        "demo-learner"
    )

    mock_get_recommendation.assert_called_once_with(
        learner_id="demo-learner"
    )

def test_get_practice_recommendation_returns_404_for_missing_learner():

    with patch(
        "backend.app.mentor_routes.database.get_learner_profile_by_id",
        return_value=None,
    ) as mock_get_profile, patch(
        "backend.app.mentor_routes.get_practice_recommendation",
    ) as mock_get_recommendation:

        response = client.get(
            "/mentor/practice/recommendation/missing-learner"
        )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Learner profile bulunamadı."
    }

    mock_get_profile.assert_called_once_with(
        "missing-learner"
    )

    mock_get_recommendation.assert_not_called()


def test_create_practice_challenge_returns_challenge():

    fake_challenge = {
        "learner_id": "demo-learner",
        "challenge": {
            "challenge_id": "challenge-001",
            "skill_name": "python_data_structures",
            "difficulty": "easy",
            "challenge_type": "code",
            "title": "Eksik city değerlerini bul",
            "instructions": (
                "Aşağıdaki records listesinde city değeri "
                "eksik olan kayıtların sayısını hesapla."
            ),
            "starter_code": "records = []",
            
        },
    }

    with patch(
        "backend.app.mentor_routes.database.get_learner_profile_by_id",
        return_value={"learner_id": "demo-learner"},
    ) as mock_get_profile, patch(
        "backend.app.mentor_routes.create_practice_challenge",
        return_value=fake_challenge,
    ) as mock_create_challenge:

        response = client.post(
            "/mentor/practice/challenge/demo-learner"
        )

    assert response.status_code == 200
    assert response.json() == fake_challenge

    mock_get_profile.assert_called_once_with(
        "demo-learner"
    )

    mock_create_challenge.assert_called_once_with(
        learner_id="demo-learner"
    )

def test_create_practice_challenge_returns_404_for_missing_learner():

    with patch(
        "backend.app.mentor_routes.database.get_learner_profile_by_id",
        return_value=None,
    ) as mock_get_profile, patch(
        "backend.app.mentor_routes.create_practice_challenge",
    ) as mock_create_challenge:

        response = client.post(
            "/mentor/practice/challenge/missing-learner"
        )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Learner profile bulunamadı."
    }

    mock_get_profile.assert_called_once_with(
        "missing-learner"
    )

    mock_create_challenge.assert_not_called()


def test_create_practice_challenge_returns_400_when_no_recommendation():

    with patch(
        "backend.app.mentor_routes.database.get_learner_profile_by_id",
        return_value={"learner_id": "demo-learner"},
    ), patch(
        "backend.app.mentor_routes.create_practice_challenge",
        side_effect=ValueError(
            "Bu learner için şu anda practice recommendation yok."
        ),
    ):

        response = client.post(
            "/mentor/practice/challenge/demo-learner"
        )

    assert response.status_code == 400

    assert response.json() == {
        "detail": (
            "Bu learner için şu anda "
            "practice recommendation yok."
        )
    }

def test_review_practice_attempt_returns_review():

    fake_review = {
        "learner_id": "demo-learner",
        "challenge_id": "challenge-001",
        "attempt_id": "attempt-001",
        "attempt_number": 1,
        "validation": {
            "success": True,
            "feedback": "Challenge başarıyla tamamlandı.",
        },
        "diagnosis": None,
        "mentor_decision": None,
        "mentor_support": None,
    }

    with patch(
        "backend.app.mentor_routes.database.get_learner_profile_by_id",
        return_value={
            "learner_id": "demo-learner",
        },
    ) as mock_get_profile, patch(
        "backend.app.mentor_routes.database.get_practice_challenge",
        return_value=object(),
    ) as mock_get_challenge, patch(
        "backend.app.mentor_routes.review_practice_attempt",
        return_value=fake_review,
    ) as mock_review:

        response = client.post(
            "/mentor/practice/attempt",
            json={
                "learner_id": "demo-learner",
                "challenge_id": "challenge-001",
                "answer": "print(2)",
                "execution_output": "2",
                "execution_error": None,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
    "learner_id": "demo-learner",
    "challenge_id": "challenge-001",
    "attempt_id": "attempt-001",
    "attempt_number": 1,
    "validation": {
        "success": True,
        "feedback": "Challenge başarıyla tamamlandı.",
    },
    "mentor_support": None,
    }
    
    assert "diagnosis" not in response.json()
    assert "mentor_decision" not in response.json()

    mock_get_profile.assert_called_once_with(
        "demo-learner"
    )

    mock_get_challenge.assert_called_once_with(
        challenge_id="challenge-001",
        learner_id="demo-learner",
    )

    mock_review.assert_called_once()

    called_attempt = (
        mock_review.call_args.kwargs["attempt"]
    )

    assert called_attempt.learner_id == "demo-learner"
    assert called_attempt.challenge_id == "challenge-001"
    assert called_attempt.execution_output == "2"

def test_review_practice_attempt_returns_404_for_missing_learner():

    with patch(
        "backend.app.mentor_routes.database.get_learner_profile_by_id",
        return_value=None,
    ) as mock_get_profile, patch(
        "backend.app.mentor_routes.database.get_practice_challenge",
    ) as mock_get_challenge, patch(
        "backend.app.mentor_routes.review_practice_attempt",
    ) as mock_review:

        response = client.post(
            "/mentor/practice/attempt",
            json={
                "learner_id": "missing-learner",
                "challenge_id": "challenge-001",
                "answer": "print(2)",
                "execution_output": "2",
                "execution_error": None,
            },
        )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Learner profile bulunamadı."
    }

    mock_get_profile.assert_called_once_with(
        "missing-learner"
    )

    mock_get_challenge.assert_not_called()
    mock_review.assert_not_called()


def test_review_practice_attempt_returns_404_for_missing_challenge():

    with patch(
        "backend.app.mentor_routes.database.get_learner_profile_by_id",
        return_value={
            "learner_id": "demo-learner",
        },
    ), patch(
        "backend.app.mentor_routes.database.get_practice_challenge",
        return_value=None,
    ) as mock_get_challenge, patch(
        "backend.app.mentor_routes.review_practice_attempt",
    ) as mock_review:

        response = client.post(
            "/mentor/practice/attempt",
            json={
                "learner_id": "demo-learner",
                "challenge_id": "missing-challenge",
                "answer": "print(2)",
                "execution_output": "2",
                "execution_error": None,
            },
        )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Practice challenge bulunamadı."
    }

    mock_get_challenge.assert_called_once_with(
        challenge_id="missing-challenge",
        learner_id="demo-learner",
    )

    mock_review.assert_not_called()


def test_review_practice_attempt_returns_400_for_service_error():

    with patch(
        "backend.app.mentor_routes.database.get_learner_profile_by_id",
        return_value={
            "learner_id": "demo-learner",
        },
    ), patch(
        "backend.app.mentor_routes.database.get_practice_challenge",
        return_value=object(),
    ), patch(
        "backend.app.mentor_routes.review_practice_attempt",
        side_effect=ValueError(
            "Bu challenge türü için validation henüz desteklenmiyor."
        ),
    ):

        response = client.post(
            "/mentor/practice/attempt",
            json={
                "learner_id": "demo-learner",
                "challenge_id": "challenge-001",
                "answer": "test",
                "execution_output": None,
                "execution_error": None,
            },
        )

    assert response.status_code == 400

    assert response.json() == {
        "detail": (
            "Bu challenge türü için validation "
            "henüz desteklenmiyor."
        )
    }

def test_update_learner_language():

    with patch(
        "backend.app.mentor_routes.database.get_learner_profile_by_id",
        return_value={
            "learner_id": "demo-learner",
        },
    ), patch(
        "backend.app.mentor_routes.database.update_learner_preferred_language",
    ) as mock_update:

        response = client.patch(
            "/mentor/profile/demo-learner/language",
            json={
                "preferred_language": "tr",
            },
        )

    assert response.status_code == 200

    assert response.json() == {
        "learner_id": "demo-learner",
        "preferred_language": "tr",
    }

    mock_update.assert_called_once_with(
        learner_id="demo-learner",
        preferred_language="tr",
    )