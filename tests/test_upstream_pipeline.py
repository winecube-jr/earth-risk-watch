from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from earth_risk_watch.upstream_pipeline import routing_grid_is_current


def write_routing(path: Path, descriptions: tuple[str, ...]) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=len(descriptions),
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(0, 2, 1, 1),
    ) as target:
        target.write(np.zeros((len(descriptions), 2, 2), dtype="float32"))
        for index, description in enumerate(descriptions, 1):
            target.set_band_description(index, description)


def test_routing_grid_is_current_requires_three_named_bands(tmp_path: Path) -> None:
    current = tmp_path / "current.tif"
    legacy = tmp_path / "legacy.tif"
    write_routing(current, ("dir", "upa", "upg"))
    write_routing(legacy, ("dir", "upa"))

    assert routing_grid_is_current(current)
    assert not routing_grid_is_current(legacy)
    assert not routing_grid_is_current(tmp_path / "missing.tif")


def test_routing_grid_is_current_rejects_invalid_file(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.tif"
    invalid.write_text("not a raster", encoding="utf-8")
    assert not routing_grid_is_current(invalid)
