# Water-quality observations

The pilot uses the current Defra/Environment Agency Water Quality Explorer API,
not the retired legacy Water Quality Archive interface. The reproducible 2024
extract is restricted to open `FRESHWATER - RIVERS` sampling points within the
pilot boundary and requests pH, water temperature, turbidity, ammoniacal
nitrogen, nitrate, and reactive orthophosphate.

The raw reporting semantics are retained in `reported_result`, `value`,
`lower_bound`, `upper_bound`, and `is_censored`. For modelling, `analysis_value`
uses half the upper bound for results reported below a detection limit, and the
lower bound for results reported above a quantification limit. This substitution
is explicit, reproducible, and should be sensitivity-tested in later modelling.

The source is observational monitoring data. Site selection and sampling
frequency are not spatially uniform, and absence of observations is not evidence
of good environmental quality. In the 2024 pilot extract, only a subset of the
eligible river sites have records for the selected determinands and turbidity is
absent. These coverage limitations must be represented in model uncertainty.
