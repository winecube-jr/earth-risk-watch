from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

from earth_risk_watch.watershed import (
    delineate_d8,
    site_watershed_polygons,
    snap_to_maximum_upstream_area,
    watershed_raster_features,
)


def test_delineate_d8_traces_all_cells_to_outlet() -> None:
    directions = np.array(
        [
            [2, 4, 8],
            [1, 4, 16],
            [1, 0, 16],
        ]
    )
    result = delineate_d8(directions, (2, 1))
    assert result.all()


def test_delineate_d8_excludes_other_drainage() -> None:
    directions = np.array([[1, 0, 16], [64, 64, 64]])
    result = delineate_d8(directions, (0, 1))
    assert result.tolist() == [[True, True, True], [True, True, True]]
    isolated = delineate_d8(np.array([[0, 0], [64, 64]]), (0, 0))
    assert isolated.tolist() == [[True, False], [True, False]]


def test_snap_uses_maximum_area_then_nearest_tie() -> None:
    area = np.array([[1.0, 9.0, 1.0], [9.0, 2.0, 1.0], [1.0, 1.0, 1.0]])
    assert snap_to_maximum_upstream_area(area, 1, 1, radius_pixels=1) == (0, 1)


def test_watershed_inputs_are_validated() -> None:
    with pytest.raises(ValueError, match="two-dimensional"):
        delineate_d8(np.array([1, 2]), (0, 0))
    with pytest.raises(ValueError, match="outside"):
        delineate_d8(np.zeros((2, 2)), (3, 3))
    with pytest.raises(ValueError, match="negative"):
        snap_to_maximum_upstream_area(np.zeros((2, 2)), 0, 0, radius_pixels=-1)
    with pytest.raises(ValueError, match="finite"):
        snap_to_maximum_upstream_area(np.full((2, 2), np.nan), 0, 0)


def test_watershed_raster_features_records_statistics_and_coverage(tmp_path: Path) -> None:
    watersheds_path = tmp_path / "watersheds.geojson"
    gpd.GeoDataFrame(
        {"point_notation": ["site-1"], "geometry": [box(0, 0, 2, 2)]}, crs="EPSG:3857"
    ).to_file(watersheds_path, driver="GeoJSON")
    raster_path = tmp_path / "pressure.tif"
    with rasterio.open(
        raster_path,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=1,
        dtype="float32",
        crs="EPSG:3857",
        transform=from_origin(0, 2, 1, 1),
        nodata=-9999,
    ) as target:
        target.write(np.array([[1, 2], [3, -9999]], dtype="float32"), 1)
        target.set_band_description(1, "urban_fraction")

    result = watershed_raster_features(watersheds_path, raster_path)

    assert result.loc[0, "urban_fraction_valid_pixel_count"] == 3
    assert result.loc[0, "urban_fraction_coverage_fraction"] == pytest.approx(0.75)
    assert result.loc[0, "urban_fraction_mean"] == pytest.approx(2.0)
    assert result.loc[0, "urban_fraction_sum"] == pytest.approx(6.0)


def test_watershed_raster_features_rejects_duplicate_sites(tmp_path: Path) -> None:
    watersheds_path = tmp_path / "watersheds.geojson"
    gpd.GeoDataFrame(
        {
            "point_notation": ["site-1", "site-1"],
            "geometry": [box(0, 0, 1, 1), box(1, 0, 2, 1)],
        },
        crs="EPSG:3857",
    ).to_file(watersheds_path, driver="GeoJSON")
    raster_path = tmp_path / "pressure.tif"
    with rasterio.open(
        raster_path,
        "w",
        driver="GTiff",
        width=2,
        height=1,
        count=1,
        dtype="float32",
        crs="EPSG:3857",
        transform=from_origin(0, 1, 1, 1),
    ) as target:
        target.write(np.ones((1, 2), dtype="float32"), 1)

    with pytest.raises(ValueError, match="duplicate"):
        watershed_raster_features(watersheds_path, raster_path)


def test_site_watershed_polygons_builds_complete_active_site(tmp_path: Path) -> None:
    routing_path = tmp_path / "routing.tif"
    with rasterio.open(
        routing_path,
        "w",
        driver="GTiff",
        width=5,
        height=5,
        count=3,
        dtype="float32",
        crs="EPSG:3857",
        transform=from_origin(0, 5, 1, 1),
    ) as target:
        target.write(np.zeros((5, 5), dtype="float32"), 1)
        upstream_area = np.ones((5, 5), dtype="float32")
        upstream_area[2, 2] = 10
        target.write(upstream_area, 2)
        target.write(np.ones((5, 5), dtype="float32"), 3)
    points_path = tmp_path / "points.geojson"
    gpd.GeoDataFrame(
        {"notation": ["active", "inactive"], "geometry": [box(2, 2, 3, 3).centroid] * 2},
        crs="EPSG:3857",
    ).to_file(points_path, driver="GeoJSON")
    observations_path = tmp_path / "observations.parquet"
    pd.DataFrame({"point_notation": ["active"]}).to_parquet(observations_path)

    result = site_watershed_polygons(
        routing_path, points_path, observations_path, snap_radius_pixels=0
    )

    assert result["point_notation"].tolist() == ["active"]
    assert result.loc[0, "watershed_pixel_count"] == 1
    assert result.loc[0, "outlet_upstream_pixel_count"] == 1
    assert result.loc[0, "delineated_to_upstream_pixel_ratio"] == pytest.approx(1)
    assert result.loc[0, "topology_consistent"]
    assert result.loc[0, "outlet_upstream_area_km2"] == pytest.approx(10)
    assert not result.loc[0, "touches_raster_boundary"]
    assert result.geometry.is_valid.all()
