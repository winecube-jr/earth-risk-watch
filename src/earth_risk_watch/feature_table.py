"""Schema and validation for model-ready spatial feature tables."""

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from earth_risk_watch.satellite import INDEX_BANDS

IDENTIFIER_COLUMNS = ("cell_id", "season", "start_date", "end_date")
CONTEXT_COLUMNS = ("coverage", "area_m2", "scene_count")
METRIC_COLUMNS = tuple(f"{index}_{stat}" for index in INDEX_BANDS for stat in ("mean", "stdDev"))
FEATURE_COLUMNS = IDENTIFIER_COLUMNS + CONTEXT_COLUMNS + METRIC_COLUMNS


def rows_from_earth_engine(
    features: Sequence[Mapping[str, Any]],
    *,
    season: str,
    start_date: str,
    end_date: str,
    scene_count: int,
) -> list[dict[str, Any]]:
    """Flatten Earth Engine FeatureCollection results into stable table rows."""
    rows: list[dict[str, Any]] = []
    for feature in features:
        properties = dict(feature.get("properties", {}))
        row = {
            "cell_id": properties.get("cell_id"),
            "season": season,
            "start_date": start_date,
            "end_date": end_date,
            "coverage": properties.get("coverage"),
            "area_m2": properties.get("area_m2"),
            "scene_count": scene_count,
        }
        row.update({column: properties.get(column) for column in METRIC_COLUMNS})
        rows.append(row)
    return rows


def validate_feature_table(frame: pd.DataFrame) -> None:
    """Reject incomplete or ambiguous tables before modelling."""
    missing = sorted(set(FEATURE_COLUMNS).difference(frame.columns))
    if missing:
        raise ValueError(f"Missing feature columns: {', '.join(missing)}")
    if frame.empty:
        raise ValueError("Feature table is empty")
    if frame["cell_id"].isna().any():
        raise ValueError("Feature table contains missing cell IDs")
    if frame.duplicated(["cell_id", "season"]).any():
        raise ValueError("Feature table contains duplicate cell-season rows")
    if not frame["coverage"].between(0, 1).all():
        raise ValueError("Grid coverage must be between zero and one")
