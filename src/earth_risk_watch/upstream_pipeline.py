"""End-to-end orchestration for configured study-area upstream features."""

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

from earth_risk_watch.areas import load_study_areas
from earth_risk_watch.cloud_run import (
    download_era5_land_rainfall_grid,
    download_merit_routing_grid,
    download_worldcover_pressure_grid,
)
from earth_risk_watch.extract.ea_catchments import save_study_area
from earth_risk_watch.extract.water_quality import save_pilot_observations, save_sampling_points
from earth_risk_watch.satellite import load_seasons
from earth_risk_watch.upstream_features import (
    save_site_upstream_monitoring_table,
    save_upstream_feature_table,
    site_modelling_readiness,
)
from earth_risk_watch.wastewater import extract_edm_2024, save_upstream_edm_features
from earth_risk_watch.watershed import (
    save_site_delineation_diagnostics,
    save_site_watershed_polygons,
    save_watershed_raster_features,
)


def run_upstream_area_pipeline(
    area_id: str,
    root: Path = Path("data"),
    *,
    buffer_metres: int = 20_000,
    force: bool = False,
) -> Path:  # pragma: no cover
    """Build all upstream features, resuming completed expensive stages by default."""
    area = load_study_areas().by_id(area_id)
    raw_study = root / "raw" / "study-areas"
    feature_study = root / "features" / "study-areas"
    product_study = root / "products" / "study-areas"
    geometry, _ = save_study_area(area_id, raw_study)
    points = raw_study / f"{area_id}-sampling-points.geojson"
    observations = feature_study / f"{area_id}-observations-2024.parquet"
    save_sampling_points(geometry, points)
    save_pilot_observations(points, observations)

    routing = root / "raw" / "hydrology" / f"{area_id}-merit-routing-90m.tif"
    land_cover = root / "raw" / "land-cover" / f"{area_id}-worldcover-100m.tif"
    climate = root / "raw" / "climate" / f"{area_id}-era5-land-2024-1km.tif"
    if force or not routing.exists():
        download_merit_routing_grid(geometry, routing, buffer_metres=buffer_metres)
    if force or not land_cover.exists():
        download_worldcover_pressure_grid(geometry, land_cover, buffer_metres=buffer_metres)
    if force or not climate.exists():
        download_era5_land_rainfall_grid(geometry, climate, buffer_metres=buffer_metres)

    diagnostics = product_study / f"{area_id}-watershed-diagnostics.parquet"
    watersheds = feature_study / f"{area_id}-site-watersheds.geojson"
    save_site_delineation_diagnostics(routing, points, observations, diagnostics)
    save_site_watershed_polygons(routing, points, observations, watersheds)

    land_cover_features = feature_study / f"{area_id}-worldcover.parquet"
    climate_features = feature_study / f"{area_id}-era5-land-2024.parquet"
    save_watershed_raster_features(watersheds, land_cover, land_cover_features)
    save_watershed_raster_features(watersheds, climate, climate_features)

    edm = root / "staged" / "wastewater" / "edm-2024.parquet"
    if not edm.exists():
        extract_edm_2024(edm)
    edm_features = feature_study / f"{area_id}-edm-2024.parquet"
    save_upstream_edm_features(watersheds, edm, edm_features)

    upstream = feature_study / f"{area_id}-upstream.parquet"
    save_upstream_feature_table(
        watersheds, land_cover_features, climate_features, edm_features, upstream
    )
    seasons = pd.DataFrame(
        [
            {
                "season": season.name,
                "start_date": season.start_date.isoformat(),
                "end_date": season.end_date.isoformat(),
            }
            for season in load_seasons()
        ]
    )
    seasons_path = root / "staged" / "study-areas" / f"{area_id}-season-windows.parquet"
    seasons_path.parent.mkdir(parents=True, exist_ok=True)
    seasons.to_parquet(seasons_path, index=False)
    monitoring = feature_study / f"{area_id}-site-upstream-monitoring.parquet"
    save_site_upstream_monitoring_table(observations, seasons_path, upstream, monitoring)

    diagnostic_frame = pd.read_parquet(diagnostics)
    watershed_frame = gpd.read_file(watersheds)
    monitoring_frame = pd.read_parquet(monitoring)
    summary = {
        "area_id": area.id,
        "area_name": area.name,
        "configured_role": area.role,
        "active_monitoring_sites": len(diagnostic_frame),
        "complete_watersheds": len(watershed_frame),
        "truncated_watersheds": int(diagnostic_frame["touches_raster_boundary"].sum()),
        "monitoring_rows": len(monitoring_frame),
        "modelling_readiness": site_modelling_readiness(monitoring_frame),
        "warning": "Engineering output; external-validation roles must not inform model tuning.",
    }
    summary_path = product_study / f"{area_id}-upstream-summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary_path
