import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from earth_risk_watch.upstream_features import (
    build_site_upstream_monitoring_table,
    build_upstream_feature_table,
    site_modelling_readiness,
)


def upstream_fixtures() -> tuple[gpd.GeoDataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    watersheds = gpd.GeoDataFrame(
        {
            "point_notation": ["site-1"],
            "watershed_pixel_count": [10],
            "geometry": [box(0, 0, 1, 1)],
        },
        crs="EPSG:4326",
    )
    land_cover = pd.DataFrame(
        {
            "point_notation": ["site-1"],
            "cropland_fraction_mean": [0.4],
            "cropland_fraction_std": [0.1],
            "cropland_fraction_coverage_fraction": [1.0],
            "cropland_fraction_sum": [40.0],
        }
    )
    climate = pd.DataFrame(
        {
            "point_notation": ["site-1"],
            "precipitation_2024_mm_mean": [900.0],
            "precipitation_2024_mm_std": [5.0],
            "precipitation_2024_mm_coverage_fraction": [1.0],
        }
    )
    edm = pd.DataFrame({"point_notation": ["site-1"], "upstream_spill_count_2024": [3.0]})
    return watersheds, land_cover, climate, edm


def test_build_upstream_feature_table_selects_scale_safe_raster_statistics() -> None:
    result = build_upstream_feature_table(*upstream_fixtures())
    assert result.loc[0, "cropland_fraction_mean"] == 0.4
    assert result.loc[0, "precipitation_2024_mm_mean"] == 900
    assert result.loc[0, "upstream_spill_count_2024"] == 3
    assert "cropland_fraction_sum" not in result


def test_build_upstream_feature_table_requires_matching_sites() -> None:
    watersheds, land_cover, climate, edm = upstream_fixtures()
    climate["point_notation"] = "other-site"
    with pytest.raises(ValueError, match="site coverage"):
        build_upstream_feature_table(watersheds, land_cover, climate, edm)


def test_build_site_upstream_monitoring_table_keeps_site_grain() -> None:
    upstream = build_upstream_feature_table(*upstream_fixtures())
    observations = pd.DataFrame(
        {
            "point_notation": ["site-1", "site-1", "outside"],
            "observed_at": pd.to_datetime(["2024-01-10", "2024-01-20", "2024-01-10"]),
            "determinand_code": ["N", "N", "N"],
            "determinand": ["Nitrate", "Nitrate", "Nitrate"],
            "unit": ["mg/l", "mg/l", "mg/l"],
            "analysis_value": [1.0, 3.0, 99.0],
            "is_censored": [False, True, False],
        }
    )
    windows = pd.DataFrame(
        {"season": ["winter"], "start_date": ["2024-01-01"], "end_date": ["2024-03-01"]}
    )

    result = build_site_upstream_monitoring_table(observations, windows, upstream)

    assert len(result) == 1
    assert result.loc[0, "point_notation"] == "site-1"
    assert result.loc[0, "target_mean"] == 2
    assert result.loc[0, "censored_fraction"] == 0.5
    assert result.loc[0, "cropland_fraction_mean"] == 0.4
    readiness = site_modelling_readiness(result)
    assert readiness["ready_for_predictive_modelling"] is False
    assert readiness["complete_watershed_sites"] == 1
