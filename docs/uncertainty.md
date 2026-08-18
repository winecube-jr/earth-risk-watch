# External-evaluation uncertainty

`earth-risk build-evaluation-diagnostics` joins external predictions back to
their monitoring support and resamples whole 2 km monitoring cells. All seasonal
rows from a selected cell move together in each bootstrap draw, avoiding false
precision from treating repeated cell-season rows as independent.

The deterministic report contains 95% bootstrap intervals for MAE, R-squared,
Spearman correlation and MAE skill against the development-median baseline. It
also reports performance separately by season and by whether an aggregated
target contains censored laboratory results. These intervals describe sampling
variation among monitored cells only; they do not correct preferential site
placement, measurement error, covariate shift or unmeasured pollution sources.
