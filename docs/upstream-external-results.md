# Derwent external-validation results

## Status

Derwent Derbyshire was evaluated once using the checksum-locked selection in
[`upstream_model_selection.yaml`](../config/upstream_model_selection.yaml).
The models were neither refit nor altered after opening Derwent outcomes. A
first command invocation stopped before prediction because the raw holdout table
required the same area-normalised derivation used by the development builder;
that shared deterministic transformation was wired into the evaluator without
changing features, parameters, thresholds, selection or model artifacts.

The imported table contains 1,179 seasonal outcome rows at 92 distinct sites.
All watersheds are topology-consistent with a traced/upstream pixel ratio of
exactly 1.0, none touch the routing boundary, all raster coverage is positive,
there are no duplicate outcome keys or target nulls, and no site overlaps Lune
or Ribble.

## Frozen external performance

| Determinand | Sites | MAE (site-bootstrap 95% CI) | RMSE (95% CI) | R² (95% CI) | MAE skill vs development median |
|---|---:|---:|---:|---:|---:|
| Water temperature | 79 | 1.404 (1.279, 1.523) | 1.763 (1.626, 1.892) | 0.632 (0.541, 0.699) | 0.423 |
| Nitrate | 57 | 1.651 (1.199, 2.123) | 2.490 (1.874, 3.044) | -0.070 (-0.387, 0.168) | 0.375 |
| Orthophosphate | 70 | 0.106 (0.077, 0.141) | 0.187 (0.099, 0.267) | 0.111 (-0.354, 0.170) | -0.408 |

Temperature is the clearest transferable signal: it explains meaningful
between-row variation and improves substantially on the development median.
Nitrate improves absolute error over the median but its negative R² shows that
it does not explain variation reliably. Orthophosphate fails the naive-baseline
test. These outcomes must be reported together; the successful temperature
result does not validate the nutrient models.

## Applicability result

Every evaluated Derwent row is flagged outside the frozen applicability domain.
Annual precipitation, maximum daily precipitation and upper-layer soil moisture
are outside the Lune–Ribble training ranges for 100% of rows. No seasons are
unseen. The predictions are therefore evidence about a difficult geographic
transfer, not in-domain operational estimates.

This warning does not erase the external metrics, but it prevents a claim that
the current development set supports national deployment. The next model
version needs geographically broader training catchments selected without using
Derwent performance to tune individual rules. It also requires a new untouched
holdout before any renewed external-validity claim.

## Evidence artifacts

The ignored, machine-readable artifacts are:

- `data/products/validation/upstream-external-predictions.parquet`;
- `data/products/validation/upstream-external-predictions.parquet.report.json`.

The report records SHA-256 hashes for the holdout table, development table,
frozen model, selection manifest and prediction file, plus 1,000 whole-site
bootstrap draws. All claims remain associative screening evidence and are not
causal, regulatory or compliance findings.
