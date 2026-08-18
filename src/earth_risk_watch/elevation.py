"""Common-coverage elevation feature normalization."""

from typing import Any

import pandas as pd

DEM_COLUMNS = (
    "cell_id",
    "dem_elevation_mean_m",
    "dem_elevation_std_m",
    "dem_elevation_min_m",
    "dem_elevation_max_m",
    "dem_slope_mean_degrees",
    "dem_slope_std_degrees",
)


def rows_from_dem_earth_engine(features: list[dict[str, Any]]) -> pd.DataFrame:
    """Normalize Earth Engine reduceRegions output into one row per cell."""
    rows = []
    for feature in features:
        properties = feature.get("properties", {})
        rows.append(
            {
                "cell_id": str(properties["cell_id"]),
                "dem_elevation_mean_m": properties.get("elevation_mean"),
                "dem_elevation_std_m": properties.get("elevation_stdDev"),
                "dem_elevation_min_m": properties.get("elevation_min"),
                "dem_elevation_max_m": properties.get("elevation_max"),
                "dem_slope_mean_degrees": properties.get("slope_mean"),
                "dem_slope_std_degrees": properties.get("slope_stdDev"),
            }
        )
    frame = pd.DataFrame(rows).reindex(columns=DEM_COLUMNS)
    if frame.empty:
        raise ValueError("Earth Engine returned no DEM cells")
    if frame["cell_id"].duplicated().any():
        raise ValueError("Earth Engine returned duplicate DEM cell IDs")
    metrics = list(DEM_COLUMNS[1:])
    if frame[metrics].isna().any().any():
        raise ValueError("Earth Engine returned incomplete DEM metrics")
    return frame.sort_values("cell_id").reset_index(drop=True)
