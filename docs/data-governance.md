# Data governance

## Rules

- Record publisher, licence, retrieval time, query, version, and checksum.
- Preserve source identifiers so results can be traced back to observations.
- Do not redistribute source data unless its licence explicitly permits it.
- Store no personal data; use appropriately aggregated population statistics.
- Do not commit credentials, raw national datasets, or generated binary rasters.
- Treat automated intervention recommendations as decision support, not decisions.
- Publish missingness and spatial bias alongside model results.

## Provenance manifest

Each product will receive a JSON manifest containing its configuration hash,
source versions, code revision, processing time, CRS, resolution, area, model
version, validation summary, licence notes, and known limitations.
