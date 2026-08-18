"""Bounded Environment Agency LiDAR terrain extraction and features."""

import hashlib
import json
import math
from pathlib import Path

import geopandas as gpd
import httpx
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry import mapping

from earth_risk_watch.http_client import get_bytes, open_data_client

WCS_ENDPOINT = (
    "https://environment.data.gov.uk/geoservices/datasets/13787b9a-26a4-4775-8523-806d13af58fc/wcs"
)
COVERAGE_ID = "13787b9a-26a4-4775-8523-806d13af58fc__Lidar_Composite_Elevation_DTM_1m"


def lidar_request_params(
    geometry_path: Path, *, output_resolution_metres: int = 10
) -> dict[str, str | list[str]]:
    """Build a pilot-only WCS request in British National Grid coordinates."""
    if output_resolution_metres < 1:
        raise ValueError("output_resolution_metres must be at least 1")
    bounds = gpd.read_file(geometry_path).to_crs("EPSG:27700").total_bounds
    min_x, min_y = (math.floor(value / 100) * 100 for value in bounds[:2])
    max_x, max_y = (math.ceil(value / 100) * 100 for value in bounds[2:])
    return {
        "service": "WCS",
        "version": "2.0.1",
        "request": "GetCoverage",
        "coverageId": COVERAGE_ID,
        "format": "image/tiff",
        "subset": [f"E({min_x},{max_x})", f"N({min_y},{max_y})"],
        "scaleFactor": str(1 / output_resolution_metres),
    }


def save_lidar_subset(
    geometry_path: Path,
    output: Path,
    *,
    output_resolution_metres: int = 10,
    client: httpx.Client | None = None,
) -> Path:
    """Download a size-limited, server-resampled LiDAR DTM subset."""
    params = lidar_request_params(geometry_path, output_resolution_metres=output_resolution_metres)

    def retrieve(active_client: httpx.Client) -> bytes:
        request = active_client.build_request("GET", WCS_ENDPOINT, params=params)
        return get_bytes(active_client, str(request.url), max_bytes=50_000_000)

    if client is None:
        with open_data_client(timeout_seconds=180) as managed_client:
            body = retrieve(managed_client)
    else:
        body = retrieve(client)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(body)
    provenance = {
        "source": WCS_ENDPOINT,
        "coverage_id": COVERAGE_ID,
        "requested_resolution_metres": output_resolution_metres,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output


def terrain_features(dtm_path: Path, grid_path: Path) -> pd.DataFrame:
    """Summarize elevation and slope for every clipped modelling cell."""
    grid = gpd.read_file(grid_path)
    with rasterio.open(dtm_path) as source:
        grid = grid.to_crs(source.crs)
        elevation = source.read(1, masked=True).astype("float64")
        filled = elevation.filled(np.nan)
        y_gradient, x_gradient = np.gradient(
            filled, abs(source.transform.e), abs(source.transform.a)
        )
        slope = np.degrees(np.arctan(np.hypot(x_gradient, y_gradient)))
        records = []
        for cell in grid.itertuples(index=False):
            inside = geometry_mask(
                [mapping(cell.geometry)],
                out_shape=source.shape,
                transform=source.transform,
                invert=True,
            )
            valid = inside & ~np.ma.getmaskarray(elevation) & np.isfinite(filled)
            values = filled[valid]
            slopes = slope[valid & np.isfinite(slope)]
            if values.size == 0 or slopes.size == 0:
                records.append(
                    {
                        "cell_id": cell.cell_id,
                        "elevation_mean_m": np.nan,
                        "elevation_std_m": np.nan,
                        "elevation_min_m": np.nan,
                        "elevation_max_m": np.nan,
                        "relief_m": np.nan,
                        "slope_mean_degrees": np.nan,
                        "slope_p90_degrees": np.nan,
                        "valid_pixel_count": 0,
                    }
                )
                continue
            records.append(
                {
                    "cell_id": cell.cell_id,
                    "elevation_mean_m": float(np.mean(values)),
                    "elevation_std_m": float(np.std(values)),
                    "elevation_min_m": float(np.min(values)),
                    "elevation_max_m": float(np.max(values)),
                    "relief_m": float(np.max(values) - np.min(values)),
                    "slope_mean_degrees": float(np.mean(slopes)),
                    "slope_p90_degrees": float(np.percentile(slopes, 90)),
                    "valid_pixel_count": int(values.size),
                }
            )
    return pd.DataFrame(records).sort_values("cell_id").reset_index(drop=True)


def save_terrain_features(dtm_path: Path, grid_path: Path, output: Path) -> Path:
    """Save grid-level terrain predictors and checksum-bearing provenance."""
    frame = terrain_features(dtm_path, grid_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    provenance = {
        "grain": "cell_id",
        "rows": len(frame),
        "cells_with_lidar": int((frame["valid_pixel_count"] > 0).sum()),
        "cells_without_lidar": int((frame["valid_pixel_count"] == 0).sum()),
        "source_product": "EA LIDAR Composite DTM 1m, server-resampled by WCS",
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output
