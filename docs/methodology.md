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

The first Lune run traced all 33 active monitoring locations. Nine watersheds
touched the unbuffered raster boundary; none touched the 20 km buffered boundary.
The buffered 1,234 by 1,570 pixel two-band routing raster is 3.1 MB, making the
approach practical for bounded cloud exports and ephemeral workers.
