# Cell-grouped uncertainty results

The fixed v1 evaluations were resampled 1,000 times by complete monitoring cell.
Intervals therefore retain all repeated seasonal rows from the selected cells.

| Catchment | Determinand | R² 95% interval | MAE-skill 95% interval | Spearman 95% interval |
|---|---|---:|---:|---:|
| Wyre | pH | -1.232 to 0.235 | 0.099 to 0.310 | 0.145 to 0.648 |
| Wyre | Water temperature | 0.880 to 0.938 | 0.657 to 0.748 | 0.797 to 0.924 |
| Wyre | Ammoniacal nitrogen | -0.066 to 0.475 | -0.110 to 0.481 | 0.517 to 0.871 |
| Wyre | Nitrate | -1.625 to 0.340 | -0.753 to 0.378 | 0.184 to 0.795 |
| Wyre | Reactive orthophosphate | -0.132 to 0.416 | 0.001 to 0.487 | 0.392 to 0.870 |
| Thames | pH | -4.238 to -1.715 | -1.130 to -0.501 | -0.172 to 0.103 |
| Thames | Water temperature | 0.654 to 0.745 | 0.468 to 0.541 | 0.809 to 0.879 |
| Thames | Ammoniacal nitrogen | -11.418 to -1.136 | -4.354 to -1.141 | 0.034 to 0.445 |
| Thames | Nitrate | -4.975 to -2.032 | 0.106 to 0.143 | -0.081 to 0.323 |
| Thames | Reactive orthophosphate | -0.172 to -0.012 | 0.178 to 0.355 | 0.170 to 0.568 |

Only water temperature has consistently strong transfer intervals in both
catchments. Thames pH and ammoniacal nitrogen are consistently worse than the
development-median baseline. Nitrate improves absolute error in Thames only
because the development median is far from Thames concentrations; its negative
R² and near-zero rank interval reject useful numeric or ranking performance.

Censoring is concentrated in ammoniacal nitrogen: 8 Wyre rows and 91 Thames rows
contain censored results. Its model is worse than the constant baseline within
those groups. Censored-value sensitivity and source-pressure predictors are
therefore required before any further nutrient modelling.
