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

## Google Colab: complete pilot

Open `notebooks/02_end_to_end_colab.ipynb` in Colab. It clones the repository,
installs dependencies in the temporary runtime, requests interactive Earth Engine
authentication, and runs every pipeline stage through the CLI. The final cell
downloads a compact ZIP containing the risk map, screen, evidence report, and
provenance.

Colab runtimes are ephemeral. Download required products before disconnecting.
Authentication tokens and raw data must never be copied into the repository.

## Unattended Earth Engine

This remains deliberately disabled. A future unattended workflow should use
Google workload identity federation or an appropriately restricted service
account, not a long-lived JSON key stored as a GitHub secret.
