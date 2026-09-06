import pandas as pd

from backend.app.data_profile_service import build_data_profile


def test_build_data_profile():

    df = pd.DataFrame(
        {
            "name": ["Ali", "Ayse", "Ali"],
            "age": [30, None, 30],
            "city": ["Den Haag", "Rotterdam", "Den Haag"],
        }
    )

    profile = build_data_profile(df)

    assert profile["row_count"] == 3
    assert profile["column_count"] == 3
    assert profile["null_counts"]["age"] == 1
    assert profile["duplicate_count"] == 1
    assert profile["numeric_columns"] == ["age"]
    assert profile["numeric_summary"]["age"]["count"] == 2
    assert profile["numeric_summary"]["age"]["mean"] == 30.0