import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, box

from earth_risk_watch.risk_screen import (
    add_weight_sensitivity,
    build_risk_screen,
    percentile_score,
)


def test_percentile_score_and_reverse() -> None:
    values = pd.Series([1.0, 2.0, 3.0])
    assert percentile_score(values).is_monotonic_increasing
    assert percentile_score(values, reverse=True).is_monotonic_decreasing
    assert percentile_score(pd.Series([4.0, 4.0])).tolist() == [50.0, 50.0]


def test_percentile_score_rejects_missing() -> None:
    with pytest.raises(ValueError, match="missing"):
        percentile_score(pd.Series([1.0, None]))


def test_weight_sensitivity_is_deterministic() -> None:
    frame = pd.DataFrame(
        {
            "sediment_pressure": [10.0, 90.0],
            "runoff_susceptibility": [20.0, 80.0],
            "condition_stress": [30.0, 70.0],
        }
    )
    first = add_weight_sensitivity(frame)
    second = add_weight_sensitivity(frame)
    assert first["weight_sensitivity_std"].equals(second["weight_sensitivity_std"])
    assert first.loc[1, "top_quintile_frequency"] == 1.0
    with pytest.raises(ValueError, match="At least 100"):
        add_weight_sensitivity(frame, simulations=99)


def test_build_risk_screen() -> None:
    grid = gpd.GeoDataFrame(
        {"cell_id": ["one", "two"], "coverage": [1.0, 1.0], "area_m2": [1.0, 1.0]},
        geometry=[box(0, 0, 1000, 1000), box(1000, 0, 2000, 1000)],
        crs="EPSG:27700",
    )
    rows = []
    for cell, offset in [("one", 0.0), ("two", 0.2)]:
        for season in ["winter", "spring", "summer", "autumn"]:
            rows.append(
                {
                    "cell_id": cell,
                    "season": season,
                    "BSI_mean": -0.2 + offset,
                    "NDMI_mean": 0.4 - offset,
                    "MNDWI_mean": -0.4 + offset,
                    "NDVI_mean": 0.7 - offset,
                    "scene_count": 10,
                }
            )
    terrain = pd.DataFrame(
        {
            "cell_id": ["one", "two"],
            "slope_p90_degrees": [2.0, 12.0],
            "relief_m": [20.0, 120.0],
        }
    )
    points = gpd.GeoDataFrame({"notation": ["site"]}, geometry=[Point(500, 500)], crs="EPSG:27700")
    observations = pd.DataFrame({"point_notation": ["site"]})
    result = build_risk_screen(grid, pd.DataFrame(rows), terrain, points, observations)
    assert len(result) == 2
    assert (
        result.loc[result["cell_id"] == "two", "screening_score"].iloc[0]
        > result.loc[result["cell_id"] == "one", "screening_score"].iloc[0]
    )
    assert result["has_monitoring_site"].sum() == 1
    assert result["top_quintile_frequency"].between(0, 1).all()
    assert set(result["screening_band"]).issubset(
        {"very low", "low", "moderate", "high", "very high"}
    )
