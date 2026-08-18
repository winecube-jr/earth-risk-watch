# Upstream-pressure feature design

The first hydrology layer uses MERIT Hydro in Earth Engine to summarize upstream
drainage area, height above drainage, river width and permanent-water fraction
for every 2 km cell at a common 90 m processing scale. These variables provide
network and floodplain context but are not themselves upstream pollution loads.
Masked MERIT pixels are explicitly filled with zero before aggregation; for
river width and permanent water this represents absence of a mapped feature at
that pixel. Coverage validation still rejects null cell-level outputs.

The next contract will snap each monitoring location to a drainage network,
delineate or select its upstream contributing sub-basins, and aggregate pressure
variables only within that contributing area. Candidate pressure inputs include
land cover, rainfall and antecedent wetness, wastewater assets, urban impermeable
surface, agricultural proxies, soils and geology. Every resulting field must
record its source year, spatial support, aggregation rule and missing coverage.

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
