"""Hydrologic-context feature normalization."""

from typing import Any

import pandas as pd

HYDROLOGY_COLUMNS = (
    "cell_id",
    "upstream_area_mean_km2",
    "upstream_area_max_km2",
    "height_above_drainage_mean_m",
    "height_above_drainage_std_m",
    "river_width_max_m",
    "permanent_water_fraction",
)


def rows_from_hydrology_earth_engine(features: list[dict[str, Any]]) -> pd.DataFrame:
    """Normalize MERIT Hydro reduceRegions output into one row per cell."""
    rows = []
    for feature in features:
        properties = feature.get("properties", {})
        rows.append(
            {
                "cell_id": str(properties["cell_id"]),
                "upstream_area_mean_km2": properties.get("upa_mean"),
                "upstream_area_max_km2": properties.get("upa_max"),
                "height_above_drainage_mean_m": properties.get("hnd_mean"),
                "height_above_drainage_std_m": properties.get("hnd_stdDev"),
                "river_width_max_m": properties.get("wth_max"),
                "permanent_water_fraction": properties.get("wat_mean"),
            }
        )
    frame = pd.DataFrame(rows).reindex(columns=HYDROLOGY_COLUMNS)
    if frame.empty:
        raise ValueError("Earth Engine returned no hydrology cells")
    if frame["cell_id"].duplicated().any():
        raise ValueError("Earth Engine returned duplicate hydrology cell IDs")
    metrics = list(HYDROLOGY_COLUMNS[1:])
    if frame[metrics].isna().any().any():
        raise ValueError("Earth Engine returned incomplete hydrology metrics")
    if not frame["permanent_water_fraction"].between(0, 1).all():
        raise ValueError("Permanent-water fraction must be between zero and one")
    return frame.sort_values("cell_id").reset_index(drop=True)
