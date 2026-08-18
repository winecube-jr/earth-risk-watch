# Sentinel-2 seasonal baseline

## Purpose

The seasonal baseline confirms that the cloud pipeline can generate bounded,
interpretable Earth-observation features over an official catchment geometry.
It is not yet an environmental quality or intervention model.

## Processing

- Collection: Sentinel-2 Level-2A harmonized surface reflectance.
- Period: calendar year 2024, split into configured seasonal windows.
- Scene filter: at most 60% scene-level cloud cover.
- Pixel mask: Sentinel SCL classes for cloud shadow, cloud, cirrus, and snow.
- Composite: median of remaining observations.
- Summary scale: 100 m for low-cost pilot diagnostics.
- Metrics: mean, standard deviation, and 10th, 50th, and 90th percentiles.
- Indices: NDVI, NDMI, MNDWI, and BSI.

## Interpretation guardrails

- Seasonal differences can reflect observation availability and residual cloud,
  not only environmental change.
- Catchment averages hide local hotspots and land-cover composition.
- MNDWI and other spectral indices are proxies, not direct water-quality measurements.
- Bare Soil Index values must be interpreted alongside vegetation and land cover.
- The winter window currently covers January and February; it is not a
  meteorological winter spanning calendar years.
- Results must be compared with field observations before use as risk evidence.

## Next analytical step

Generate spatial grid-cell features and join them to Environment Agency monitoring
outcomes. That supports spatial validation and moves the project from descriptive
remote sensing toward an evidence-tested pressure and condition model.
