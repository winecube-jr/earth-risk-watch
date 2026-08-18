"""Command-line interface for repeatable local and cloud execution."""

import json
from pathlib import Path
from typing import Annotated

import typer

from earth_risk_watch.catalogue import load_catalogue
from earth_risk_watch.cloud_run import (
    download_merit_routing_grid,
    run_dem_grid_features,
    run_grid_features,
    run_hydroatlas_site_features,
    run_hydrology_grid_features,
    run_pilot_summary,
    run_seasonal_summary,
)
from earth_risk_watch.demo import build_demo_manifest
from earth_risk_watch.diagnostics import save_evaluation_diagnostics
from earth_risk_watch.evidence import save_evidence_pack
from earth_risk_watch.extract.ea_catchments import (
    save_pilot_classifications,
    save_pilot_geometry,
    save_study_area,
)
from earth_risk_watch.extract.water_quality import save_pilot_observations, save_sampling_points
from earth_risk_watch.grid import build_clipped_grid
from earth_risk_watch.monitoring_features import save_monitoring_feature_table
from earth_risk_watch.outcomes import build_ecological_outcomes
from earth_risk_watch.publish import build_risk_map
from earth_risk_watch.readiness import checks_as_dicts
from earth_risk_watch.risk_screen import save_risk_screen
from earth_risk_watch.satellite import load_sentinel_job
from earth_risk_watch.terrain import save_lidar_subset, save_terrain_features
from earth_risk_watch.validation import parse_partition_paths, save_geographic_partitions
from earth_risk_watch.watershed import save_site_delineation_diagnostics

app = typer.Typer(no_args_is_help=True, help="Earth Risk Watch pipeline tools.")
catalogue_app = typer.Typer(no_args_is_help=True, help="Inspect configured data sources.")
app.add_typer(catalogue_app, name="catalogue")


@app.command()
def doctor() -> None:
    """Report local and cloud configuration readiness."""
    checks = checks_as_dicts()
    typer.echo(json.dumps(checks, indent=2))
    if any(not bool(check["ok"]) for check in checks):
        raise typer.Exit(code=1)


@catalogue_app.command("list")
def catalogue_list() -> None:
    """List all registered data sources."""
    for source in load_catalogue().sources:
        typer.echo(f"{source.id}\t{source.provider}\t{source.title}")


@catalogue_app.command("show")
def catalogue_show(source_id: str) -> None:
    """Show one source as JSON."""
    source = load_catalogue().by_id(source_id)
    typer.echo(source.model_dump_json(indent=2))


@app.command()
def demo(output: Path = Path("data/products/demo")) -> None:
    """Run the credential-free foundation demonstration."""
    target = build_demo_manifest(output)
    typer.echo(f"Created {target}")


@app.command("extract-ea-pilot")
def extract_ea_pilot(
    output: Path = Path("data/raw/ea-catchments/pilot-classifications.csv"),
) -> None:
    """Download provisional pilot classifications with provenance."""
    target = save_pilot_classifications(output)
    typer.echo(f"Created {target}")


@app.command("sentinel-plan")
def sentinel_plan() -> None:
    """Print the configured Sentinel-2 request without running cloud compute."""
    typer.echo(json.dumps(load_sentinel_job().manifest(), indent=2))


@app.command("extract-ea-geometry")
def extract_ea_geometry(
    output: Path = Path("data/raw/ea-catchments/pilot.geojson"),
) -> None:
    """Download the official provisional pilot boundary."""
    target = save_pilot_geometry(output)
    typer.echo(f"Created {target}")


@app.command("extract-study-area")
def extract_study_area(
    area_id: str,
    output: Path = Path("data/raw/study-areas"),
) -> None:
    """Download geometry and classifications for a configured study area."""
    geometry, classifications = save_study_area(area_id, output)
    typer.echo(f"Created {geometry}")
    typer.echo(f"Created {classifications}")


@app.command("sentinel-summary")
def sentinel_summary(
    geometry: Path = Path("data/raw/ea-catchments/pilot.geojson"),
    output: Path = Path("data/products/sentinel/pilot-summary.json"),
) -> None:
    """Run the controlled annual Sentinel pilot summary in Earth Engine."""
    target = run_pilot_summary(geometry, output)
    typer.echo(f"Created {target}")


@app.command("sentinel-seasonal")
def sentinel_seasonal(
    geometry: Path = Path("data/raw/ea-catchments/pilot.geojson"),
    output: Path = Path("data/products/sentinel/pilot-seasonal.json"),
) -> None:
    """Run controlled seasonal Sentinel summaries in Earth Engine."""
    target = run_seasonal_summary(geometry, output)
    typer.echo(f"Created {target}")


@app.command("build-grid")
def build_grid(
    geometry: Path = Path("data/raw/ea-catchments/pilot.geojson"),
    output: Path = Path("data/staged/grid/pilot-2km.geojson"),
    cell_size_metres: int = 2_000,
) -> None:
    """Create clipped British National Grid modelling units."""
    target = build_clipped_grid(geometry, output, cell_size_metres=cell_size_metres)
    typer.echo(f"Created {target}")


@app.command("sentinel-grid-features")
def sentinel_grid_features(
    grid: Path = Path("data/staged/grid/pilot-2km.geojson"),
    output: Path = Path("data/features/sentinel/pilot-seasonal.parquet"),
) -> None:
    """Build the model-ready seasonal Sentinel feature table."""
    target = run_grid_features(grid, output)
    typer.echo(f"Created {target}")


@app.command("dem-grid-features")
def dem_grid_features(
    grid: Path = Path("data/staged/grid/pilot-2km.geojson"),
    output: Path = Path("data/features/terrain/pilot-dem-30m.parquet"),
) -> None:
    """Build common-coverage Copernicus DEM features in Earth Engine."""
    target = run_dem_grid_features(grid, output)
    typer.echo(f"Created {target}")


@app.command("hydrology-grid-features")
def hydrology_grid_features(
    grid: Path = Path("data/staged/grid/pilot-2km.geojson"),
    output: Path = Path("data/features/hydrology/pilot-merit-90m.parquet"),
) -> None:
    """Build common MERIT Hydro context features in Earth Engine."""
    target = run_hydrology_grid_features(grid, output)
    typer.echo(f"Created {target}")


@app.command("hydroatlas-site-features")
def hydroatlas_site_features(
    points: Path = Path("data/raw/water-quality/pilot-sampling-points.geojson"),
    output: Path = Path("data/features/upstream/pilot-hydroatlas.parquet"),
) -> None:
    """Assign monitoring sites to HydroATLAS basins and upstream attributes."""
    target = run_hydroatlas_site_features(points, output)
    typer.echo(f"Created {target}")


@app.command("extract-merit-routing-grid")
def extract_merit_routing_grid(
    geometry: Path = Path("data/raw/ea-catchments/pilot.geojson"),
    output: Path = Path("data/raw/hydrology/pilot-merit-routing-90m.tif"),
    buffer_metres: int = typer.Option(20_000, min=0),
) -> None:
    """Download bounded MERIT D8 direction and upstream-area bands."""
    target = download_merit_routing_grid(geometry, output, buffer_metres=buffer_metres)
    typer.echo(f"Created {target}")


@app.command("diagnose-site-watersheds")
def diagnose_site_watersheds(
    routing: Path,
    points: Path,
    observations: Path,
    output: Path = Path("data/products/hydrology/site-watershed-diagnostics.parquet"),
    snap_radius_pixels: int = typer.Option(5, min=0),
) -> None:
    """Trace active-site watersheds and report snap and boundary diagnostics."""
    target = save_site_delineation_diagnostics(
        routing,
        points,
        observations,
        output,
        snap_radius_pixels=snap_radius_pixels,
    )
    typer.echo(f"Created {target}")


@app.command("build-ecological-outcomes")
def build_outcomes(
    source: Path = Path("data/raw/ea-catchments/pilot-classifications.csv"),
    output: Path = Path("data/features/outcomes/pilot-ecological.parquet"),
) -> None:
    """Normalize independent EA ecological-status outcomes."""
    target = build_ecological_outcomes(source, output)
    typer.echo(f"Created {target}")


@app.command("extract-water-sampling-points")
def extract_water_sampling_points(
    geometry: Path = Path("data/raw/ea-catchments/pilot.geojson"),
    output: Path = Path("data/raw/water-quality/pilot-sampling-points.geojson"),
) -> None:
    """Download Water Quality Explorer sampling points inside the pilot."""
    target = save_sampling_points(geometry, output)
    typer.echo(f"Created {target}")


@app.command("extract-water-observations")
def extract_water_observations(
    sampling_points: Path = Path("data/raw/water-quality/pilot-sampling-points.geojson"),
    output: Path = Path("data/features/water-quality/pilot-2024.parquet"),
) -> None:
    """Download 2024 core observations from open river sites in the pilot."""
    target = save_pilot_observations(sampling_points, output)
    typer.echo(f"Created {target}")


@app.command("build-monitoring-features")
def build_monitoring_features(
    observations: Path = Path("data/features/water-quality/pilot-2024.parquet"),
    sampling_points: Path = Path("data/raw/water-quality/pilot-sampling-points.geojson"),
    grid: Path = Path("data/staged/grid/pilot-2km.geojson"),
    satellite: Path = Path("data/features/sentinel/pilot-seasonal.parquet"),
    terrain: Path = Path("data/features/terrain/pilot-2km.parquet"),
    output: Path = Path("data/features/monitoring/pilot-seasonal.parquet"),
) -> None:
    """Link seasonal water observations to same-cell satellite predictors."""
    target = save_monitoring_feature_table(
        observations, sampling_points, grid, satellite, terrain, output
    )
    typer.echo(f"Created {target}")


@app.command("extract-lidar-terrain")
def extract_lidar_terrain(
    geometry: Path = Path("data/raw/ea-catchments/pilot.geojson"),
    output: Path = Path("data/raw/lidar/pilot-dtm-10m.tif"),
    resolution_metres: int = typer.Option(10, min=1),
) -> None:
    """Download a bounded, server-resampled DTM from the official LiDAR WCS."""
    target = save_lidar_subset(geometry, output, output_resolution_metres=resolution_metres)
    typer.echo(f"Created {target}")


@app.command("build-terrain-features")
def build_terrain_feature_command(
    dtm: Path = Path("data/raw/lidar/pilot-dtm-10m.tif"),
    grid: Path = Path("data/staged/grid/pilot-2km.geojson"),
    output: Path = Path("data/features/terrain/pilot-2km.parquet"),
) -> None:
    """Build elevation, relief, and slope predictors for pilot grid cells."""
    target = save_terrain_features(dtm, grid, output)
    typer.echo(f"Created {target}")


@app.command("build-risk-screen")
def build_risk_screen_command(
    grid: Path = Path("data/staged/grid/pilot-2km.geojson"),
    satellite: Path = Path("data/features/sentinel/pilot-seasonal.parquet"),
    terrain: Path = Path("data/features/terrain/pilot-2km.parquet"),
    sampling_points: Path = Path("data/raw/water-quality/pilot-sampling-points.geojson"),
    observations: Path = Path("data/features/water-quality/pilot-2024.parquet"),
    output: Path = Path("data/products/risk/pilot-screen.geojson"),
) -> None:
    """Build an explainable relative pressure screen for the pilot grid."""
    target = save_risk_screen(grid, satellite, terrain, sampling_points, observations, output)
    typer.echo(f"Created {target}")


@app.command("publish-risk-map")
def publish_risk_map(
    screen: Path = Path("data/products/risk/pilot-screen.geojson"),
    sampling_points: Path = Path("data/raw/water-quality/pilot-sampling-points.geojson"),
    output: Path = Path("data/products/risk/pilot-map.html"),
) -> None:
    """Publish the pilot pressure screen as an interactive static map."""
    target = build_risk_map(screen, sampling_points, output)
    typer.echo(f"Created {target}")


@app.command("build-evidence-pack")
def build_evidence_pack_command(
    screen: Path = Path("data/products/risk/pilot-screen.geojson"),
    monitoring: Path = Path("data/features/monitoring/pilot-seasonal.parquet"),
    output: Path = Path("data/products/evidence"),
) -> None:
    """Build the pilot diagnostic report and investigation shortlist."""
    target = save_evidence_pack(screen, monitoring, output)
    typer.echo(f"Created {target}")


@app.command("build-validation-partitions")
def build_validation_partitions_command(
    development: Annotated[list[str], typer.Option(help="Repeat AREA_ID=PATH for development")],
    external: Annotated[
        list[str], typer.Option(help="Repeat AREA_ID=PATH for external validation")
    ],
    output: Path = Path("data/features/validation/geographic-partitions.parquet"),
) -> None:
    """Label development and external feature tables without random splitting."""
    target = save_geographic_partitions(
        parse_partition_paths(development),
        parse_partition_paths(external),
        output,
    )
    typer.echo(f"Created {target}")


@app.command("evaluate-fixed-baseline")
def evaluate_fixed_baseline_command(
    table: Path = Path("data/features/validation/geographic-partitions.parquet"),
    output: Path = Path("data/products/model/wyre-fixed-baseline.parquet"),
) -> None:
    """Fit the preregistered development baseline and evaluate on the holdout."""
    from earth_risk_watch.model import save_fixed_baseline_evaluation

    target = save_fixed_baseline_evaluation(table, output)
    typer.echo(f"Created {target}")


@app.command("build-evaluation-diagnostics")
def build_evaluation_diagnostics_command(
    predictions: Path,
    partitions: Path,
    output: Path = Path("data/products/model/evaluation-diagnostics.json"),
    draws: int = typer.Option(1_000, min=100),
    seed: int = 42,
) -> None:
    """Quantify external uncertainty by resampling whole monitored cells."""
    target = save_evaluation_diagnostics(predictions, partitions, output, draws=draws, seed=seed)
    typer.echo(f"Created {target}")


if __name__ == "__main__":
    app()
