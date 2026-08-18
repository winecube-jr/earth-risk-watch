# Pilot evidence pack

`earth-risk build-evidence-pack` creates a concise Markdown report, a CSV of
nutrient-alignment diagnostics, a GeoJSON investigation shortlist, and a JSON
manifest. The diagnostic uses annual cell aggregates for ammonia, nitrate, and
reactive orthophosphate, avoiding the false sample-size inflation that would come
from treating seasonal records as independent locations.

Spearman rank correlations describe monotonic alignment between observed
nutrients and three screening metrics. Two-sided permutation values use 999
deterministic shuffles. With only eight monitored cells, results are explicitly
low-power diagnostics and are neither causal evidence nor predictive validation.
The generated report explicitly counts comparisons below a 0.05 permutation
threshold. This is a descriptive warning flag, not a multiple-testing-adjusted
model-selection rule.

The shortlist includes cells appearing in the top catchment quintile under at
least 80% of the weight-sensitivity simulations. Cells more than 5 km from a 2024
monitoring site are marked as evidence gaps, making the output useful for planning
further investigation without claiming their environmental condition is known.
