# Earth Risk Watch

Cloud-first environmental risk and nature-recovery opportunity modelling for England.

The project combines Earth observation, LiDAR, regulatory monitoring, climate,
habitat, and community data. Raw national datasets remain with their publishers;
the pipeline stores compact, reproducible derived features and model products.

## Status

The repository is in its foundation phase. It currently provides:

- a typed Python package and command-line interface;
- configuration-driven areas, indicators, and data sources;
- a machine-readable source catalogue;
- Earth Engine and HTTP data-source readiness checks;
- a small, reproducible sample pipeline that does not require credentials;
- unit tests, linting, type checking, security checks, and GitHub Actions;
- Colab-ready onboarding notebooks;
- architecture, methodology, governance, and setup documentation.

No credentials or large datasets belong in this repository.

## Quick start

Python 3.11 or 3.12 is recommended because compiled GIS packages may not yet
publish wheels for newer Python releases.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
earth-risk doctor
earth-risk catalogue list
earth-risk demo --output data/products/demo
earth-risk sentinel-plan
earth-risk extract-ea-geometry
earth-risk sentinel-summary
earth-risk sentinel-seasonal
earth-risk build-grid
earth-risk sentinel-grid-features
earth-risk build-ecological-outcomes
earth-risk extract-water-sampling-points
earth-risk extract-water-observations
earth-risk build-monitoring-features
earth-risk extract-lidar-terrain
earth-risk build-terrain-features
earth-risk build-risk-screen
earth-risk publish-risk-map
pytest
```

See [docs/setup.md](docs/setup.md) for cloud authentication and
[docs/architecture.md](docs/architecture.md) for the system design. The current
Earth-observation method is documented in
[docs/satellite-baseline.md](docs/satellite-baseline.md), and the model-ready
table contract is described in [docs/feature-table.md](docs/feature-table.md).
The independent regulatory outcome assessment and its modelling constraints are
documented in [docs/outcomes.md](docs/outcomes.md).
The live regulatory monitoring extraction and censored-result treatment are
documented in [docs/water-quality.md](docs/water-quality.md).
The spatial-temporal monitoring linkage is documented in
[docs/monitoring-features.md](docs/monitoring-features.md).
The bounded Environment Agency LiDAR method is documented in
[docs/terrain.md](docs/terrain.md).
The explainable, non-predictive prioritisation layer is documented in
[docs/risk-screen.md](docs/risk-screen.md).

## Project principles

1. England-first, with explicit extension points for the rest of the UK.
2. Process data close to its source; do not build a duplicate raw-data lake.
3. Separate observable condition, modelled risk, vulnerability, and opportunity.
4. Validate geographically using spatially separated folds.
5. Publish uncertainty, provenance, licensing, and limitations with every result.
6. Treat notebooks as explanations; keep repeatable logic in `src/`.

## Licence

Project code is licensed under the MIT License. Source datasets retain their
original licences and attribution requirements.
