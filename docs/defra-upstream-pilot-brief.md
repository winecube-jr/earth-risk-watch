# Earth Risk Watch: upstream environmental-risk pilot

## Decision brief

Earth Risk Watch tests whether open environmental data can support transparent,
catchment-aware screening of river water-quality risk. The pilot links official
monitoring outcomes to the complete land area draining to each sampling point,
rather than treating nearby square-grid conditions as if they were upstream
causes.

The result is promising for water temperature and deliberately cautionary for
nutrients. It demonstrates a reproducible cloud workflow and exposes where the
current evidence base is not yet geographically representative enough for
national prediction.

## What is new

For each monitoring site, the pipeline:

1. snaps the site to the MERIT Hydro drainage network;
2. traces its full upstream watershed on the native categorical routing grid;
3. validates traced pixel count against MERIT's independent upstream-pixel
   count and rejects boundary-truncated or inconsistent watersheds;
4. aggregates open land-cover, rainfall, soil-moisture and storm-overflow
   indicators over that watershed;
5. predicts seasonal Environment Agency water-quality summaries using spatially
   independent validation groups;
6. carries provenance hashes, uncertainty intervals and an explicit
   applicability-domain warning into the output.

This is designed as an auditable screening workflow. It does not infer causal
pollution sources, replace monitoring, establish compliance or recommend
site-specific engineering works.

## Evidence generated

| Stage | Geography | Sites | Purpose |
|---|---|---:|---|
| Development | Lune and Ribble | 108 | Fit models and test two-way geographic transfer |
| Untouched validation | Derwent Derbyshire | 92 | One-shot test of frozen eligible models |

All 200 upstream watersheds used across these stages passed native-grid topology
checks; none were truncated. The development table contains 1,646 seasonal
outcome rows and the Derwent holdout contains 1,179.

## Untouched Derwent findings

| Outcome | External result | Interpretation |
|---|---|---|
| Water temperature | R² 0.632; MAE 1.404; 42.3% MAE improvement over the development median | Useful transferable signal, subject to domain warning |
| Nitrate | R² -0.070; MAE 1.651; 37.5% MAE improvement over the median | Improves typical absolute error but does not explain variation reliably |
| Orthophosphate | R² 0.111; MAE 0.106; 40.8% worse than the median | Fails the naive-baseline test |

pH and ammoniacal nitrogen were stopped before external evaluation because they
failed the preregistered development-transfer gate. This avoids selecting only
favourable Derwent outcomes after inspection.

Every Derwent prediction is outside the frozen applicability domain. Annual
rainfall, maximum daily rainfall and upper-layer soil moisture fall outside the
Lune–Ribble training ranges for all evaluated rows. That is a central finding:
two north-west development catchments do not span the environmental conditions
needed for a national model.

## What could be presented to Defra now

- A working, open-source, cloud-executable pipeline joining hydrology, Earth
  observation, climate, wastewater and monitoring data.
- A topology validation method that caught and prevented a categorical-raster
  resampling error before modelling.
- Honest geographic-transfer and untouched-holdout evidence, including negative
  results and whole-site bootstrap uncertainty.
- A practical applicability warning showing when a prediction exceeds training
  support.
- A reproducible basis for designing a geographically stratified national
  feasibility study.

The defensible proposition is not “we can already predict environmental quality
across England.” It is “we can build an auditable upstream evidence system,
quantify where it transfers, and identify the additional geography and
monitoring needed before operational use.”

## Proposed next phase

1. Preselect a geographically stratified development cohort spanning dry
   lowland, wet upland, urban, agricultural and mixed catchments.
2. Reserve a new untouched catchment before examining its outcomes.
3. Rebuild the same native-grid features without changing the Derwent-tested
   pipeline in response to individual sites.
4. Assess whether climate-support coverage and nutrient transfer improve across
   leave-one-catchment-out folds.
5. Add multi-year hydrometeorology, geological and agricultural-pressure layers
   only as separately preregistered experiments.
6. Co-design thresholds, governance and acceptable-error criteria with Defra and
   Environment Agency domain experts before any operational pilot.

## Reproducibility

The frozen model choice is in
[`config/upstream_model_selection.yaml`](../config/upstream_model_selection.yaml).
Detailed development and external results are in
[`upstream-robust-results.md`](upstream-robust-results.md) and
[`upstream-external-results.md`](upstream-external-results.md). Generated reports
record input, model, selection and prediction SHA-256 hashes. The repository's
full automated gate currently passes 116 tests with more than 80% source
coverage.
