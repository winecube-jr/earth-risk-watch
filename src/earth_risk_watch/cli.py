"""Command-line interface for repeatable local and cloud execution."""

import json
from pathlib import Path

import typer

from earth_risk_watch.catalogue import load_catalogue
from earth_risk_watch.cloud_run import (
    run_grid_features,
    run_pilot_summary,
    run_seasonal_summary,
)
from earth_risk_watch.demo import build_demo_manifest
from earth_risk_watch.extract.ea_catchments import (
    save_pilot_classifications,
    save_pilot_geometry,
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
) -> None:
    """Download a bounded 10 m pilot DTM from the official LiDAR WCS."""
    target = save_lidar_subset(geometry, output)
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


if __name__ == "__main__":
    app()
