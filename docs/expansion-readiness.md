# Expansion readiness

Cloud inventories establish adequate combined coverage, but holdout cells cannot
be counted as training support. The linked feature tables currently contain 29
Lune development cells and 13 Wyre holdout cells. The development partition is
therefore one cell below the 30-cell software floor; predictive training remains
blocked. This does not affect continued data engineering and coverage expansion.

| Area | Role | Area (km²) | Grid cells | Active river sites | Monitored cells | 2024 observations |
|---|---|---:|---:|---:|---:|---:|
| Lune Management Catchment | development | 1,200.6 | 379 | 33 | 29 | 2,382 |
| Ribble Management Catchment | development | 1,404.5 | 437 | 75 | 67 | 3,895 |
| Wyre Management Catchment | external validation | 384.0 | 138 | 17 | 13 | 1,601 |
| **Total** | | **2,989.1** | **954** | **125** | **109** | **7,878** |

The inventories were run using the public-data GitHub Actions workflow on
18 August 2026. The Lune result is
[run 32139494960](https://github.com/winecube-jr/earth-risk-watch/actions/runs/32139494960)
the Ribble result is
[run 32142061181](https://github.com/winecube-jr/earth-risk-watch/actions/runs/32142061181),
and the Wyre result is
[run 32140087907](https://github.com/winecube-jr/earth-risk-watch/actions/runs/32140087907).

The configured policy reserves Wyre as a geographic holdout. It must not be used
to choose variables, tune the model, select risk thresholds, or revise the
screening weights. The 13 monitored Wyre cells clear the initial ten-cell
external coverage floor, but represent only one catchment. Any performance result
must therefore be presented as an external pilot, not evidence of UK-wide
generalisability.

Matching Sentinel and common-terrain features now produce 96 development cells
across Lune and Ribble and 13 external cells in Wyre, with no grid-cell overlap
between roles. This clears the minimum software gate for a geographically grouped
experiment. Predictive work remains subordinate to data leakage checks,
per-determinand sample sizes, censored-result treatment, spatial dependence, and
uncertainty reporting.

## Terrain coverage finding

The cross-catchment public-feature run
[32140745977](https://github.com/winecube-jr/earth-risk-watch/actions/runs/32140745977)
found EA LiDAR coverage in 117 of 379 Lune cells and all 138 Wyre cells. Because
that missingness strongly identifies geography, LiDAR is supplementary rather
than the primary terrain baseline. The current Copernicus GLO-30 2024_1 surface
model was subsequently reduced in Earth Engine for all 517 cells with no missing
metrics. This preserves a common terrain feature definition while retaining
LiDAR coverage and higher-resolution summaries for explicit sensitivity work.
