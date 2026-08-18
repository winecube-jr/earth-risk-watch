# Configurable study areas

Study-area identity is separated from pipeline code in `config/study_areas.yaml`.
The registry includes the original Lune–Rawthey-to-Greta operational catchment,
the complete Lune management catchment, and the neighbouring Wyre management
catchment. Wyre is designated as an external-validation expansion: its data must
remain a distinct geographic group when models or thresholds are assessed.
Ribble is designated as a development expansion, adding upland, agricultural,
urban and estuarine contexts while preserving Wyre as the untouched holdout.
After the fixed v1 evaluation consumed Wyre, Thames and Chilterns South was
reserved as the next untouched external area. It must remain excluded from all
model changes until a new specification is frozen.

That v1 sequence is now historical. For upstream model v2, Lune and Ribble were
the development catchments and Derwent Derbyshire was frozen before model
selection. Derwent passed its coverage gate and was evaluated once on 18 August
2026; it is now consumed. Any subsequent model change requires a newly selected
untouched area. Current results and selection hashes are recorded in
`docs/upstream-external-results.md` and `config/upstream_model_selection.yaml`.

`earth-risk extract-study-area AREA_ID` downloads the official boundary and
classifications with checksums. Every downstream command already accepts custom
geometry and output paths, allowing the same grid, Water Quality Explorer,
LiDAR, Earth Engine, screening, and evidence logic to be reused for expansion.

No expansion is automatically treated as validation. Monitoring-site coverage,
temporal overlap, and independence must be assessed before changing modelling
readiness. In particular, tuning on Lune and evaluating once on Wyre is more
credible than randomly splitting neighbouring cells from one catchment, although
it still represents only one external geography and cannot establish national
generalisability. The measured baseline and holdout rules are recorded in
`docs/expansion-readiness.md` and `config/validation.yaml`.
