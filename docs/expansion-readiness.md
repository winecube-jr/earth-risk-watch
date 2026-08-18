# Expansion readiness

Cloud inventories establish that the current expansion has enough spatial groups
to begin building a geographically grouped modelling experiment. They do not
establish that a model is valid or suitable for operational decisions.

| Area | Role | Area (km²) | Grid cells | Active river sites | Monitored cells | 2024 observations |
|---|---|---:|---:|---:|---:|---:|
| Lune Management Catchment | development | 1,200.6 | 379 | 33 | 29 | 2,382 |
| Wyre Management Catchment | external validation | 384.0 | 138 | 17 | 13 | 1,601 |
| **Total** | | **1,584.6** | **517** | **50** | **42** | **3,983** |

The inventories were run from commit `ef615f9` using the public-data GitHub
Actions workflow on 18 August 2026. The Lune result is
[run 32139494960](https://github.com/winecube-jr/earth-risk-watch/actions/runs/32139494960)
and the Wyre result is
[run 32140087907](https://github.com/winecube-jr/earth-risk-watch/actions/runs/32140087907).

The configured policy reserves Wyre as a geographic holdout. It must not be used
to choose variables, tune the model, select risk thresholds, or revise the
screening weights. The 13 monitored Wyre cells clear the initial ten-cell
external coverage floor, but represent only one catchment. Any performance result
must therefore be presented as an external pilot, not evidence of UK-wide
generalisability.

The next build stage is to produce Sentinel and terrain features for both areas,
train only on Lune, and evaluate once on Wyre. Predictive work remains subordinate
to data leakage checks, per-determinand sample sizes, censored-result treatment,
spatial dependence, and uncertainty reporting.

## Terrain coverage finding

The cross-catchment public-feature run
[32140745977](https://github.com/winecube-jr/earth-risk-watch/actions/runs/32140745977)
found EA LiDAR coverage in 117 of 379 Lune cells and all 138 Wyre cells. Because
that missingness strongly identifies geography, LiDAR is supplementary rather
than the primary terrain baseline. The current Copernicus GLO-30 2024_1 surface
model was subsequently reduced in Earth Engine for all 517 cells with no missing
metrics. This preserves a common terrain feature definition while retaining
LiDAR coverage and higher-resolution summaries for explicit sensitivity work.
