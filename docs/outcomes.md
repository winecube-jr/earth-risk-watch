# Environment Agency ecological outcomes

The pilot classification extraction contains regulatory classifications rather
than raw laboratory measurements. Earth Risk Watch normalizes the ecological
status records into an ordinal table while preserving water-body and year identity.

## Ordinal mapping

| Status | Score |
|---|---:|
| Bad | 0 |
| Poor | 1 |
| Moderate | 2 |
| Good | 3 |
| High | 4 |

The numeric score preserves order only. It must not be treated as an interval-scale
measurement where the difference between every adjacent category is equal.

## Pilot result

- 89 historical ecological records
- 7 distinct water bodies
- reporting years from 2009 to 2022
- 62 Good, 26 Moderate, and 1 Poor classification

## Why a model is not trained yet

The 89 records are repeated observations of only seven spatial entities and are
therefore not 89 independent samples. The present satellite table describes 2024,
whereas the latest regulatory classification is from 2022. Treating every historic
row as an independent target, or attaching 2022 outcomes to 2024 predictors without
a declared lag hypothesis, would create misleading validation results.

The preferred next target is continuous, dated water-quality monitoring data. It
can be aggregated into seasonal outcomes aligned with satellite observation windows,
while spatial folds keep entire monitoring locations out of training data.
