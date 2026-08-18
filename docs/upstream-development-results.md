# Upstream development results

## Status

This is the first execution of the preregistered upstream model using corrected
native-grid MERIT watersheds. It is a development evaluation, not external
validation. Derwent Derbyshire remains untouched and no Derwent outcome was
loaded, inspected or used.

The combined Lune and Ribble table contains 1,646 site-season-determinand rows
from 108 distinct monitoring sites. All 108 watersheds are topology-consistent,
none touch the routing-grid boundary, predictor null counts are zero and the two
catchments share no monitoring-site identifiers.

## Frozen execution

Separate Ridge models were fit for each determinand. Alpha was selected from
`0.01, 0.1, 1, 10, 100` using five-fold grouped cross-validation on whole sites
inside the training catchment. Transfer was then assessed in both directions by
holding out the other catchment. Confidence intervals use 1,000 bootstrap draws
of whole monitoring sites.

Development-only distribution checks supported `log1p` for ammoniacal nitrogen,
nitrate and orthophosphate because their target skews were 10.59, 3.29 and 2.36.
pH and water temperature remained on their original scales. No transformation
was selected from transfer-test or external-holdout performance.

## Catchment-transfer performance

| Determinand | Held-out catchment | MAE | RMSE | R² | MAE skill vs training median |
|---|---|---:|---:|---:|---:|
| pH | Lune | 0.233 | 0.285 | 0.488 | 0.320 |
| pH | Ribble | 0.431 | 0.548 | -0.495 | -0.369 |
| Water temperature | Lune | 1.714 | 2.029 | 0.577 | 0.358 |
| Water temperature | Ribble | 1.895 | 2.529 | 0.320 | 0.257 |
| Ammoniacal nitrogen | Lune | 0.074 | 0.240 | 0.414 | 0.267 |
| Ammoniacal nitrogen | Ribble | 0.974 | 1.847 | -32.812 | -10.085 |
| Nitrate | Lune | 0.474 | 0.646 | 0.291 | 0.253 |
| Nitrate | Ribble | 85.329 | 317.158 | -73,118.770 | -116.056 |
| Orthophosphate | Lune | 0.049 | 0.059 | 0.331 | 0.031 |
| Orthophosphate | Ribble | 0.811 | 1.536 | -324.321 | -11.650 |

The pathological Ribble nutrient errors are retained rather than clipped or
removed. In the Lune-to-Ribble direction, 82% of annual-precipitation values are
outside the Lune training range and Ribble mean built-up fraction is about nine
Lune standard deviations higher. Linear predictions on the log scale therefore
produce extreme inverse-transformed values, including a nitrate prediction of
3,783.62 mg/L. This is evidence of unsupported extrapolation and failed
geographic transfer, not credible environmental concentration estimates.

## Interpretation and next decision

Water temperature is the only outcome that beats the training-catchment median
in both transfer directions. pH and all three nutrient models fail that test in
at least one direction. The current model must therefore not be described as a
national predictor or used for operational prioritisation.

The development result motivates broader geographic training support and an
explicit applicability-domain flag. It does not justify changing the frozen
Derwent evaluation after seeing Derwent results. Any robust-model comparison,
prediction clipping or revised target transformation must be labelled a second
development experiment and completed before the untouched holdout is opened.

Machine-readable evidence is written to:

- `data/products/development/upstream-diagnostics.json`;
- `data/products/development/upstream-transfer-predictions.parquet`;
- `data/products/development/upstream-transfer-predictions.parquet.report.json`;
- `data/models/upstream-development-models.joblib`.

These generated artifacts are checksum-linked and excluded from Git.
