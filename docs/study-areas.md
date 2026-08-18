# Configurable study areas

Study-area identity is separated from pipeline code in `config/study_areas.yaml`.
The registry includes the original Lune–Rawthey-to-Greta operational catchment,
the complete Lune management catchment, and the neighbouring Wyre management
catchment. Wyre is designated as an external-validation expansion: its data must
remain a distinct geographic group when models or thresholds are assessed.

`earth-risk extract-study-area AREA_ID` downloads the official boundary and
classifications with checksums. Every downstream command already accepts custom
geometry and output paths, allowing the same grid, Water Quality Explorer,
LiDAR, Earth Engine, screening, and evidence logic to be reused for expansion.

No expansion is automatically treated as validation. Monitoring-site coverage,
temporal overlap, and independence must be assessed before changing modelling
readiness. In particular, tuning on Lune and evaluating once on Wyre is more
credible than randomly splitting neighbouring cells from one catchment, although
it still represents only one external geography and cannot establish national
generalisability.
