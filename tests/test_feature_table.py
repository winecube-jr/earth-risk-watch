from typing import Any

import pandas as pd
import pytest

from earth_risk_watch.feature_table import (
    FEATURE_COLUMNS,
    rows_from_earth_engine,
    validate_feature_table,
)


def valid_frame() -> pd.DataFrame:
    row: dict[str, Any] = {column: 0.1 for column in FEATURE_COLUMNS}
    row.update(
        {
            "cell_id": "bng-2000m-1-1",
            "season": "winter",
            "start_date": "2024-01-01",
            "end_date": "2024-03-01",
            "coverage": 0.8,
            "area_m2": 3_200_000.0,
            "scene_count": 9,
        }
    )
    return pd.DataFrame([row])


def test_rows_from_earth_engine() -> None:
    features = [
        {
            "properties": {
                "cell_id": "cell-1",
                "coverage": 0.5,
                "area_m2": 2_000_000,
                "NDVI_mean": 0.7,
            }
        }
    ]
    rows = rows_from_earth_engine(
        features,
        season="summer",
        start_date="2024-06-01",
        end_date="2024-09-01",
        scene_count=19,
    )
    assert rows[0]["cell_id"] == "cell-1"
    assert rows[0]["NDVI_mean"] == 0.7
    assert rows[0]["NDMI_mean"] is None
    assert rows[0]["scene_count"] == 19


def test_validate_feature_table() -> None:
    validate_feature_table(valid_frame())


def test_validate_feature_table_rejects_bad_schema() -> None:
    with pytest.raises(ValueError, match="Missing feature columns"):
        validate_feature_table(pd.DataFrame({"cell_id": ["cell-1"]}))
    with pytest.raises(ValueError, match="empty"):
        validate_feature_table(pd.DataFrame(columns=FEATURE_COLUMNS))


def test_validate_feature_table_rejects_bad_rows() -> None:
    frame = valid_frame()
    frame.loc[0, "cell_id"] = None
    with pytest.raises(ValueError, match="missing cell IDs"):
        validate_feature_table(frame)
    frame = pd.concat([valid_frame(), valid_frame()], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        validate_feature_table(frame)
    frame = valid_frame()
    frame.loc[0, "coverage"] = 2
    with pytest.raises(ValueError, match="between zero and one"):
        validate_feature_table(frame)
