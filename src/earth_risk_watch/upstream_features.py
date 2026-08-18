"""Validated site-level upstream predictors and monitoring outcomes."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd

from earth_risk_watch.monitoring_features import MINIMUM_SPATIAL_GROUPS, add_satellite_season

SITE_KEY = "point_notation"
SITE_OUTCOME_KEY = (SITE_KEY, "season", "determinand_code")


def _validate_site_table(frame: pd.DataFrame, name: str) -> None:
    if SITE_KEY not in frame:
        raise ValueError(f"{name} is missing {SITE_KEY}")
    if frame[SITE_KEY].isna().any():
        raise ValueError(f"{name} contains a null {SITE_KEY}")
    if frame[SITE_KEY].duplicated().any():
        raise ValueError(f"{name} contains duplicate {SITE_KEY} values")


def build_upstream_feature_table(
    watersheds: gpd.GeoDataFrame,
    land_cover: pd.DataFrame,
    climate: pd.DataFrame,
    storm_overflows: pd.DataFrame,
) -> pd.DataFrame:
    """Combine independently generated upstream layers at one row per site."""
    tables = {
        "watersheds": pd.DataFrame(watersheds.drop(columns="geometry")),
        "land_cover": land_cover,
        "climate": climate,
        "storm_overflows": storm_overflows,
    }
    for name, frame in tables.items():
        _validate_site_table(frame, name)
    expected_sites = set(tables["watersheds"][SITE_KEY])
    for name, frame in tables.items():
        if set(frame[SITE_KEY]) != expected_sites:
            raise ValueError(f"{name} site coverage does not match watersheds")
    land_cover_columns = [
        column
        for column in land_cover
        if column == SITE_KEY
        or column.endswith("_mean")
        or column.endswith("_std")
        or column.endswith("_coverage_fraction")
    ]
    climate_columns = [
        column
        for column in climate
        if column == SITE_KEY
        or column.endswith("_mean")
        or column.endswith("_std")
        or column.endswith("_coverage_fraction")
    ]
    result = tables["watersheds"].copy()
    for frame in [land_cover[land_cover_columns], climate[climate_columns], storm_overflows]:
        result = result.merge(frame, on=SITE_KEY, validate="one_to_one")
    coverage_columns = [column for column in result if column.endswith("_coverage_fraction")]
    if coverage_columns and result[coverage_columns].isna().any().any():
        raise ValueError("Upstream raster coverage contains null values")
    return result.sort_values(SITE_KEY).reset_index(drop=True)


def build_site_upstream_monitoring_table(
    observations: pd.DataFrame,
    satellite_windows: pd.DataFrame,
    upstream: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate monitoring outcomes by site and season, then attach upstream predictors."""
    _validate_site_table(upstream, "upstream")
    linked = add_satellite_season(observations, satellite_windows)
    linked = linked.loc[
        linked[SITE_KEY].isin(upstream[SITE_KEY])
        & linked["season"].notna()
        & linked["analysis_value"].notna()
    ]
    if linked.empty:
        raise ValueError("No observations overlap complete watersheds and seasonal windows")
    groups = [SITE_KEY, "season", "determinand_code", "determinand", "unit"]
    outcomes = (
        linked.groupby(groups, dropna=False)
        .agg(
            target_mean=("analysis_value", "mean"),
            target_median=("analysis_value", "median"),
            target_std=("analysis_value", "std"),
            target_min=("analysis_value", "min"),
            target_max=("analysis_value", "max"),
            observation_count=("analysis_value", "size"),
            censored_count=("is_censored", "sum"),
        )
        .reset_index()
    )
    outcomes["censored_fraction"] = outcomes["censored_count"] / outcomes["observation_count"]
    result = outcomes.merge(upstream, on=SITE_KEY, how="left", validate="many_to_one")
    if result.duplicated(list(SITE_OUTCOME_KEY)).any():
        raise ValueError("Site upstream monitoring table contains duplicate keys")
    return result.sort_values(list(SITE_OUTCOME_KEY)).reset_index(drop=True)


def site_modelling_readiness(table: pd.DataFrame) -> dict[str, object]:
    """Block modelling until enough independent complete-watershed sites exist."""
    sites = int(table[SITE_KEY].nunique())
    determinand_sites = {
        str(code): int(group[SITE_KEY].nunique())
        for code, group in table.groupby("determinand_code")
    }
    reasons = []
    if sites < MINIMUM_SPATIAL_GROUPS:
        reasons.append(
            f"Only {sites} complete-watershed sites; at least {MINIMUM_SPATIAL_GROUPS} are required"
        )
    sparse = sorted(code for code, count in determinand_sites.items() if count < 10)
    if sparse:
        reasons.append(f"Fewer than 10 independent sites for determinands: {', '.join(sparse)}")
    return {
        "ready_for_predictive_modelling": not reasons,
        "complete_watershed_sites": sites,
        "minimum_spatial_groups": MINIMUM_SPATIAL_GROUPS,
        "sites_by_determinand": determinand_sites,
        "reasons": reasons,
    }


def save_upstream_feature_table(
    watersheds_path: Path,
    land_cover_path: Path,
    climate_path: Path,
    storm_overflows_path: Path,
    output: Path,
) -> Path:
    """Save the consolidated site predictor table with input checksums."""
    inputs = [watersheds_path, land_cover_path, climate_path, storm_overflows_path]
    frame = build_upstream_feature_table(
        gpd.read_file(watersheds_path),
        pd.read_parquet(land_cover_path),
        pd.read_parquet(climate_path),
        pd.read_parquet(storm_overflows_path),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    provenance = {
        "created_at": datetime.now(UTC).isoformat(),
        "grain": SITE_KEY,
        "rows": len(frame),
        "columns": len(frame.columns),
        "inputs": {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs},
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "status": "exploratory predictors; not part of the frozen baseline",
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output


def save_site_upstream_monitoring_table(
    observations_path: Path,
    satellite_path: Path,
    upstream_path: Path,
    output: Path,
) -> Path:
    """Save site-season outcomes joined to complete-watershed predictors."""
    frame = build_site_upstream_monitoring_table(
        pd.read_parquet(observations_path),
        pd.read_parquet(satellite_path),
        pd.read_parquet(upstream_path),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    provenance = {
        "created_at": datetime.now(UTC).isoformat(),
        "grain": "point_notation x season x determinand_code",
        "rows": len(frame),
        "sites": int(frame[SITE_KEY].nunique()),
        "seasons": sorted(frame["season"].unique().tolist()),
        "determinand_codes": sorted(frame["determinand_code"].unique().tolist()),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "modelling_readiness": site_modelling_readiness(frame),
        "status": "exploratory; new catchment holdout required before model evaluation",
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output
