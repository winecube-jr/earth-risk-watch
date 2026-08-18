import pandas as pd
import pytest

from earth_risk_watch.elevation import rows_from_dem_earth_engine


def test_rows_from_dem_earth_engine() -> None:
    frame = rows_from_dem_earth_engine(
        [
            {
                "properties": {
                    "cell_id": "cell-1",
                    "elevation_mean": 12.0,
                    "elevation_stdDev": 2.0,
                    "elevation_min": 8.0,
                    "elevation_max": 16.0,
                    "slope_mean": 3.0,
                    "slope_stdDev": 1.0,
                }
            }
        ]
    )
    assert frame.loc[0, "dem_elevation_mean_m"] == 12.0
    assert frame.loc[0, "dem_slope_mean_degrees"] == 3.0


@pytest.mark.parametrize(
    "features",
    [
        [],
        [
            {"properties": {"cell_id": "duplicate", "elevation_mean": 1}},
            {"properties": {"cell_id": "duplicate", "elevation_mean": 1}},
        ],
        [{"properties": {"cell_id": "missing"}}],
    ],
)
def test_rows_from_dem_earth_engine_rejects_invalid_results(
    features: list[dict[str, object]],
) -> None:
    with pytest.raises(ValueError):
        rows_from_dem_earth_engine(features)


def test_dem_frame_has_numeric_metrics() -> None:
    frame = rows_from_dem_earth_engine(
        [
            {
                "properties": {
                    "cell_id": "cell-1",
                    "elevation_mean": 1,
                    "elevation_stdDev": 2,
                    "elevation_min": 0,
                    "elevation_max": 4,
                    "slope_mean": 5,
                    "slope_stdDev": 6,
                }
            }
        ]
    )
    assert all(pd.api.types.is_numeric_dtype(frame[column]) for column in frame.columns[1:])
