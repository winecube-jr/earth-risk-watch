"""Deterministic modelling grids in British National Grid."""

from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import box

BRITISH_NATIONAL_GRID = "EPSG:27700"
WEB_GEOGRAPHIC = "EPSG:4326"


def build_clipped_grid(
    geometry_path: Path,
    output: Path,
    *,
    cell_size_metres: int = 2_000,
) -> Path:
    """Create stable square modelling units clipped to an input boundary."""
    if cell_size_metres <= 0:
        raise ValueError("cell_size_metres must be positive")
    boundary = gpd.read_file(geometry_path).to_crs(BRITISH_NATIONAL_GRID)
    if boundary.empty:
        raise ValueError("boundary contains no features")
    dissolved = boundary.geometry.union_all()
    min_x, min_y, max_x, max_y = dissolved.bounds
    start_x = np.floor(min_x / cell_size_metres) * cell_size_metres
    start_y = np.floor(min_y / cell_size_metres) * cell_size_metres
    records: list[dict[str, object]] = []
    for x in np.arange(start_x, max_x, cell_size_metres):
        for y in np.arange(start_y, max_y, cell_size_metres):
            square = box(x, y, x + cell_size_metres, y + cell_size_metres)
            clipped = square.intersection(dissolved)
            coverage = clipped.area / square.area
            if clipped.is_empty or coverage < 0.001:
                continue
            grid_x = int(x // cell_size_metres)
            grid_y = int(y // cell_size_metres)
            records.append(
                {
                    "cell_id": f"bng-{cell_size_metres}m-{grid_x}-{grid_y}",
                    "coverage": coverage,
                    "area_m2": clipped.area,
                    "geometry": clipped,
                }
            )
    grid = gpd.GeoDataFrame(records, geometry="geometry", crs=BRITISH_NATIONAL_GRID)
    grid = grid.sort_values("cell_id").reset_index(drop=True).to_crs(WEB_GEOGRAPHIC)
    output.parent.mkdir(parents=True, exist_ok=True)
    grid.to_file(output, driver="GeoJSON")
    return output
