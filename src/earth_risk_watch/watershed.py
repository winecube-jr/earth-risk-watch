"""Deterministic D8 outlet snapping and upstream-cell delineation."""

from collections import deque
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

D8_OFFSETS = {
    1: (0, 1),
    2: (1, 1),
    4: (1, 0),
    8: (1, -1),
    16: (0, -1),
    32: (-1, -1),
    64: (-1, 0),
    128: (-1, 1),
}


def snap_to_maximum_upstream_area(
    upstream_area: np.ndarray,
    row: int,
    column: int,
    *,
    radius_pixels: int = 5,
) -> tuple[int, int]:
    """Snap a point to the largest finite upstream-area pixel nearby."""
    if upstream_area.ndim != 2:
        raise ValueError("upstream_area must be a two-dimensional array")
    if radius_pixels < 0:
        raise ValueError("radius_pixels must not be negative")
    height, width = upstream_area.shape
    if not (0 <= row < height and 0 <= column < width):
        raise ValueError("Point pixel is outside the raster")
    row_min, row_max = max(0, row - radius_pixels), min(height, row + radius_pixels + 1)
    col_min, col_max = max(0, column - radius_pixels), min(width, column + radius_pixels + 1)
    window = upstream_area[row_min:row_max, col_min:col_max]
    finite = np.isfinite(window)
    if not finite.any():
        raise ValueError("No finite upstream-area pixel is available within the snap radius")
    candidates = np.argwhere(finite)
    values = window[finite]
    maximum = np.max(values)
    maximum_candidates = candidates[values == maximum]
    distances = np.square(maximum_candidates[:, 0] + row_min - row) + np.square(
        maximum_candidates[:, 1] + col_min - column
    )
    selected = maximum_candidates[np.argmin(distances)]
    return int(selected[0] + row_min), int(selected[1] + col_min)


def delineate_d8(flow_direction: np.ndarray, outlet: tuple[int, int]) -> np.ndarray:
    """Return the cells draining to an outlet under MERIT's D8 convention."""
    if flow_direction.ndim != 2:
        raise ValueError("flow_direction must be a two-dimensional array")
    height, width = flow_direction.shape
    outlet_row, outlet_column = outlet
    if not (0 <= outlet_row < height and 0 <= outlet_column < width):
        raise ValueError("Outlet pixel is outside the raster")
    watershed = np.zeros(flow_direction.shape, dtype=bool)
    watershed[outlet] = True
    queue: deque[tuple[int, int]] = deque([outlet])
    while queue:
        target_row, target_column = queue.popleft()
        for code, (row_offset, column_offset) in D8_OFFSETS.items():
            source_row = target_row - row_offset
            source_column = target_column - column_offset
            if not (0 <= source_row < height and 0 <= source_column < width):
                continue
            if watershed[source_row, source_column]:
                continue
            if int(flow_direction[source_row, source_column]) == code:
                watershed[source_row, source_column] = True
                queue.append((source_row, source_column))
    return watershed


def site_delineation_diagnostics(
    routing_path: Path,
    points_path: Path,
    observations_path: Path,
    *,
    snap_radius_pixels: int = 5,
) -> pd.DataFrame:
    """Delineate active monitoring sites and report snap and truncation checks."""
    points = gpd.read_file(points_path)
    observations = pd.read_parquet(observations_path)
    active = points.loc[points["notation"].isin(observations["point_notation"].unique())]
    records = []
    with rasterio.open(routing_path) as source:
        active = active.to_crs(source.crs)
        flow_direction = source.read(1)
        upstream_area = source.read(2)
        for point in active.itertuples(index=False):
            row, column = source.index(point.geometry.x, point.geometry.y)
            snapped = snap_to_maximum_upstream_area(
                upstream_area, row, column, radius_pixels=snap_radius_pixels
            )
            watershed = delineate_d8(flow_direction, snapped)
            touches_boundary = bool(
                watershed[0, :].any()
                or watershed[-1, :].any()
                or watershed[:, 0].any()
                or watershed[:, -1].any()
            )
            records.append(
                {
                    "point_notation": point.notation,
                    "source_row": row,
                    "source_column": column,
                    "outlet_row": snapped[0],
                    "outlet_column": snapped[1],
                    "snap_distance_pixels": float(np.hypot(snapped[0] - row, snapped[1] - column)),
                    "outlet_upstream_area_km2": float(upstream_area[snapped]),
                    "watershed_pixel_count": int(watershed.sum()),
                    "touches_raster_boundary": touches_boundary,
                }
            )
    return pd.DataFrame(records).sort_values("point_notation").reset_index(drop=True)


def save_site_delineation_diagnostics(
    routing_path: Path,
    points_path: Path,
    observations_path: Path,
    output: Path,
    *,
    snap_radius_pixels: int = 5,
) -> Path:
    """Save active-site watershed diagnostic records."""
    frame = site_delineation_diagnostics(
        routing_path,
        points_path,
        observations_path,
        snap_radius_pixels=snap_radius_pixels,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    return output
