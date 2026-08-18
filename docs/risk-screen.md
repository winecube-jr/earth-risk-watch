# Explainable pilot risk screen

The pilot screen is a relative, exploratory prioritisation layer. It is not a
validated prediction of pollution, ecological status, or regulatory failure.
It helps identify places where multiple observable pressure signals coincide and
where further evidence collection may be valuable.

Three components receive equal weight:

- sediment-delivery pressure: maximum seasonal bare-soil signal, LiDAR slope,
  and relief;
- runoff susceptibility: LiDAR slope, relief, and maximum surface-wetness signal;
- vegetation/moisture condition stress: minimum seasonal NDMI and NDVI.

Every source metric is transformed to a within-pilot percentile score before
combination. Overall scores therefore express relative contrast inside this
catchment and cannot be compared numerically with another area. The GeoJSON
retains all component scores and source metrics so no result is a black box.

Distance to the nearest sampling point represented in the 2024 observation table
is included as evidence context. It does not alter the score. Cells far from
monitoring should be considered candidates for investigation, not assumed to be
high or low condition.

Weight sensitivity is tested with 1,000 deterministic draws from a uniform
Dirichlet distribution over the three component weights. Each cell reports its
mean, standard deviation, 10th and 90th percentile score, and frequency of
appearing in the top catchment quintile. This measures sensitivity to weighting;
it is not a probabilistic confidence interval for environmental condition.

The screen requires sensitivity analysis before presentation. Future versions
must test alternative weights, seasonal summaries, grid scales, and associations
with independent outcomes. Predictive language remains prohibited until the
spatial validation gate is passed.

`earth-risk publish-risk-map` produces a static interactive HTML map containing
the screen and sampling points. It requires an internet connection only for the
Leaflet library and OpenStreetMap basemap; the project data are embedded directly
in the page. The map repeats the non-prediction warning and exposes components,
evidence distance, and weight sensitivity in each cell popup.
