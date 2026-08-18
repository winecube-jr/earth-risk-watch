# Frozen upstream-model holdout

## Evaluation status

Derwent passed its eligibility gate with 92 complete watersheds, no truncation
and no topology inconsistency. The frozen models were evaluated once on 18
August 2026. Results are reported in
[`upstream-external-results.md`](upstream-external-results.md). Derwent is now
consumed and cannot be reused as an untouched holdout for later model changes.

## Selection

Derwent Derbyshire Management Catchment (`3026`) is frozen as the upstream-v2
external holdout on 18 August 2026. The choice was made before downloading or
examining its 2024 water-quality outcome values.

The catchment provides a deliberate geographic and landscape contrast with the
north-west Lune and Ribble development areas. The Environment Agency describes
an approximately 1,197 km² inland catchment spanning rural headwaters,
reservoirs, market towns and the urban area of Derby. This creates a meaningful
test of transfer beyond the development region without reusing the already
consumed Wyre or Thames evaluations.

Official area record:
<https://environment.data.gov.uk/catchment-planning/ManagementCatchment/3026>

## Eligibility gate

Processing the area does not automatically make it an evaluable holdout. Before
model fitting—and without inspecting target values—it must yield at least ten
complete native-grid watersheds and at least ten independent sites for every
determinand selected for external evaluation. All sites must pass boundary,
topology-concordance and raster-coverage checks.

If the gate fails, Derwent Derbyshire remains documented as infeasible and is
not replaced based on model performance. A replacement would require a new,
explicitly versioned selection decision based only on coverage and geography.

## Lock rules

- Do not use Derwent outcomes for predictor selection or transformations.
- Do not use Derwent to choose Ridge regularisation or exclusion thresholds.
- Fit and freeze the development pipeline before opening holdout predictions.
- Evaluate once and report all preregistered determinands, including failures.
- Do not use Wyre or Thames as substitute unbiased evaluations.
