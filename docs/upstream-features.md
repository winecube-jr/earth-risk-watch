# Upstream-pressure feature design

The first hydrology layer uses MERIT Hydro in Earth Engine to summarize upstream
drainage area, height above drainage, river width and permanent-water fraction
for every 2 km cell at a common 90 m processing scale. These variables provide
network and floodplain context but are not themselves upstream pollution loads.
Masked MERIT pixels are explicitly filled with zero before aggregation; for
river width and permanent water this represents absence of a mapped feature at
that pixel. Coverage validation still rejects null cell-level outputs.

The site-scale contract now snaps each monitoring location to the maximum MERIT
upstream-area pixel within a bounded search, traces its contributing D8 cells,
and emits a dissolved watershed polygon. Truncated watersheds are excluded by
default, while an explicit override is available for diagnosis. A generic raster
aggregation command calculates valid-pixel count, coverage fraction, mean,
standard deviation, minimum, maximum and sum for every named raster band inside
each watershed. Candidate pressure inputs include
land cover, rainfall and antecedent wetness, wastewater assets, urban impermeable
surface, agricultural proxies, soils and geology. Every resulting field must
record its source year, spatial support, aggregation rule and missing coverage.

The compact repository pilot fixture contains nine actively monitored sites.
With its 20 km buffered routing extract, six yield complete, valid polygons and
three larger lower-catchment watersheds reach the raster boundary and are
excluded. This differs from the expanded Lune validation run because the latter
uses a larger source boundary. Boundary status is therefore an extent-quality
check, not an intrinsic classification of a monitoring site.

## First pressure raster: land cover

ESA WorldCover v200 supplies the first independently sourced pressure raster.
The pipeline converts its 2021 10 m categorical map to eight binary class bands,
then averages those bands at a configurable 100 m processing scale. Values are
therefore class fractions rather than category codes. Tree, shrub, grass,
cropland, built-up, bare, permanent-water and wetland fractions can be aggregated
within each complete site watershed using the generic raster feature contract.

WorldCover is static and temporally offset from the 2024 monitoring outcomes. It
is useful for landscape context and interpretable source-pressure hypotheses,
but does not measure fertiliser application, wastewater discharge, pollutant
load or short-term land-cover change. The source is ESA WorldCover 2021 v200 at
10 m under CC-BY-4.0; derived exports retain the source year, class mapping,
processing scale, checksum and licence in a provenance sidecar.

The first pilot export is a 729 by 1,077 pixel, eight-band GeoTIFF of 2.28 MB.
All six complete pilot watersheds have full raster coverage. Their dominant
WorldCover class is grassland (mean watershed fractions from 0.802 to 0.958),
while built-up fractions range from approximately 0.001 to 0.020. These are
engineering validation results showing that the extraction and aggregation
contracts work; they are not evidence of a relationship with water quality.

## Rainfall and wetness context

The climate contract uses the ERA5-Land Daily Aggregated reanalysis for calendar
year 2024. It derives annual and quarterly precipitation totals in millimetres,
counts days above 1 mm and 10 mm, retains maximum daily precipitation, and
calculates mean upper-layer volumetric soil moisture. These bands use the same
coverage-aware watershed aggregation contract as land cover.

ERA5-Land's effective source resolution is approximately 11.1 km. The pipeline
exports a bilinearly resampled 1 km grid so small watershed polygons can be
processed consistently, but this adds no spatial information and must never be
described as 1 km rainfall evidence. It represents broad reanalysis context,
not rain-gauge observations, local convective rainfall, event-specific antecedent
conditions or pollutant mobilisation. A later UK-focused comparison should use
HadUK-Grid under its applicable access and licensing terms.

The first pilot export is a 74 by 109 pixel, nine-band GeoTIFF of 0.21 MB, and
all six complete watersheds have full raster coverage. Mean annual precipitation
ranges from approximately 1,388 to 1,424 mm, mean wet-day counts from 218 to 220,
and mean heavy-rain-day counts from 38.5 to 41.0. The narrow between-site range
is consistent with the coarse effective resolution and confirms that this layer
should provide temporal and regional context rather than fine local separation.

## Storm-overflow exposure

The wastewater contract uses the Environment Agency's 2024 Event Duration
Monitoring Storm Overflow Annual Return. It normalizes all water-company sheets,
converts outlet OS National Grid references to British National Grid point
geometry, and retains spill count, total spill duration and monitor-operational
coverage. Each complete site watershed receives counts of intersecting outlets,
monitored outlets, reported spills and spill hours, plus mean EDM coverage and a
count of outlets below 90% coverage.

These company-reported regulatory returns describe storm-overflow activity. They
do not represent continuous treated-effluent discharges, dry-weather flow,
pollutant concentration, receiving-water dilution or ecological impact. A spill
count also does not encode volume. Results must therefore be described as an
upstream exposure indicator, with low monitor coverage visible, and not as a
wastewater load. The 2024 annual return is published by the Environment Agency
under the Open Government Licence.

The first national extraction produced 14,251 outlets with valid British
National Grid references across all ten reporting companies. Identifier and
range checks found no duplicate overflow IDs, invalid geometries, negative spill
values or monitor coverage outside 0–100%. Of the six complete pilot watersheds,
four small upland watersheds contain no EDM outlet. The two larger downstream
watersheds contain five and nine outlets, with 206 and 384 reported spills and
approximately 1,909 and 2,434 total spill hours respectively. Because these
watersheds are nested, their totals are cumulative rather than independent.

## Consolidated site feature contract

The model-facing upstream table has exactly one row per monitoring site with a
complete watershed. It combines watershed diagnostics, scale-safe land-cover
means and standard deviations, raster coverage fractions, rainfall and wetness
context, and storm-overflow exposure. Raster sums are deliberately excluded:
they depend on processing resolution and pixel count and could be mistaken for
physical loads. Site membership must match exactly across every input table, and
duplicate or null site identifiers fail the build.
Mean EDM coverage remains null when no monitored overflow exists; an explicit
coverage-available flag distinguishes this structurally inapplicable value from
missing source data.

A separate site × season × determinand table aggregates monitoring outcomes only
for those complete watersheds and attaches the consolidated predictors. This is
kept separate from the established cell-level feature table, because joining
site-specific contributing areas after cell aggregation would create ambiguous
many-to-many relationships. The new table is exploratory and cannot be used to
revise or re-evaluate the frozen baseline on Wyre or Thames; a new untouched
catchment is required for external evaluation of any redesigned model.

The first pilot and development consolidations passed schema and key checks, but
a later hydrologic concordance audit showed that the nominal 90 m routing export
had resampled the categorical D8 grid. Some traced polygon areas were less than
one percent of MERIT's upstream area at the same outlet. All polygon-derived
land-cover, climate and EDM features from that export are superseded and must not
be modelled. The native-grid rebuild adds `upg` and requires traced pixel count
to agree within 1% before a site is considered complete.

The configured-area orchestration command, `earth-risk run-upstream-area
AREA_ID`, now reproduces all upstream stages with deterministic paths and emits a
JSON summary containing the study-area role, active sites, complete and truncated
watersheds, monitoring rows and readiness result. The companion Colab notebook
runs this pipeline for the Lune and Ribble development areas so Earth Engine and
data-extraction workloads remain off the local computer.

Raster aggregation uses all pixels touched by a watershed boundary. This avoids
undefined climate summaries for polygons smaller than the 1 km export grid, but
does not change ERA5-Land's approximately 11.1 km effective information scale.

As an intermediate stage, monitoring sites are assigned to the smallest
intersecting HydroATLAS level-12 basin. The staged table retains topology,
sub-basin and total upstream area, plus upstream climate, land-cover, soil,
erosion, population and road attributes. Source column names and values remain
unchanged until the HydroATLAS scaling factors are independently audited.

The first assignment run mapped all 1,714 configured sampling sites without
nulls, but only 45 distinct level-12 basins were represented. Active monitored
sites occupy 8 basins in Lune, 11 in Ribble, 4 in Wyre and 14 in Thames and
Chilterns South. Some outlet-level upstream areas substantially exceed the local
MERIT upstream-area value near a site. These findings confirm that HydroATLAS is
a coarse upstream-pressure proxy and topology scaffold, not a precise site
watershed. A later operational method must snap sites to the river network and
delineate from a nationally appropriate flow-direction surface.

HydroBASINS provides explicit hierarchical topology and is suitable for an
initial reproducible network prototype. MERIT Hydro provides finer approximately
90 m flow direction and upstream-area context. Neither should be presented as an
authoritative Environment Agency operational catchment delineation. Licensing
and attribution must be reviewed before public or Defra-facing redistribution.

The first cloud run produced complete hydrologic-context rows for all 1,416
configured grid cells. Maximum mapped upstream area ranges from 311.9 km² in
Wyre to 6,947.1 km² in Thames and Chilterns South, confirming that the external
replication includes a substantially different river-network scale. These values
are descriptive checks, not new model inputs, because both external catchments
have already been evaluated.
