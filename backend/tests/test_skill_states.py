import backend.app.database as database

def test_insert_and_get_skill_state(tmp_path):
    database.DATABASE_PATH = tmp_path / "test.db"
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )

    database.insert_skill_state(
        learner_id="learner-001",
        skill_name="python_dict",
        status="learning",
    )

    skill = database.get_skill_state(
        "learner-001",
        "python_dict",
    )

    assert skill["learner_id"] == "learner-001"
    assert skill["skill_name"] == "python_dict"
    assert skill["status"] == "learning"


def test_get_all_skill_states_by_learner(tmp_path):
    database.DATABASE_PATH = tmp_path / "test.db"
    database.init_db()

    database.insert_learner_profile(
        learner_id="learner-001",
        answer_length="concise",
        learning_style="guided",
        code_support="medium",
    )

    database.insert_skill_state(
        learner_id="learner-001",
        skill_name="python_dict",
        status="learning",
    )


    database.insert_skill_state(
        learner_id="learner-001",
        skill_name="null_analysis",
        status="practicing",
    )
    skills = database.get_skill_states_by_learner("learner-001")

    assert len(skills) == 2
    assert skills[0]["skill_name"] == "python_dict"
    assert skills[0]["status"] == "learning"
    
    assert skills[1]["skill_name"] == "null_analysis"
    assert skills[1]["status"] == "practicing"
    
  