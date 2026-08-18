"""Transparent environmental pressure screening, distinct from prediction."""

import hashlib
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

COMPONENT_COLUMNS = ("sediment_pressure", "runoff_susceptibility", "condition_stress")


def percentile_score(series: pd.Series, *, reverse: bool = False) -> pd.Series:
    """Convert a metric to a stable 0-100 relative score within the pilot."""
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.isna().any():
        raise ValueError("Screening metrics cannot contain missing values")
    if numeric.nunique() == 1:
        return pd.Series(50.0, index=series.index)
    scores = numeric.rank(method="average", pct=True) * 100
    return 100 - scores if reverse else scores


def satellite_screen_metrics(satellite: pd.DataFrame) -> pd.DataFrame:
    """Reduce seasonal satellite features to interpretable annual signals."""
    required = {"cell_id", "season", "BSI_mean", "NDMI_mean", "MNDWI_mean", "NDVI_mean"}
    missing = required.difference(satellite.columns)
    if missing:
        raise ValueError(f"Missing satellite columns: {', '.join(sorted(missing))}")
    return (
        satellite.groupby("cell_id")
        .agg(
            bare_soil_signal=("BSI_mean", "max"),
            minimum_moisture=("NDMI_mean", "min"),
            maximum_wetness=("MNDWI_mean", "max"),
            minimum_vegetation=("NDVI_mean", "min"),
            satellite_seasons=("season", "nunique"),
            satellite_scenes=("scene_count", "sum"),
        )
        .reset_index()
    )


def monitoring_evidence(
    grid: gpd.GeoDataFrame,
    sampling_points: gpd.GeoDataFrame,
    observations: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate distance from each cell centroid to a site with observations."""
    active_notations = observations["point_notation"].dropna().unique()
    sites = sampling_points.loc[sampling_points["notation"].isin(active_notations)]
    if sites.empty:
        raise ValueError("No sampling points match the observation table")
    projected_grid = grid.to_crs("EPSG:27700")
    site_geometry = sites.to_crs("EPSG:27700").geometry
    distances = projected_grid.geometry.centroid.apply(
        lambda centroid: float(site_geometry.distance(centroid).min() / 1_000)
    )
    containing = gpd.sjoin(
        projected_grid[["cell_id", "geometry"]],
        sites.to_crs(projected_grid.crs)[["geometry"]],
        predicate="intersects",
        how="left",
    )
    monitored_cells = set(containing.loc[containing["index_right"].notna(), "cell_id"])
    return pd.DataFrame(
        {
            "cell_id": projected_grid["cell_id"],
            "monitoring_distance_km": distances,
            "has_monitoring_site": projected_grid["cell_id"].isin(monitored_cells),
        }
    )


def add_weight_sensitivity(
    frame: pd.DataFrame, *, simulations: int = 1_000, seed: int = 42
) -> pd.DataFrame:
    """Quantify score stability under random non-negative component weights."""
    if simulations < 100:
        raise ValueError("At least 100 weight simulations are required")
    components = frame[list(COMPONENT_COLUMNS)].to_numpy(dtype=float)
    weights = np.random.default_rng(seed).dirichlet(np.ones(len(COMPONENT_COLUMNS)), simulations)
    scores = components @ weights.T
    thresholds = np.percentile(scores, 80, axis=0)
    result = frame.copy()
    result["weight_sensitivity_mean"] = np.mean(scores, axis=1)
    result["weight_sensitivity_std"] = np.std(scores, axis=1)
    result["weight_sensitivity_p10"] = np.percentile(scores, 10, axis=1)
    result["weight_sensitivity_p90"] = np.percentile(scores, 90, axis=1)
    result["top_quintile_frequency"] = np.mean(scores >= thresholds, axis=1)
    return result


def build_risk_screen(
    grid: gpd.GeoDataFrame,
    satellite: pd.DataFrame,
    terrain: pd.DataFrame,
    sampling_points: gpd.GeoDataFrame,
    observations: pd.DataFrame,
) -> gpd.GeoDataFrame:
    """Build a relative pressure screen with explicit evidence context."""
    metrics = satellite_screen_metrics(satellite)
    if terrain["cell_id"].duplicated().any():
        raise ValueError("Terrain table contains duplicate cell IDs")
    frame = grid.merge(metrics, on="cell_id", validate="one_to_one").merge(
        terrain, on="cell_id", validate="one_to_one"
    )
    frame["bare_soil_score"] = percentile_score(frame["bare_soil_signal"])
    frame["slope_score"] = percentile_score(frame["slope_p90_degrees"])
    frame["relief_score"] = percentile_score(frame["relief_m"])
    frame["wetness_score"] = percentile_score(frame["maximum_wetness"])
    frame["moisture_stress_score"] = percentile_score(frame["minimum_moisture"], reverse=True)
    frame["vegetation_stress_score"] = percentile_score(frame["minimum_vegetation"], reverse=True)
    frame["sediment_pressure"] = frame[["bare_soil_score", "slope_score", "relief_score"]].mean(
        axis=1
    )
    frame["runoff_susceptibility"] = frame[["slope_score", "relief_score", "wetness_score"]].mean(
        axis=1
    )
    frame["condition_stress"] = frame[["moisture_stress_score", "vegetation_stress_score"]].mean(
        axis=1
    )
    frame["screening_score"] = frame[
        ["sediment_pressure", "runoff_susceptibility", "condition_stress"]
    ].mean(axis=1)
    frame["screening_band"] = pd.cut(
        frame["screening_score"],
        bins=[0, 20, 40, 60, 80, 100],
        labels=["very low", "low", "moderate", "high", "very high"],
        include_lowest=True,
    ).astype(str)
    frame = add_weight_sensitivity(frame)
    evidence = monitoring_evidence(grid, sampling_points, observations)
    frame = frame.merge(evidence, on="cell_id", validate="one_to_one")
    frame["evidence_proximity"] = pd.cut(
        frame["monitoring_distance_km"],
        bins=[-np.inf, 2, 5, np.inf],
        labels=["near", "intermediate", "distant"],
    ).astype(str)
    if len(frame) != len(grid) or frame["cell_id"].duplicated().any():
        raise ValueError("Risk screen must contain exactly one row per grid cell")
    return gpd.GeoDataFrame(frame, geometry="geometry", crs=grid.crs)


def save_risk_screen(
    grid_path: Path,
    satellite_path: Path,
    terrain_path: Path,
    sampling_points_path: Path,
    observations_path: Path,
    output: Path,
) -> Path:
    """Save the pilot screen as GeoJSON with an evidence/provenance sidecar."""
    screen = build_risk_screen(
        gpd.read_file(grid_path),
        pd.read_parquet(satellite_path),
        pd.read_parquet(terrain_path),
        gpd.read_file(sampling_points_path),
        pd.read_parquet(observations_path),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    screen.to_file(output, driver="GeoJSON")
    provenance = {
        "product_type": "relative exploratory screening index; not a validated prediction",
        "rows": len(screen),
        "score_range": [
            float(screen["screening_score"].min()),
            float(screen["screening_score"].max()),
        ],
        "weights": {
            "overall": {
                "sediment_pressure": "1/3",
                "runoff_susceptibility": "1/3",
                "condition_stress": "1/3",
            },
            "components": "equal weights among listed source scores",
        },
        "normalization": "within-pilot percentile ranks; scores are not nationally comparable",
        "weight_sensitivity": {
            "simulations": 1000,
            "seed": 42,
            "weight_distribution": "Dirichlet(1,1,1)",
        },
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output
