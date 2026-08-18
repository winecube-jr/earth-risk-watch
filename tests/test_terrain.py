from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

from earth_risk_watch.terrain import lidar_request_params, terrain_features


def test_lidar_request_params(tmp_path: Path) -> None:
    geometry = tmp_path / "pilot.geojson"
    gpd.GeoDataFrame(
        {"name": ["pilot"]}, geometry=[box(350000, 460000, 351000, 461000)], crs=27700
    ).to_file(geometry, driver="GeoJSON")
    params = lidar_request_params(geometry)
    assert params["scaleFactor"] == "0.1"
    assert params["subset"] == ["E(350000,351000)", "N(460000,461000)"]


def test_lidar_request_rejects_resolution(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least 1"):
        lidar_request_params(tmp_path / "unused.geojson", output_resolution_metres=0)


def test_terrain_features(tmp_path: Path) -> None:
    raster = tmp_path / "dtm.tif"
    values = np.arange(100, dtype="float32").reshape(10, 10)
    with rasterio.open(
        raster,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="float32",
        crs="EPSG:27700",
        transform=from_origin(0, 100, 10, 10),
    ) as target:
        target.write(values, 1)
    grid = tmp_path / "grid.geojson"
    gpd.GeoDataFrame({"cell_id": ["cell-1"]}, geometry=[box(0, 0, 100, 100)], crs=27700).to_file(
        grid, driver="GeoJSON"
    )
    result = terrain_features(raster, grid)
    assert result.loc[0, "elevation_mean_m"] == pytest.approx(49.5)
    assert result.loc[0, "relief_m"] == 99
    assert result.loc[0, "valid_pixel_count"] == 100
    assert result.loc[0, "slope_mean_degrees"] > 0
