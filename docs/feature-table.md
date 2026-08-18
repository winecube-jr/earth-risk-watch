# Pilot satellite feature table

The first model-ready predictor table is generated at:

`data/features/sentinel/pilot-seasonal.parquet`

Generated data are intentionally excluded from Git. The producing code,
configuration, schema, tests, and provenance contract are versioned.

## Grain and key

Each row represents one `cell_id` and `season`. The pair must be unique.
The current pilot contains 98 clipped 2 km cells and four seasonal windows,
giving 392 rows.

## Columns

- `cell_id`: stable British National Grid-derived identifier.
- `season`, `start_date`, `end_date`: temporal identity.
- `coverage`: fraction of the full square inside the catchment.
- `area_m2`: clipped cell area.
- `scene_count`: source scenes passing the scene-level cloud filter.
- `NDVI_mean`, `NDVI_stdDev`: vegetation condition and within-cell variation.
- `NDMI_mean`, `NDMI_stdDev`: vegetation/canopy moisture proxy.
- `MNDWI_mean`, `MNDWI_stdDev`: open-water and surface wetness proxy.
- `BSI_mean`, `BSI_stdDev`: bare-soil spectral proxy.

## Quality contract

The pipeline rejects missing required columns, empty tables, absent cell IDs,
duplicate cell-season keys, and invalid grid-coverage values. Every output has a
sidecar containing its creation time, Earth Engine project, dimensions, seasons,
SHA-256 checksum, and interpretation warning.

## Modelling limitations

This table contains predictors only. It does not contain a target variable and
cannot yet support claims about environmental risk. The next stage must join
independent Environment Agency water-condition observations using a defensible
spatial and temporal relationship, followed by spatially separated validation.
