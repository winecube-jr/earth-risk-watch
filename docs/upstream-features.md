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
