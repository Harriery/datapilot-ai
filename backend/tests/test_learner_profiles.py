import backend.app.database as database


def test_insert_and_get_learner_profile(tmp_path):
    database.DATABASE_PATH = tmp_path / "test.db"   #pytest’in her test için oluşturduğu geçici klasör. Test bitince gerçek projemizin veritabanına dokunmamış oluyoruz.
    database.init_db()
    database.insert_learner_profile(
    learner_id="learner-001",
    answer_length="concise",
    learning_style="guided",
    code_support="medium",
    
    )

    profile = database.get_learner_profile_by_id("learner-001")
    assert profile is not None
    assert profile["learner_id"] == "learner-001"
    assert profile["answer_length"] == "concise"
    assert profile["learning_style"] == "guided"
    assert profile["code_support"] == "medium"

