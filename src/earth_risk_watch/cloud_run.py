"""Small, controlled Earth Engine executions."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from earth_risk_watch.satellite import INDEX_BANDS, build_composite, load_sentinel_job
from earth_risk_watch.settings import Settings


def run_pilot_summary(geometry_path: Path, output: Path) -> Path:
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
