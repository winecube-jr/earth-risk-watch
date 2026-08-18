# Monitoring-linked feature table

`earth-risk build-monitoring-features` creates the first table that combines
independent in-river observations with Earth-observation predictors. Each row is
one `cell_id`, satellite `season`, and water-quality `determinand_code`.

Sampling points are assigned to intersecting clipped 2 km grid cells. Monitoring
dates are assigned to the exact half-open Sentinel composite windows: the start
date is included and the end date is excluded. Observations outside those windows
are retained in the source product but excluded from this linkage.

Targets include the mean, median, standard deviation, range, observation count,
site count, censored count, and censored fraction. Predictor columns are joined
from the matching grid cell and season. Missing monitoring remains missing: the
pipeline does not manufacture targets for unmonitored cells.

This is an exploratory pilot table, not yet a defensible national training set.
Nearby observations can be spatially and temporally dependent, monitoring is
preferential rather than random, and the small number of monitored cells cannot
support reliable out-of-area claims. Later modelling must use grouped spatial
validation and report coverage separately from predicted condition.

The output provenance includes a modelling-readiness gate. Predictive modelling
is blocked when there are fewer than 30 monitored spatial groups or when an
individual determinand occurs in fewer than 10 cells. These are minimum software
guardrails, not evidence that a dataset passing them is automatically adequate.
