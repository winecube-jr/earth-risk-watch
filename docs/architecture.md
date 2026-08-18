# Architecture

## Design decision

Earth Risk Watch uses a federated, cloud-first architecture. Source data remain
with public publishers. Google Earth Engine performs large Earth-observation
aggregations. Short-lived Python workers process catchment-sized external data,
and only derived features, models, provenance, and published products persist.

## Logical flow

1. **Catalogue** — source identity, owner, licence, access method, coverage, and version.
2. **Extract** — bounded queries by area, date, and tile; no unbounded national downloads.
3. **Stage** — validate schema, CRS, units, temporal coverage, and missingness.
4. **Features** — create observable pressure, condition, exposure, and connectivity variables.
5. **Models** — fit interpretable baselines before more complex spatial models.
6. **Evaluate** — spatially separated validation, calibration, uncertainty, and sensitivity.
7. **Scenarios** — estimate intervention benefits under explicit assumptions.
8. **Publish** — compact web layers, evidence cards, model cards, and provenance manifests.

The first implemented vertical slice is a bounded Environment Agency provisional
pilot classifications extraction. It validates HTTP status, CSV shape, and
response size, writes atomically, and records retrieval time, byte count, source
identity, and SHA-256 checksum.

## Spatial scales

- National screening: 100 m or catchment summaries.
- Pilot analysis: 10–25 m.
- LiDAR terrain analysis: 1 m only within selected sub-catchments.

The pipeline must never imply that a coarse national screen has property-level accuracy.

## Deployment boundary

- Earth Engine: satellite collections and scalable raster aggregation.
- Colab: exploration and manually initiated pilot runs.
- GitHub Actions: testing, data-contract checks, documentation, and small scheduled jobs.
- GitHub Pages: static public demonstrator.
- Publisher endpoints: system of record for raw open data.
