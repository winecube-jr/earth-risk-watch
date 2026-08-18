import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, box

from earth_risk_watch.monitoring_features import (
    add_satellite_season,
    assign_sites_to_grid,
    build_monitoring_feature_table,
    modelling_readiness,
)


def fixtures() -> tuple[pd.DataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame, pd.DataFrame]:
    observations = pd.DataFrame(
        {
            "point_notation": ["site-1", "site-1", "site-1"],
            "observed_at": pd.to_datetime(["2024-01-15", "2024-02-15", "2024-12-10"]),
            "determinand_code": ["0117", "0117", "0117"],
            "determinand": ["Nitrate as N"] * 3,
            "unit": ["mg/l"] * 3,
            "analysis_value": [1.0, 3.0, 99.0],
            "is_censored": [False, True, False],
        }
    )
    points = gpd.GeoDataFrame({"notation": ["site-1"]}, geometry=[Point(0.5, 0.5)], crs="EPSG:4326")
    grid = gpd.GeoDataFrame({"cell_id": ["cell-1"]}, geometry=[box(0, 0, 1, 1)], crs="EPSG:4326")
    satellite = pd.DataFrame(
        {
            "cell_id": ["cell-1"],
            "season": ["winter"],
            "start_date": ["2024-01-01"],
            "end_date": ["2024-03-01"],
            "scene_count": [9],
            "NDVI_mean": [0.7],
        }
    )
    return observations, points, grid, satellite


def test_assign_sites_to_grid() -> None:
    _, points, grid, _ = fixtures()
    result = assign_sites_to_grid(points, grid)
    assert result.to_dict("records") == [{"notation": "site-1", "cell_id": "cell-1"}]


def test_add_satellite_season_excludes_outside_window() -> None:
    observations, _, _, satellite = fixtures()
    result = add_satellite_season(observations, satellite)
    assert result["season"].tolist()[:2] == ["winter", "winter"]
    assert pd.isna(result.loc[2, "season"])


def test_build_monitoring_feature_table() -> None:
    observations, points, grid, satellite = fixtures()
    result = build_monitoring_feature_table(observations, points, grid, satellite)
    assert len(result) == 1
    assert result.loc[0, "target_mean"] == 2.0
    assert result.loc[0, "observation_count"] == 2
    assert result.loc[0, "censored_fraction"] == 0.5
    assert result.loc[0, "NDVI_mean"] == 0.7


def test_assign_sites_requires_crs() -> None:
    _, points, grid, _ = fixtures()
    points = points.set_crs(None, allow_override=True)
    with pytest.raises(ValueError, match="must both have a CRS"):
        assign_sites_to_grid(points, grid)


def test_modelling_readiness_blocks_small_pilot() -> None:
    observations, points, grid, satellite = fixtures()
    table = build_monitoring_feature_table(observations, points, grid, satellite)
    result = modelling_readiness(table)
    assert result["ready_for_predictive_modelling"] is False
    assert result["monitored_cells"] == 1
    assert result["reasons"]
