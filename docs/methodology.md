# Methodology contract

Earth Risk Watch separates four concepts that are often incorrectly combined:

- **Condition:** an observed environmental state.
- **Pressure:** a plausible source or process affecting that state.
- **Vulnerability:** sensitivity to current or future disturbance.
- **Opportunity:** the expected benefit and feasibility of an intervention.

## Minimum modelling standard

Every published model must include:

- a named outcome and decision use;
- temporal and spatial applicability;
- a simple baseline comparison;
- spatially separated cross-validation;
- calibration and error metrics appropriate to the outcome;
- uncertainty or confidence information;
- sensitivity to subjective weights and thresholds;
- leakage checks;
- known data gaps and prohibited interpretations;
- a reproducible model and data provenance record.

A weighted index may support exploration, but it must not be described as a
validated risk prediction unless it has been tested against an observed outcome.
# Watershed delineation method

Monitoring locations are snapped to the maximum MERIT upstream-drainage-area
pixel within a bounded square search window. The configured five-pixel half-width
allows a maximum corner-to-centre movement of 7.07 pixels. Watersheds are then
traced upstream using
the published MERIT D8 direction codes: east `1`, southeast `2`, south `4`,
southwest `8`, west `16`, northwest `32`, north `64`, and northeast `128`.

Routing is tested against synthetic networks before use on real data. Production
delineation must record the original and snapped coordinates, snap distance,
outlet upstream area, raster resolution, boundary truncation and pixel count.
Watersheds touching an extraction boundary are incomplete and must not be used
for pressure aggregation until the raster extent is expanded.
Routing rasters are exported for the supplied geometry's bounding rectangle,
rather than clipping the image to a complex grid union; this avoids excessive
Earth Engine memory use and makes boundary truncation straightforward to test.
The current routing export adds a 20 km buffer, and diagnostics still reject any
watershed that reaches the buffered boundary.

Flow direction is categorical topology, so production routing exports now use
MERIT's native EPSG:4326 three-arc-second affine transform with no resampling.
The export contains `dir`, upstream area (`upa`) and upstream pixel count (`upg`).
For every outlet, the traced pixel count is compared with `upg`; a relative
difference above 1% marks the topology inconsistent and excludes the watershed.

An August 2026 audit found that the earlier nominal 90 m export had resampled
the categorical direction grid. Although all direction values remained valid,
several watershed polygons were far smaller than MERIT's outlet upstream area.
The earlier Lune/Ribble polygon features and their apparent 108-site readiness
result are therefore superseded and prohibited from modelling. Both development
areas must be rebuilt on the native grid and pass pixel-count concordance before
their readiness result is accepted.

The corrected native-grid pilot traced all nine active sites with delineated-to-
MERIT upstream-pixel ratios from 0.9979 to 1.0000. Six traces reached the 20 km
buffer boundary and are therefore correctly excluded; the three non-boundary
traces had exact pixel-count agreement. This live check validates the topology
correction while showing why boundary and concordance checks are both required.
