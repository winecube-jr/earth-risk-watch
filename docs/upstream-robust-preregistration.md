# Robust upstream model preregistration

## Status and purpose

This second development experiment is fixed after observing the preregistered
Ridge transfer failure and before fitting the model described here. It uses only
Lune and Ribble. Derwent Derbyshire remains untouched.

The purpose is to test a bounded, nonlinear comparison and attach an explicit
applicability warning. It does not replace or retrospectively alter the first
Ridge experiment.

## Model

One random-forest regressor is fit per determinand with 500 trees,
`min_samples_leaf=5`, `max_features=0.7`, bootstrap sampling enabled and random
seed 42. These settings are fixed; no hyperparameter search is performed.
Numeric predictors are median-imputed and season is one-hot encoded. The feature
set and nutrient `log1p` transformations are identical to the first experiment.
Because tree predictions average training responses, inverse-transformed
predictions remain bounded by training-target support.

## Validation and metrics

The exact Lune-to-Ribble and Ribble-to-Lune splits from the first experiment are
used. No row-random split is permitted. MAE, RMSE and R² are reported overall,
by season and by applicability class, with 1,000 bootstrap draws of whole sites.
The training-catchment median remains the naive comparator.

## Applicability domain

For every held-out row, numeric predictors are compared with the training
catchment only. The report records:

- the number and fraction of predictors outside their training minimum–maximum
  range;
- the maximum absolute robust z-score, using training median and IQR;
- any season absent from training.

A row is flagged `outside_applicability_domain` when at least two predictors are
outside their training range, the maximum robust z-score exceeds 4, or its
season was unseen. The flag is diagnostic: rows are never removed from headline
metrics.

## Advancement rule

A determinand is eligible for untouched Derwent evaluation only if one frozen
candidate model beats the training-median baseline in both catchment-transfer
directions. Between eligible Ridge and forest candidates, choose the one with
lower mean transfer MAE; ties favour Ridge. Failure of this gate means more
development geography is required and the Derwent outcomes remain unopened.

No threshold, transformation, feature, hyperparameter or advancement rule may
change after the forest results are generated. Any later change is a separately
numbered development experiment.
