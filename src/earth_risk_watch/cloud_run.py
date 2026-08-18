"""Small, controlled Earth Engine executions."""

import hashlib
import json
import os
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from earth_risk_watch.elevation import rows_from_dem_earth_engine
from earth_risk_watch.feature_table import (
    FEATURE_COLUMNS,
    rows_from_earth_engine,
    validate_feature_table,
)
from earth_risk_watch.satellite import (
    INDEX_BANDS,
    build_composite,
    load_seasons,
    load_sentinel_job,
)
from earth_risk_watch.settings import Settings


def run_pilot_summary(geometry_path: Path, output: Path) -> Path:  # pragma: no cover
    """Run a low-volume annual Sentinel summary over the pilot catchment."""
    import ee

    settings = Settings()
    if settings.earthengine_project is None:
        raise RuntimeError("EARTHENGINE_PROJECT is not configured")
    ee.Initialize(project=settings.earthengine_project)
    geojson: dict[str, Any] = json.loads(geometry_path.read_text(encoding="utf-8"))
    geometry = ee.FeatureCollection(geojson).geometry()
    job = load_sentinel_job()
    collection = (
        ee.ImageCollection(job.collection)
        .filterBounds(geometry)
        .filterDate(job.start_date.isoformat(), job.end_date.isoformat())
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", job.maximum_scene_cloud_percent))
    )
    composite = build_composite(ee, geometry, job)
    means = composite.select(list(INDEX_BANDS)).reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=100,
        bestEffort=True,
        maxPixels=10_000_000,
    )
    result = {
        "created_at": datetime.now(UTC).isoformat(),
        "earth_engine_project": settings.earthengine_project,
        "job": job.manifest(),
        "scene_count": collection.size().getInfo(),
        "pilot_index_means": means.getInfo(),
        "warning": "Engineering baseline; not a validated environmental risk result.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return output


def run_seasonal_summary(geometry_path: Path, output: Path) -> Path:  # pragma: no cover
    """Calculate seasonal distributions for core indices at controlled scale."""
    import ee

    settings = Settings()
    if settings.earthengine_project is None:
        raise RuntimeError("EARTHENGINE_PROJECT is not configured")
    ee.Initialize(project=settings.earthengine_project)
    geojson: dict[str, Any] = json.loads(geometry_path.read_text(encoding="utf-8"))
    geometry = ee.FeatureCollection(geojson).geometry()
    baseline = load_sentinel_job()
    reducer = (
        ee.Reducer.mean()
        .combine(ee.Reducer.stdDev(), sharedInputs=True)
        .combine(ee.Reducer.percentile([10, 50, 90]), sharedInputs=True)
    )
    results: dict[str, Any] = {}
    for season in load_seasons():
        job = replace(baseline, start_date=season.start_date, end_date=season.end_date)
        collection = (
            ee.ImageCollection(job.collection)
            .filterBounds(geometry)
            .filterDate(job.start_date.isoformat(), job.end_date.isoformat())
            .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", job.maximum_scene_cloud_percent))
        )
        metrics = (
            build_composite(ee, geometry, job)
            .select(list(INDEX_BANDS))
            .reduceRegion(
                reducer=reducer,
                geometry=geometry,
                scale=100,
                bestEffort=True,
                maxPixels=10_000_000,
            )
        )
        results[season.name] = {
            "start_date": season.start_date.isoformat(),
            "end_date": season.end_date.isoformat(),
            "scene_count": collection.size().getInfo(),
            "metrics": metrics.getInfo(),
        }
    product = {
        "created_at": datetime.now(UTC).isoformat(),
        "earth_engine_project": settings.earthengine_project,
        "processing_scale_metres": 100,
        "seasons": results,
        "warning": "Engineering baseline; seasonal bias and residual cloud require review.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(product, indent=2) + "\n", encoding="utf-8")
    return output


def run_grid_features(grid_path: Path, output: Path) -> Path:  # pragma: no cover
    """Extract seasonal Sentinel features for every configured modelling cell."""
    import ee

    settings = Settings()
    if settings.earthengine_project is None:
        raise RuntimeError("EARTHENGINE_PROJECT is not configured")
    ee.Initialize(project=settings.earthengine_project)
    grid_geojson: dict[str, Any] = json.loads(grid_path.read_text(encoding="utf-8"))
    grid = ee.FeatureCollection(grid_geojson)
    geometry = grid.geometry()
    baseline = load_sentinel_job()
    reducer = ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True)
    rows: list[dict[str, Any]] = []
    for season in load_seasons():
        job = replace(baseline, start_date=season.start_date, end_date=season.end_date)
        collection = (
            ee.ImageCollection(job.collection)
            .filterBounds(geometry)
            .filterDate(job.start_date.isoformat(), job.end_date.isoformat())
            .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", job.maximum_scene_cloud_percent))
        )
        reduced = (
            build_composite(ee, geometry, job)
            .select(list(INDEX_BANDS))
            .reduceRegions(
                collection=grid,
                reducer=reducer,
                scale=100,
                tileScale=4,
            )
            .getInfo()
        )
        rows.extend(
            rows_from_earth_engine(
                reduced["features"],
                season=season.name,
                start_date=season.start_date.isoformat(),
                end_date=season.end_date.isoformat(),
                scene_count=collection.size().getInfo(),
            )
        )
    frame = pd.DataFrame(rows).reindex(columns=FEATURE_COLUMNS)
    validate_feature_table(frame)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    frame.to_parquet(temporary, index=False)
    os.replace(temporary, output)
    provenance = {
        "created_at": datetime.now(UTC).isoformat(),
        "earth_engine_project": settings.earthengine_project,
        "rows": len(frame),
        "cells": int(frame["cell_id"].nunique()),
        "seasons": sorted(frame["season"].unique().tolist()),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "warning": "Model-ready predictors only; no validated risk outcome is included.",
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output


def run_dem_grid_features(grid_path: Path, output: Path) -> Path:  # pragma: no cover
    """Extract common 30 m Copernicus DEM features for every modelling cell."""
    import ee

    settings = Settings()
    if settings.earthengine_project is None:
        raise RuntimeError("EARTHENGINE_PROJECT is not configured")
    ee.Initialize(project=settings.earthengine_project)
    grid_geojson: dict[str, Any] = json.loads(grid_path.read_text(encoding="utf-8"))
    grid = ee.FeatureCollection(grid_geojson)
    elevation = (
        ee.ImageCollection("COPERNICUS/DEM/GLO30").select("DEM").mosaic().rename("elevation")
    )
    image = elevation.addBands(ee.Terrain.slope(elevation).rename("slope"))
    reducer = (
        ee.Reducer.mean()
        .combine(ee.Reducer.stdDev(), sharedInputs=True)
        .combine(ee.Reducer.minMax(), sharedInputs=True)
    )
    reduced = image.reduceRegions(
        collection=grid,
        reducer=reducer,
        scale=30,
        tileScale=4,
    ).getInfo()
    frame = rows_from_dem_earth_engine(reduced["features"])
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    frame.to_parquet(temporary, index=False)
    os.replace(temporary, output)
    provenance = {
        "created_at": datetime.now(UTC).isoformat(),
        "earth_engine_project": settings.earthengine_project,
        "source": "COPERNICUS/DEM/GLO30",
        "processing_scale_metres": 30,
        "rows": len(frame),
        "cells": int(frame["cell_id"].nunique()),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "role": "Common-coverage terrain baseline; LiDAR remains supplementary.",
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output
