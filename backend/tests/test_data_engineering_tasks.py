import json

import backend.app.database as database

from backend.app.models import (
    DataEngineeringTask,
    DataEngineeringTaskStep,
    DataQualityFinding,
)


def test_save_data_engineering_task(tmp_path):

    database.DATABASE_PATH = tmp_path / "test.db"
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )

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

    task = DataEngineeringTask(
        task_id="task-001",
        title="Dataset problemlerini çöz",
        steps=[step],
        current_step_number=1,
        status="active",
    )

    database.save_data_engineering_task(
        learner_id="learner-001",
        task=task,
    )

    connection = database.get_connection()

    row = connection.execute(
        """
        SELECT *
        FROM data_engineering_tasks
        WHERE task_id = ?
        """,
        ("task-001",),
    ).fetchone()

    connection.close()

    assert row is not None
    assert row["learner_id"] == "learner-001"
    assert row["status"] == "active"

    saved_task = json.loads(row["task_json"])

    assert saved_task["task_id"] == "task-001"
    assert saved_task["current_step_number"] == 1
    assert saved_task["steps"][0]["status"] == "active"

def test_get_data_engineering_task(tmp_path):

    database.DATABASE_PATH = tmp_path / "test.db"
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )

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

    task = DataEngineeringTask(
        task_id="task-001",
        title="Dataset problemlerini çöz",
        steps=[step],
        current_step_number=1,
        status="active",
    )

    database.save_data_engineering_task(
        learner_id="learner-001",
        task=task,
    )

    loaded_task = database.get_data_engineering_task(
        task_id="task-001",
        learner_id="learner-001",
    )

    assert loaded_task is not None

    assert loaded_task.task_id == "task-001"
    assert loaded_task.title == "Dataset problemlerini çöz"
    assert loaded_task.current_step_number == 1
    assert loaded_task.status == "active"

    assert loaded_task.steps[0].status == "active"
    assert (
        loaded_task.steps[0].finding.issue_type
        == "missing_values"
    )

def test_get_data_engineering_task_returns_none_for_wrong_learner(
    tmp_path,
):

    database.DATABASE_PATH = tmp_path / "test.db"
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )

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

    task = DataEngineeringTask(
        task_id="task-001",
        title="Dataset problemlerini çöz",
        steps=[step],
        current_step_number=1,
        status="active",
    )

    database.save_data_engineering_task(
        learner_id="learner-001",
        task=task,
    )

    loaded_task = database.get_data_engineering_task(
        task_id="task-001",
        learner_id="different-learner",
    )

    assert loaded_task is None