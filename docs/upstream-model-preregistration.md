# Upstream model preregistration

## Status

This design is fixed before corrected native-grid Lune and Ribble features are
examined. The earlier resampled-routing features are invalid and prohibited from
model fitting. No external validation may begin until a new untouched catchment
is named and frozen in configuration.

The design was executed on 18 August 2026. Results are recorded in
[`upstream-development-results.md`](upstream-development-results.md); Derwent
Derbyshire remains the untouched external holdout.

## Development population

Development data comprise monitoring sites with complete, topology-consistent
MERIT watersheds in Lune and Ribble. A site must have a traced-to-MERIT upstream
pixel ratio within 1%, no contact with the routing boundary, positive upstream
area and non-zero coverage for every raster layer. Site identifiers must be
disjoint between catchments. Outcomes are aggregated at site × season ×
determinand, preserving site as the independent grouping unit.

## Outcomes

Separate models may be assessed for pH (`0061`), water temperature (`0076`),
ammoniacal nitrogen (`0111`), nitrate (`0117`) and orthophosphate (`0180`). No
multi-output pooling is permitted in the first experiment. Target transformations
must be declared from development distributions only; nutrient targets may use
`log1p` if their skew and zero support justify it. Censoring fraction and sample
count are diagnostics, not predictors.

## Fixed predictors

The initial predictor set is deliberately small and interpretable:

- log upstream area;
- upstream tree, grass, cropland, built-up, water and wetland fractions;
- annual precipitation, maximum daily precipitation and mean upper-layer soil
  moisture;
- overflow count, reported spill count and reported spill hours per 100 km²;
- season as a categorical effect.

Raster sums, raw pixel counts, monitoring coverage, outcome sampling intensity,
site identifiers, catchment identifiers and any ecological-status outcome are
excluded. Catchment identity is retained only for validation and reporting.

## Model and validation

The primary benchmark is regularised Ridge regression in a pipeline containing
median imputation, standardisation and one-hot encoding of season. Hyperparameter
selection must use grouped folds holding out entire monitoring sites. Reported
development performance must include leave-one-catchment-out transfer in both
directions, not random row splits. Any tree-based comparison is secondary and
uses the identical folds and predictors.

Metrics are MAE, RMSE and R² with whole-site bootstrap confidence intervals.
Predictions and residuals must be reported by catchment and season. A model is
not considered transferable merely because pooled grouped cross-validation is
positive.

## External validation

Wyre and Thames are consumed and cannot be reused to claim unbiased performance.
A different catchment must be selected using monitoring coverage and geographic
contrast only, frozen before fitting, processed through the same native-grid
pipeline, and evaluated once. No predictor, transformation, hyperparameter or
exclusion rule may be changed in response to that holdout result.

## Interpretation

All models remain associative screening tools. Storm-overflow activity does not
measure pollutant load, land cover does not measure agricultural application,
and ERA5-Land does not provide local observed rainfall. No causal, regulatory,
compliance or site-specific engineering claim is supported.
