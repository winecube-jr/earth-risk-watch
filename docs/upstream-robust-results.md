# Robust upstream development results

## Outcome

The fixed random-forest comparison substantially reduced the unsupported linear
extrapolation seen in the Ridge experiment. It passed the preregistered
two-direction advancement rule for water temperature, nitrate and
orthophosphate. pH and ammoniacal nitrogen failed and are excluded from the
untouched Derwent evaluation.

| Determinand | Held-out catchment | MAE | RMSE | R² | MAE skill vs training median |
|---|---|---:|---:|---:|---:|
| pH | Lune | 0.341 | 0.461 | -0.339 | 0.007 |
| pH | Ribble | 0.502 | 0.615 | -0.880 | -0.595 |
| Water temperature | Lune | 0.900 | 1.192 | 0.854 | 0.663 |
| Water temperature | Ribble | 1.271 | 1.566 | 0.739 | 0.502 |
| Ammoniacal nitrogen | Lune | 0.076 | 0.281 | 0.194 | 0.244 |
| Ammoniacal nitrogen | Ribble | 0.104 | 0.324 | -0.039 | -0.180 |
| Nitrate | Lune | 0.390 | 0.548 | 0.491 | 0.386 |
| Nitrate | Ribble | 0.538 | 1.051 | 0.197 | 0.262 |
| Orthophosphate | Lune | 0.033 | 0.048 | 0.559 | 0.347 |
| Orthophosphate | Ribble | 0.053 | 0.083 | 0.062 | 0.171 |

The forest bounds predictions to training-response support, removing the
physically implausible inverse-transform explosions from the Ridge comparison.
This is improved robustness, not proof of national validity.

## Applicability warning

The frozen applicability rule flags 77–93% of held-out rows, depending on
outcome and direction. This high rate is itself a result: Lune and Ribble occupy
substantially different predictor domains, particularly for precipitation,
soil moisture and built-up land. Flagged rows remain in all headline metrics.

The warning should accompany every later prediction. It must not be used to
discard difficult Derwent rows or improve external metrics after the fact.

## Frozen selection

The machine-readable decision is committed in
[`upstream_model_selection.yaml`](../config/upstream_model_selection.yaml). The
manifest records exact SHA-256 hashes for the Ridge report, forest report and
forest model bundle. Only the following frozen candidates may be evaluated on
Derwent:

- water temperature (`0076`): random forest;
- nitrate (`0117`): random forest;
- orthophosphate (`0180`): random forest.

The pH and ammonia models remain valuable negative development results but are
not eligible for external performance claims.
