# Fixed baseline results

The preregistered `fixed-ridge-log1p-v1` model was evaluated once against Wyre
on 18 August 2026, after its specification was committed as `3fe10ed`. The input
contained 96 development cells from Lune and Ribble and 13 external cells from
Wyre, with no cells shared across roles. The evaluation produced 258 holdout
predictions.

| Determinand | Unit | Holdout rows | MAE | R² | Spearman | MAE skill vs median |
|---|---|---:|---:|---:|---:|---:|
| pH | pH units | 50 | 0.325 | -0.216 | 0.429 | 20.9% |
| Water temperature | °C | 52 | 0.776 | 0.910 | 0.870 | 70.3% |
| Ammoniacal nitrogen as N | mg/l | 52 | 0.169 | 0.103 | 0.756 | 25.9% |
| Nitrate as N | mg/l | 52 | 0.751 | 0.120 | 0.601 | 4.4% |
| Reactive orthophosphate as P | mg/l | 52 | 0.078 | 0.232 | 0.738 | 32.7% |

Temperature is the clearest transferable signal, plausibly because season,
surface characteristics and terrain capture substantial physical structure. The
nutrient models show useful rank association but modest R², indicating that they
may help prioritize investigation while remaining poorly calibrated for numeric
concentration prediction. The pH model improves absolute error over the constant
baseline but has negative R² and should not be treated as predictive.

These are exploratory results from one external catchment, 13 monitored cells
and one year. Seasonal rows from the same cell are not independent, monitoring
locations are preferential, censored observations require further sensitivity
analysis, and the Copernicus product is a surface model rather than bare-earth
terrain. No operational, causal, regulatory, or England-wide claim is supported.

Wyre is no longer an untouched holdout for subsequent model redesign. Any change
to features, transformations, algorithms or hyperparameters informed by these
results requires a newly reserved catchment for honest external evaluation.
