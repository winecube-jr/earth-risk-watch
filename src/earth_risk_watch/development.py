"""Fail-closed construction of cross-catchment upstream development data."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

KEY_COLUMNS = ("area_id", "point_notation", "season", "determinand_code")
PREREGISTERED_PREDICTORS = (
    "log_upstream_area_km2",
    "tree_fraction_mean",
    "grass_fraction_mean",
    "cropland_fraction_mean",
    "built_up_fraction_mean",
    "water_fraction_mean",
    "wetland_fraction_mean",
    "precipitation_2024_mm_mean",
    "maximum_daily_precipitation_2024_mm_mean",
    "soil_moisture_layer_1_mean_2024_mean",
    "upstream_overflow_density_per_100_km2",
    "upstream_spill_density_per_100_km2",
    "upstream_spill_hours_per_100_km2",
)
DERIVED_PREDICTORS = (
    "log_upstream_area_km2",
    "upstream_overflow_density_per_100_km2",
    "upstream_spill_density_per_100_km2",
    "upstream_spill_hours_per_100_km2",
)


def derive_upstream_predictors(source: pd.DataFrame) -> pd.DataFrame:
    """Derive the identical area-normalized predictors for any partition."""
    frame = source.copy()
    required = {
        "outlet_upstream_area_km2",
        "upstream_overflow_count",
        "upstream_spill_count_2024",
        "upstream_spill_duration_hours_2024",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Cannot derive upstream predictors; missing columns: {sorted(missing)}")
    area = frame["outlet_upstream_area_km2"]
    if area.isna().any() or (area <= 0).any():
        raise ValueError("Cannot derive upstream predictors from invalid upstream areas")
    frame["log_upstream_area_km2"] = np.log1p(area)
    frame["upstream_overflow_density_per_100_km2"] = frame["upstream_overflow_count"] / area * 100
    frame["upstream_spill_density_per_100_km2"] = frame["upstream_spill_count_2024"] / area * 100
    frame["upstream_spill_hours_per_100_km2"] = (
        frame["upstream_spill_duration_hours_2024"] / area * 100
    )
    return frame


def build_upstream_development_table(area_tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Combine disjoint, topology-validated catchments and derive scale-safe pressures."""
    if len(area_tables) < 2:
        raise ValueError("At least two development catchments are required")
    expected_columns: list[str] | None = None
    seen_sites: set[str] = set()
    frames = []
    for area_id, source in sorted(area_tables.items()):
        frame = source.copy()
        if expected_columns is None:
            expected_columns = list(frame.columns)
        elif list(frame.columns) != expected_columns:
            raise ValueError(f"Feature schema mismatch for {area_id}")
        required = {
            "point_notation",
            "season",
            "determinand_code",
            "outlet_upstream_area_km2",
            "topology_consistent",
            "touches_raster_boundary",
            "target_mean",
        }
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{area_id} is missing corrected watershed fields: {sorted(missing)}")
        if not frame["topology_consistent"].all():
            raise ValueError(f"{area_id} contains topology-inconsistent watersheds")
        if frame["touches_raster_boundary"].any():
            raise ValueError(f"{area_id} contains boundary-truncated watersheds")
        sites = set(frame["point_notation"].astype(str))
        overlap = seen_sites.intersection(sites)
        if overlap:
            raise ValueError(f"Monitoring sites occur in multiple catchments: {sorted(overlap)}")
        seen_sites.update(sites)
        coverage = [column for column in frame if column.endswith("_coverage_fraction")]
        if coverage and ((frame[coverage] <= 0).any().any() or frame[coverage].isna().any().any()):
            raise ValueError(f"{area_id} contains missing upstream raster coverage")
        area = frame["outlet_upstream_area_km2"]
        if area.isna().any() or (area <= 0).any():
            raise ValueError(f"{area_id} contains invalid upstream areas")
        frame = derive_upstream_predictors(frame)
        missing_predictors = set(PREREGISTERED_PREDICTORS).difference(frame.columns)
        if missing_predictors:
            raise ValueError(f"{area_id} is missing predictors: {sorted(missing_predictors)}")
        frame.insert(0, "area_id", area_id)
        frames.append(frame)
    result = pd.concat(frames, ignore_index=True)
    if result.duplicated(list(KEY_COLUMNS)).any():
        raise ValueError("Development table contains duplicate outcome keys")
    return result.sort_values(list(KEY_COLUMNS)).reset_index(drop=True)


def development_diagnostics(frame: pd.DataFrame) -> dict[str, object]:
    """Summarize independent support and preregistered predictor completeness."""
    return {
        "rows": len(frame),
        "sites": int(frame["point_notation"].nunique()),
        "catchments": int(frame["area_id"].nunique()),
        "sites_by_catchment": {
            str(area): int(group["point_notation"].nunique())
            for area, group in frame.groupby("area_id")
        },
        "sites_by_determinand": {
            str(code): int(group["point_notation"].nunique())
            for code, group in frame.groupby("determinand_code")
        },
        "predictors": list(PREREGISTERED_PREDICTORS),
        "predictor_null_counts": {
            column: int(frame[column].isna().sum()) for column in PREREGISTERED_PREDICTORS
        },
        "target_support_by_determinand": {
            str(code): {
                "rows": len(group),
                "sites": int(group["point_notation"].nunique()),
                "minimum": float(group["target_mean"].min()),
                "median": float(group["target_mean"].median()),
                "maximum": float(group["target_mean"].max()),
                "skew": float(group["target_mean"].skew()),
                "zero_rows": int((group["target_mean"] == 0).sum()),
            }
            for code, group in frame.groupby("determinand_code")
        },
        "topology_consistent": bool(frame["topology_consistent"].all()),
        "delineated_to_upstream_pixel_ratio": {
            "minimum": float(frame["delineated_to_upstream_pixel_ratio"].min()),
            "maximum": float(frame["delineated_to_upstream_pixel_ratio"].max()),
        },
        "boundary_truncated_rows": int(frame["touches_raster_boundary"].sum()),
        "duplicate_outcome_keys": int(frame.duplicated(list(KEY_COLUMNS)).sum()),
    }


def save_upstream_development_table(
    area_paths: dict[str, Path], output: Path, diagnostics_output: Path
) -> Path:
    """Save validated development data, diagnostics and checksum provenance."""
    frame = build_upstream_development_table(
        {area_id: pd.read_parquet(path) for area_id, path in area_paths.items()}
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    diagnostics_output.parent.mkdir(parents=True, exist_ok=True)
    diagnostics_output.write_text(
        json.dumps(development_diagnostics(frame), indent=2) + "\n", encoding="utf-8"
    )
    provenance = {
        "created_at": datetime.now(UTC).isoformat(),
        "grain": "area_id x point_notation x season x determinand_code",
        "inputs": {
            area_id: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for area_id, path in sorted(area_paths.items())
        },
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "preregistered_predictors": list(PREREGISTERED_PREDICTORS),
        "status": "development only; no external holdout rows",
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output
