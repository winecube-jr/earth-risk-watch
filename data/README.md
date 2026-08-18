# Data directory

This repository does not version large or third-party data.

- `raw/`: temporary, immutable source subsets
- `staged/`: standardized source subsets
- `features/`: model-ready derived variables
- `models/`: fitted artifacts and model cards
- `products/`: maps, tables, evidence cards, and provenance manifests

All generated directories are ignored by Git. Small synthetic fixtures belong
under `tests/fixtures/`, not here.
