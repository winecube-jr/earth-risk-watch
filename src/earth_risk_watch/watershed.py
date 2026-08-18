"""Deterministic D8 outlet snapping and upstream-cell delineation."""

from collections import deque
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask, shapes
from rasterio.mask import mask as raster_mask
from shapely.geometry import shape

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


def _routing_concordance(
    watershed: np.ndarray,
    upstream_pixels: np.ndarray | None,
    outlet: tuple[int, int],
) -> tuple[float, float, bool]:
    """Compare traced cells with MERIT's upstream-pixel count when available."""
    if upstream_pixels is None:
        return float("nan"), float("nan"), True
    expected = float(upstream_pixels[outlet])
    ratio = float(watershed.sum() / expected) if np.isfinite(expected) and expected > 0 else np.nan
    consistent = bool(np.isfinite(ratio) and np.isclose(ratio, 1.0, rtol=0.01))
    return expected, ratio, consistent


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
        upstream_pixels = source.read(3) if source.count >= 3 else None
        for point in active.itertuples(index=False):
            row, column = source.index(point.geometry.x, point.geometry.y)
            snapped = snap_to_maximum_upstream_area(
                upstream_area, row, column, radius_pixels=snap_radius_pixels
            )
            watershed = delineate_d8(flow_direction, snapped)
            expected_pixels, concordance, topology_consistent = _routing_concordance(
                watershed, upstream_pixels, snapped
            )
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
                    "outlet_upstream_pixel_count": expected_pixels,
                    "delineated_to_upstream_pixel_ratio": concordance,
                    "topology_consistent": topology_consistent,
                    "touches_raster_boundary": touches_boundary,
                }
            )
    return pd.DataFrame(records).sort_values("point_notation").reset_index(drop=True)


def site_watershed_polygons(
    routing_path: Path,
    points_path: Path,
    observations_path: Path,
    *,
    snap_radius_pixels: int = 5,
    include_truncated: bool = False,
) -> gpd.GeoDataFrame:
    """Delineate active sites and return one dissolved pixel polygon per site."""
    points = gpd.read_file(points_path)
    observations = pd.read_parquet(observations_path)
    active = points.loc[points["notation"].isin(observations["point_notation"].unique())]
    records = []
    output_crs = None
    with rasterio.open(routing_path) as source:
        output_crs = source.crs
        active = active.to_crs(source.crs)
        flow_direction = source.read(1)
        upstream_area = source.read(2)
        upstream_pixels = source.read(3) if source.count >= 3 else None
        for point in active.itertuples(index=False):
            row, column = source.index(point.geometry.x, point.geometry.y)
            snapped = snap_to_maximum_upstream_area(
                upstream_area, row, column, radius_pixels=snap_radius_pixels
            )
            watershed = delineate_d8(flow_direction, snapped)
            expected_pixels, concordance, topology_consistent = _routing_concordance(
                watershed, upstream_pixels, snapped
            )
            touches_boundary = bool(
                watershed[0, :].any()
                or watershed[-1, :].any()
                or watershed[:, 0].any()
                or watershed[:, -1].any()
            )
            if (touches_boundary and not include_truncated) or not topology_consistent:
                continue
            pixel_shapes = [
                shape(geometry)
                for geometry, value in shapes(
                    watershed.astype("uint8"), mask=watershed, transform=source.transform
                )
                if value == 1
            ]
            geometry = pixel_shapes[0]
            for part in pixel_shapes[1:]:
                geometry = geometry.union(part)
            records.append(
                {
                    "point_notation": point.notation,
                    "snap_distance_pixels": float(np.hypot(snapped[0] - row, snapped[1] - column)),
                    "outlet_upstream_area_km2": float(upstream_area[snapped]),
                    "watershed_pixel_count": int(watershed.sum()),
                    "outlet_upstream_pixel_count": expected_pixels,
                    "delineated_to_upstream_pixel_ratio": concordance,
                    "topology_consistent": topology_consistent,
                    "touches_raster_boundary": touches_boundary,
                    "geometry": geometry,
                }
            )
    if not records:
        raise ValueError("No complete active-site watersheds were delineated")
    return (
        gpd.GeoDataFrame(records, geometry="geometry", crs=output_crs)
        .sort_values("point_notation")
        .reset_index(drop=True)
    )


def watershed_raster_features(
    watersheds_path: Path,
    raster_path: Path,
) -> pd.DataFrame:
    """Aggregate every raster band within each site watershed with coverage checks."""
    watersheds = gpd.read_file(watersheds_path)
    if "point_notation" not in watersheds:
        raise ValueError("Watersheds must contain point_notation")
    if watersheds["point_notation"].duplicated().any():
        raise ValueError("Watersheds contain duplicate point_notation values")
    records: list[dict[str, object]] = []
    with rasterio.open(raster_path) as source:
        projected = watersheds.to_crs(source.crs)
        band_names = [
            description or f"band_{index}"
            for index, description in enumerate(source.descriptions, 1)
        ]
        if len(set(band_names)) != len(band_names):
            raise ValueError("Raster band descriptions must be unique")
        for watershed in projected.itertuples(index=False):
            values, transform = raster_mask(
                source,
                [watershed.geometry],
                crop=True,
                filled=False,
                all_touched=True,
            )
            footprint = geometry_mask(
                [watershed.geometry],
                out_shape=values.shape[1:],
                transform=transform,
                invert=True,
                all_touched=True,
            )
            footprint_count = int(footprint.sum())
            record: dict[str, object] = {"point_notation": watershed.point_notation}
            for band_index, band_name in enumerate(band_names):
                band = values[band_index]
                valid = band.compressed().astype("float64")
                record[f"{band_name}_valid_pixel_count"] = int(valid.size)
                record[f"{band_name}_coverage_fraction"] = (
                    float(valid.size / footprint_count) if footprint_count else 0.0
                )
                record[f"{band_name}_mean"] = float(valid.mean()) if valid.size else np.nan
                record[f"{band_name}_std"] = float(valid.std()) if valid.size else np.nan
                record[f"{band_name}_min"] = float(valid.min()) if valid.size else np.nan
                record[f"{band_name}_max"] = float(valid.max()) if valid.size else np.nan
                record[f"{band_name}_sum"] = float(valid.sum()) if valid.size else np.nan
            records.append(record)
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


def save_site_watershed_polygons(
    routing_path: Path,
    points_path: Path,
    observations_path: Path,
    output: Path,
    *,
    snap_radius_pixels: int = 5,
    include_truncated: bool = False,
) -> Path:
    """Save active-site watershed polygons as GeoJSON."""
    frame = site_watershed_polygons(
        routing_path,
        points_path,
        observations_path,
        snap_radius_pixels=snap_radius_pixels,
        include_truncated=include_truncated,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_file(output, driver="GeoJSON")
    return output


def save_watershed_raster_features(
    watersheds_path: Path,
    raster_path: Path,
    output: Path,
) -> Path:
    """Save per-site pressure-raster summaries as Parquet."""
    frame = watershed_raster_features(watersheds_path, raster_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    return output
