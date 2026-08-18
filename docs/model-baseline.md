# Fixed geographic baseline

The first predictive experiment is deliberately preregistered in
`config/baseline_model.yaml`. A separate ridge model is fitted for each water
quality determinand using only Lune and Ribble rows. Predictors are the fixed
seasonal Sentinel index summaries, common Copernicus surface-height and slope
summaries, and season. The non-negative target is transformed with `log1p` and
predictions are transformed back and clipped at zero.

Wyre is evaluated once and is never used to select predictors, transformations,
regularisation, or thresholds. Results are compared with a constant baseline set
to the median development target for that determinand. MAE, R-squared, Spearman
correlation and baseline-relative MAE skill are reported. Passing the software
readiness gate permits this experiment; it does not make the result operational,
causal, nationally representative, or appropriate for regulatory decisions.
