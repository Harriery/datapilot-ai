import pandas as pd
import pytest

from backend.app.mentor_local_investigation_service import (
    verify_missingness_relationship,
)


def test_missingness_relationship_counts_each_group():
    sample = pd.DataFrame({
        "reason": [None, None, "weather", None, "other"],
        "status": [0, 0, 1, 1, 1],
    })
    result = verify_missingness_relationship(
        sample,
        target_column="reason",
        group_column="status",
    )
    assert result["total_rows"] == 5
    assert result["total_missing"] == 3
    assert result["verification_status"] == "verified"
    assert result["business_rule_confirmed"] is False
    groups = {row["value"]: row for row in result["groups"]}
    assert groups["0"]["missing_rows"] == 2
    assert groups["0"]["present_rows"] == 0
    assert groups["1"]["missing_rows"] == 1
    assert groups["1"]["present_rows"] == 2


def test_missingness_relationship_rejects_bad_columns():
    data = pd.DataFrame({"a": [None], "b": [1]})
    with pytest.raises(ValueError, match="exist"):
        verify_missingness_relationship(
            data, target_column="nonexistent", group_column="b"
        )
    with pytest.raises(ValueError, match="distinct"):
        verify_missingness_relationship(
            data, target_column="a", group_column="a"
        )


def test_missingness_relationship_bounds_high_cardinality_groups():
    data = pd.DataFrame({
        "optional": [None] * 60,
        "group": [f"g{i}" for i in range(60)],
    })
    result = verify_missingness_relationship(
        data, target_column="optional", group_column="group", max_groups=5
    )
    assert len(result["groups"]) == 5
    assert result["groups_truncated"] is True
    assert result["total_missing"] == 60
