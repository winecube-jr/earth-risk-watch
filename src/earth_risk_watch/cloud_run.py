"""Small, controlled Earth Engine executions."""

import hashlib
import json
import math
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
from earth_risk_watch.http_client import get_bytes, open_data_client
from earth_risk_watch.hydrology import rows_from_hydrology_earth_engine
from earth_risk_watch.satellite import (
    INDEX_BANDS,
    build_composite,
    load_seasons,
    load_sentinel_job,
)
from earth_risk_watch.settings import Settings
from earth_risk_watch.upstream import SOURCE_ATTRIBUTES, rows_from_hydroatlas


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
    collection = ee.ImageCollection("COPERNICUS/DEM/GLO30_2024_1").select("DEM")
    elevation = (
        collection.mosaic()
        .setDefaultProjection(collection.first().projection())
        .rename("elevation")
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
        "source": "COPERNICUS/DEM/GLO30_2024_1",
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


def run_hydrology_grid_features(grid_path: Path, output: Path) -> Path:  # pragma: no cover
    """Extract common MERIT Hydro context for every modelling cell."""
    import ee

    settings = Settings()
    if settings.earthengine_project is None:
        raise RuntimeError("EARTHENGINE_PROJECT is not configured")
    ee.Initialize(project=settings.earthengine_project)
    grid_geojson: dict[str, Any] = json.loads(grid_path.read_text(encoding="utf-8"))
    grid = ee.FeatureCollection(grid_geojson)
    source = ee.Image("MERIT/Hydro/v1_0_1")
    image = ee.Image.cat(
        [source.select(band).unmask(0).rename(band) for band in ["upa", "hnd", "wth", "wat"]]
    )
    reducer = (
        ee.Reducer.mean()
        .combine(ee.Reducer.stdDev(), sharedInputs=True)
        .combine(ee.Reducer.max(), sharedInputs=True)
    )
    reduced = image.reduceRegions(
        collection=grid,
        reducer=reducer,
        scale=90,
        tileScale=4,
    ).getInfo()
    frame = rows_from_hydrology_earth_engine(reduced["features"])
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    frame.to_parquet(temporary, index=False)
    os.replace(temporary, output)
    provenance = {
        "created_at": datetime.now(UTC).isoformat(),
        "earth_engine_project": settings.earthengine_project,
        "source": "MERIT/Hydro/v1_0_1",
        "processing_scale_metres": 90,
        "rows": len(frame),
        "cells": int(frame["cell_id"].nunique()),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "masked_pixel_rule": "MERIT masked pixels are filled with zero before aggregation",
        "warning": "Hydrologic context only; not a delineated upstream pollution load.",
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output


def run_hydroatlas_site_features(points_path: Path, output: Path) -> Path:  # pragma: no cover
    """Assign monitoring sites to level-12 basins and retain upstream attributes."""
    import ee

    settings = Settings()
    if settings.earthengine_project is None:
        raise RuntimeError("EARTHENGINE_PROJECT is not configured")
    ee.Initialize(project=settings.earthengine_project)
    points_geojson: dict[str, Any] = json.loads(points_path.read_text(encoding="utf-8"))
    points = ee.FeatureCollection(points_geojson)
    basins = ee.FeatureCollection("WWF/HydroATLAS/v1/Basins/level12")

    def attach_basin(feature: Any) -> Any:
        basin = ee.Feature(basins.filterBounds(feature.geometry()).sort("SUB_AREA").first())
        return ee.Feature(feature).copyProperties(basin, list(SOURCE_ATTRIBUTES))

    joined = points.map(attach_basin).getInfo()
    frame = rows_from_hydroatlas(joined["features"])
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    frame.to_parquet(temporary, index=False)
    os.replace(temporary, output)
    provenance = {
        "created_at": datetime.now(UTC).isoformat(),
        "earth_engine_project": settings.earthengine_project,
        "source": "WWF/HydroATLAS/v1/Basins/level12",
        "rows": len(frame),
        "basins": int(frame["HYBAS_ID"].nunique()),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "assignment": "Point-in-polygon; smallest intersecting level-12 basin",
        "scaling": "Source attributes retained unscaled pending technical-document audit",
        "warning": "Basin outlet attributes approximate, but do not exactly delineate, each site.",
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output


def download_merit_routing_grid(
    geometry_path: Path, output: Path, *, buffer_metres: int = 20_000
) -> Path:  # pragma: no cover
    """Download a bounded 90 m MERIT flow-direction and upstream-area grid."""
    import ee

    settings = Settings()
    if settings.earthengine_project is None:
        raise RuntimeError("EARTHENGINE_PROJECT is not configured")
    ee.Initialize(project=settings.earthengine_project)
    if buffer_metres < 0:
        raise ValueError("buffer_metres must not be negative")
    geometry_geojson: dict[str, Any] = json.loads(geometry_path.read_text(encoding="utf-8"))

    def coordinate_pairs(value: Any) -> list[tuple[float, float]]:
        if (
            isinstance(value, list)
            and len(value) >= 2
            and isinstance(value[0], int | float)
            and isinstance(value[1], int | float)
        ):
            return [(float(value[0]), float(value[1]))]
        if isinstance(value, list):
            return [pair for item in value for pair in coordinate_pairs(item)]
        if isinstance(value, dict):
            return [pair for item in value.values() for pair in coordinate_pairs(item)]
        return []

    pairs = [
        pair
        for feature in geometry_geojson["features"]
        for pair in coordinate_pairs(feature["geometry"])
    ]
    longitudes, latitudes = zip(*pairs, strict=True)
    middle_latitude = (min(latitudes) + max(latitudes)) / 2
    latitude_buffer = buffer_metres / 111_320
    longitude_buffer = buffer_metres / (111_320 * math.cos(math.radians(middle_latitude)))
    geometry = ee.Geometry.BBox(
        min(longitudes) - longitude_buffer,
        min(latitudes) - latitude_buffer,
        max(longitudes) + longitude_buffer,
        max(latitudes) + latitude_buffer,
    )
    import numpy as np
    import rasterio
    from rasterio.io import MemoryFile

    source = ee.Image("MERIT/Hydro/v1_0_1")
    bodies = []
    with open_data_client(timeout_seconds=180) as client:
        for band in ["dir", "upa"]:
            url = source.select(band).getDownloadURL(
                {
                    "name": f"merit-{band}-90m",
                    "region": geometry,
                    "scale": 90,
                    "format": "GEO_TIFF",
                }
            )
            bodies.append(get_bytes(client, url, max_bytes=25_000_000))
    arrays = []
    profile: dict[str, Any] | None = None
    for body in bodies:
        with MemoryFile(body) as memory_file, memory_file.open() as source_band:
            arrays.append(source_band.read(1).astype("float32"))
            if profile is None:
                profile = source_band.profile.copy()
            elif (
                source_band.shape != arrays[0].shape
                or source_band.transform != profile["transform"]
                or source_band.crs != profile["crs"]
            ):
                raise ValueError("MERIT routing bands do not share one pixel grid")
    if profile is None:
        raise ValueError("Earth Engine returned no MERIT routing bands")
    profile.update(count=2, dtype="float32", compress="deflate")
    output.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output, "w", **profile) as target:
        target.write(np.stack(arrays))
        target.set_band_description(1, "dir")
        target.set_band_description(2, "upa")
    provenance = {
        "created_at": datetime.now(UTC).isoformat(),
        "earth_engine_project": settings.earthengine_project,
        "source": "MERIT/Hydro/v1_0_1",
        "bands": ["dir", "upa"],
        "processing_scale_metres": 90,
        "region": "bounding rectangle of supplied geometry",
        "buffer_metres": buffer_metres,
        "source_download_bytes": sum(len(body) for body in bodies),
        "bytes": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "warning": "Watersheds touching the clipped raster boundary are incomplete.",
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output
