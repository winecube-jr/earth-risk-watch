import json
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import box

from earth_risk_watch.grid import build_clipped_grid


def write_boundary(path: Path) -> None:
    frame = gpd.GeoDataFrame(
        {"name": ["test"]},
        geometry=[box(400_000, 300_000, 404_000, 304_000)],
        crs="EPSG:27700",
    ).to_crs("EPSG:4326")
    frame.to_file(path, driver="GeoJSON")


def test_build_clipped_grid(tmp_path: Path) -> None:
    boundary = tmp_path / "boundary.geojson"
    output = tmp_path / "grid.geojson"
    write_boundary(boundary)
    build_clipped_grid(boundary, output, cell_size_metres=2_000)
    grid = gpd.read_file(output)
    assert len(grid) == 4
    assert grid["cell_id"].is_unique
    assert grid.crs is not None and grid.crs.to_epsg() == 4326
    assert all(grid["coverage"].between(0.99, 1.0))
    assert json.loads(output.read_text(encoding="utf-8"))["type"] == "FeatureCollection"


def test_grid_rejects_invalid_inputs(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="positive"):
        build_clipped_grid(
            tmp_path / "missing.geojson", tmp_path / "out.geojson", cell_size_metres=0
        )
