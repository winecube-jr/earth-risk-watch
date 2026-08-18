# Cloud execution

The project supports two free hosted execution paths.

## GitHub Actions: credential-free public data

Run the `public-data-pipeline` workflow manually from the repository Actions tab.
It rebuilds the EA catchment, sampling points, 2024 observations, bounded LiDAR
subset, grid, and terrain features on a GitHub-hosted runner. Compact outputs and
provenance are retained as a downloadable artifact for seven days. The 36 MB
LiDAR raster itself is not uploaded because it is reproducible and unnecessarily
increases artifact storage.

The workflow has read-only repository permissions, a 30-minute timeout, bounded
downloads, and no secrets. It cannot run Earth Engine stages.

The separate `study-area-inventory` workflow evaluates configured expansion
areas without launching raster processing. It downloads the official geometry
and classifications, creates the 2 km grid, queries sampling points, and reports
area, cell count, open-river monitoring coverage, 2024 observations, and observed
spatial-cell count as a seven-day artifact.

The `cross-catchment-public-features` workflow then rebuilds Lune and Wyre as
independent matrix jobs. Both use the same 2 km grid, 2024 observation window,
determinands, and 20 m WCS-resampled LiDAR product. The common terrain resolution
keeps the larger Lune request below the download safety cap and prevents a
resolution difference from becoming a hidden catchment signal. Cells outside
LiDAR coverage are retained with a zero pixel count and missing terrain values.

## Google Colab: complete pilot

Open `notebooks/02_end_to_end_colab.ipynb` in Colab. It clones the repository,
installs dependencies in the temporary runtime, requests interactive Earth Engine
authentication, and runs every pipeline stage through the CLI. The final cell
downloads a compact ZIP containing the risk map, screen, evidence report, and
provenance.

Colab runtimes are ephemeral. Download required products before disconnecting.
Authentication tokens and raw data must never be copied into the repository.

For development-scale upstream features, open
`notebooks/03_upstream_development_colab.ipynb`. After one interactive Earth
Engine authentication, it runs `earth-risk run-upstream-area` for Lune and
Ribble. Each configured-area run downloads its official boundary, sampling
points and 2024 observations; builds buffered MERIT routing, WorldCover and
ERA5-Land rasters; delineates complete site watersheds; attaches national 2024
EDM activity; and writes a readiness summary. The final cell downloads compact
features, summaries and provenance as a ZIP before the ephemeral runtime closes.

Wyre and Thames are intentionally absent from this notebook. Their evaluations
have already been consumed, so they may be processed only for engineering
diagnostics and must not influence feature selection or model tuning.

## Unattended Earth Engine

This remains deliberately disabled. A future unattended workflow should use
Google workload identity federation or an appropriately restricted service
account, not a long-lived JSON key stored as a GitHub secret.
