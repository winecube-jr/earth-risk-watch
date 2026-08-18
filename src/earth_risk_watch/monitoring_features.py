"""Spatial-temporal linkage of water monitoring outcomes and satellite predictors."""

import hashlib
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

KEY_COLUMNS = ("cell_id", "season", "determinand_code")
MINIMUM_SPATIAL_GROUPS = 30


def assign_sites_to_grid(sampling_points: gpd.GeoDataFrame, grid: gpd.GeoDataFrame) -> pd.DataFrame:
    """Assign each sampling point to one clipped grid cell deterministically."""
    if sampling_points.crs is None or grid.crs is None:
        raise ValueError("Sampling points and grid must both have a CRS")
    if "notation" not in sampling_points or "cell_id" not in grid:
        raise ValueError("Expected notation and cell_id columns")
    points = sampling_points[["notation", "geometry"]].to_crs(grid.crs)
    joined = gpd.sjoin(points, grid[["cell_id", "geometry"]], predicate="intersects")
    assignments = (
        joined[["notation", "cell_id"]]
        .sort_values(["notation", "cell_id"])
        .drop_duplicates("notation")
        .reset_index(drop=True)
    )
    if assignments["notation"].duplicated().any():
        raise ValueError("Sampling points map ambiguously to grid cells")
    return pd.DataFrame(assignments)


def add_satellite_season(observations: pd.DataFrame, satellite: pd.DataFrame) -> pd.DataFrame:
    """Assign observations to the exact half-open satellite composite windows."""
    required = {"season", "start_date", "end_date"}
    if not required.issubset(satellite.columns):
        raise ValueError("Satellite table is missing seasonal window columns")
    frame = observations.copy()
    frame["season"] = pd.NA
    timestamps = pd.to_datetime(frame["observed_at"], errors="coerce")
    windows = satellite[list(required)].drop_duplicates()
    for window in windows.itertuples(index=False):
        start = pd.Timestamp(window.start_date)
        end = pd.Timestamp(window.end_date)
        mask = timestamps.ge(start) & timestamps.lt(end)
        frame.loc[mask, "season"] = window.season
    return frame


def build_monitoring_feature_table(
    observations: pd.DataFrame,
    sampling_points: gpd.GeoDataFrame,
    grid: gpd.GeoDataFrame,
    satellite: pd.DataFrame,
    terrain: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Aggregate site observations and attach same-cell, same-season predictors."""
    assignments = assign_sites_to_grid(sampling_points, grid)
    linked = add_satellite_season(observations, satellite)
    linked = linked.dropna(subset=["season", "analysis_value"]).merge(
        assignments, left_on="point_notation", right_on="notation", how="inner"
    )
    if linked.empty:
        raise ValueError("No observations overlap the grid and satellite seasons")
    groups = ["cell_id", "season", "determinand_code", "determinand", "unit"]
    outcomes = (
        linked.groupby(groups, dropna=False)
        .agg(
            target_mean=("analysis_value", "mean"),
            target_median=("analysis_value", "median"),
            target_std=("analysis_value", "std"),
            target_min=("analysis_value", "min"),
            target_max=("analysis_value", "max"),
            observation_count=("analysis_value", "size"),
            site_count=("point_notation", "nunique"),
            censored_count=("is_censored", "sum"),
        )
        .reset_index()
    )
    outcomes["censored_fraction"] = outcomes["censored_count"] / outcomes["observation_count"]
    predictors = satellite.drop(columns=["start_date", "end_date"])
    if terrain is not None:
        if terrain["cell_id"].duplicated().any():
            raise ValueError("Terrain table contains duplicate cell IDs")
        predictors = predictors.merge(terrain, on="cell_id", how="left", validate="many_to_one")
    table = outcomes.merge(predictors, on=["cell_id", "season"], how="left", validate="many_to_one")
    if table.duplicated(list(KEY_COLUMNS)).any():
        raise ValueError("Monitoring feature table contains duplicate keys")
    if table["scene_count"].isna().any():
        raise ValueError("Some monitoring outcomes have no satellite predictors")
    return table.sort_values(list(KEY_COLUMNS)).reset_index(drop=True)


def modelling_readiness(table: pd.DataFrame) -> dict[str, object]:
    """Assess whether the linked data can support grouped spatial validation."""
    cells = int(table["cell_id"].nunique())
    determinand_cells = {
        str(code): int(group["cell_id"].nunique())
        for code, group in table.groupby("determinand_code")
    }
    reasons = []
    if cells < MINIMUM_SPATIAL_GROUPS:
        reasons.append(
            f"Only {cells} monitored cells; at least {MINIMUM_SPATIAL_GROUPS} are required"
        )
    sparse = sorted(code for code, count in determinand_cells.items() if count < 10)
    if sparse:
        reasons.append(f"Fewer than 10 spatial cells for determinands: {', '.join(sparse)}")
    return {
        "ready_for_predictive_modelling": not reasons,
        "monitored_cells": cells,
        "minimum_spatial_groups": MINIMUM_SPATIAL_GROUPS,
        "cells_by_determinand": determinand_cells,
        "reasons": reasons,
    }


def save_monitoring_feature_table(
    observations_path: Path,
    sampling_points_path: Path,
    grid_path: Path,
    satellite_path: Path,
    terrain_path: Path,
    output: Path,
) -> Path:
    """Build and save the pilot monitoring feature table with provenance."""
    observations = pd.read_parquet(observations_path)
    sampling_points = gpd.read_file(sampling_points_path)
    grid = gpd.read_file(grid_path)
    satellite = pd.read_parquet(satellite_path)
    terrain = pd.read_parquet(terrain_path)
    table = build_monitoring_feature_table(observations, sampling_points, grid, satellite, terrain)
    output.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(output, index=False)
    provenance = {
        "grain": "cell_id x season x determinand_code",
        "rows": len(table),
        "cells": int(table["cell_id"].nunique()),
        "seasons": sorted(table["season"].unique().tolist()),
        "determinand_codes": sorted(table["determinand_code"].unique().tolist()),
        "temporal_join": "observed_at >= start_date and observed_at < end_date",
        "spatial_join": "sampling point intersects clipped 2 km grid cell",
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "modelling_readiness": modelling_readiness(table),
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output
