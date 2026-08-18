# Configurable study areas

Study-area identity is separated from pipeline code in `config/study_areas.yaml`.
The registry currently includes the original Lune–Rawthey-to-Greta operational
catchment and the complete Lune management catchment, comprising six operational
catchments.

`earth-risk extract-study-area AREA_ID` downloads the official boundary and
classifications with checksums. Every downstream command already accepts custom
geometry and output paths, allowing the same grid, Water Quality Explorer,
LiDAR, Earth Engine, screening, and evidence logic to be reused for expansion.

The management-catchment expansion is not automatically treated as validation.
Its monitoring-site coverage, temporal overlap, and independence must be assessed
before changing the modelling-readiness status.
