"""Google Earth Engine Sentinel-2 feature construction."""

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from earth_risk_watch.settings import repository_root

INDEX_BANDS = ("NDVI", "NDMI", "MNDWI", "BSI")
EXCLUDED_SCL_CLASSES = (3, 8, 9, 10, 11)


@dataclass(frozen=True)
class SentinelJob:
    """Validated, serializable Sentinel-2 processing request."""

    collection: str
    start_date: date
    end_date: date
    maximum_scene_cloud_percent: int
    output_scale_metres: int
    composite: str

    def __post_init__(self) -> None:
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        if not 0 <= self.maximum_scene_cloud_percent <= 100:
            raise ValueError("maximum_scene_cloud_percent must be between 0 and 100")
        if self.output_scale_metres <= 0:
            raise ValueError("output_scale_metres must be positive")
        if self.composite != "median":
            raise ValueError("Only the audited median baseline is currently supported")

    def manifest(self) -> dict[str, Any]:
        """Return a JSON/YAML-friendly processing description."""
        values = asdict(self)
        values["start_date"] = self.start_date.isoformat()
        values["end_date"] = self.end_date.isoformat()
        values["index_bands"] = list(INDEX_BANDS)
        values["excluded_scl_classes"] = list(EXCLUDED_SCL_CLASSES)
        return values


def load_sentinel_job(path: Path | None = None) -> SentinelJob:
    """Load the baseline Sentinel request from project configuration."""
    config_path = path or repository_root() / "config" / "sentinel.yaml"
    with config_path.open(encoding="utf-8") as stream:
        raw = yaml.safe_load(stream)["sentinel_2"]
    return SentinelJob(
        collection=raw["collection"],
        start_date=date.fromisoformat(raw["start_date"]),
        end_date=date.fromisoformat(raw["end_date"]),
        maximum_scene_cloud_percent=raw["maximum_scene_cloud_percent"],
        output_scale_metres=raw["output_scale_metres"],
        composite=raw["composite"],
    )


def mask_s2_scl(image: Any) -> Any:
    """Mask cloud shadow, cloud, cirrus, and snow using Sentinel-2 SCL."""
    scl = image.select("SCL")
    mask = scl.neq(EXCLUDED_SCL_CLASSES[0])
    for value in EXCLUDED_SCL_CLASSES[1:]:
        mask = mask.And(scl.neq(value))
    return image.updateMask(mask).divide(10_000).copyProperties(image, ["system:time_start"])


def add_indices(image: Any) -> Any:
    """Add interpretable vegetation, moisture, water, and bare-soil indices."""
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
    ndmi = image.normalizedDifference(["B8", "B11"]).rename("NDMI")
    mndwi = image.normalizedDifference(["B3", "B11"]).rename("MNDWI")
    bsi = image.expression(
        "((swir + red) - (nir + blue)) / ((swir + red) + (nir + blue))",
        {
            "swir": image.select("B11"),
            "red": image.select("B4"),
            "nir": image.select("B8"),
            "blue": image.select("B2"),
        },
    ).rename("BSI")
    return image.addBands([ndvi, ndmi, mndwi, bsi])


def build_composite(ee: Any, geometry: Any, job: SentinelJob) -> Any:
    """Build a lazy Earth Engine annual median for a bounded geometry."""
    collection = (
        ee.ImageCollection(job.collection)
        .filterBounds(geometry)
        .filterDate(job.start_date.isoformat(), job.end_date.isoformat())
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", job.maximum_scene_cloud_percent))
        .map(mask_s2_scl)
        .map(add_indices)
    )
    return collection.median().clip(geometry)
