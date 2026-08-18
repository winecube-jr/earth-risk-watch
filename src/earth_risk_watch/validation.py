"""Leakage-safe geographic development and validation partitions."""

import hashlib
import json
from pathlib import Path

import pandas as pd

MINIMUM_DEVELOPMENT_CELLS = 30
MINIMUM_EXTERNAL_CELLS = 10
MINIMUM_DETERMINAND_CELLS = 10


def build_geographic_partitions(
    development: dict[str, pd.DataFrame], external: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """Label and combine catchment tables without mixing geographic roles."""
    overlap = set(development) & set(external)
    if overlap:
        raise ValueError(f"Areas cannot have both roles: {', '.join(sorted(overlap))}")
    if not development or not external:
        raise ValueError("At least one development and one external area are required")
    parts = []
    for role, tables in (("development", development), ("external_validation", external)):
        for area_id, table in tables.items():
            part = table.copy()
            part.insert(0, "area_id", area_id)
            part.insert(1, "partition_role", role)
            parts.append(part)
    combined = pd.concat(parts, ignore_index=True)
    development_cells = set(combined.loc[combined["partition_role"] == "development", "cell_id"])
    external_cells = set(
        combined.loc[combined["partition_role"] == "external_validation", "cell_id"]
    )
    shared_cells = development_cells & external_cells
    if shared_cells:
        raise ValueError(
            f"Grid cells cannot cross partition roles: {', '.join(sorted(shared_cells))}"
        )
    return combined


def partition_readiness(table: pd.DataFrame) -> dict[str, object]:
    """Assess development and untouched external spatial support separately."""
    required = {"area_id", "partition_role", "cell_id", "determinand_code"}
    if not required.issubset(table.columns):
        raise ValueError(f"Partition table is missing columns: {sorted(required - set(table))}")
    development = table.loc[table["partition_role"] == "development"]
    external = table.loc[table["partition_role"] == "external_validation"]
    development_cells = int(development["cell_id"].nunique())
    external_cells = int(external["cell_id"].nunique())
    external_areas = int(external["area_id"].nunique())
    development_by_determinand = {
        str(code): int(group["cell_id"].nunique())
        for code, group in development.groupby("determinand_code")
    }
    external_by_determinand = {
        str(code): int(group["cell_id"].nunique())
        for code, group in external.groupby("determinand_code")
    }
    reasons = []
    if development_cells < MINIMUM_DEVELOPMENT_CELLS:
        reasons.append(
            f"Only {development_cells} development cells; "
            f"at least {MINIMUM_DEVELOPMENT_CELLS} are required"
        )
    if external_cells < MINIMUM_EXTERNAL_CELLS:
        reasons.append(
            f"Only {external_cells} external cells; at least {MINIMUM_EXTERNAL_CELLS} are required"
        )
    if external_areas < 1:
        reasons.append("At least one external catchment is required")
    for label, counts in (
        ("development", development_by_determinand),
        ("external", external_by_determinand),
    ):
        sparse = sorted(code for code, count in counts.items() if count < MINIMUM_DETERMINAND_CELLS)
        if sparse:
            reasons.append(
                f"Fewer than {MINIMUM_DETERMINAND_CELLS} {label} cells for determinands: "
                f"{', '.join(sparse)}"
            )
    return {
        "ready_for_geographic_validation": not reasons,
        "development_cells": development_cells,
        "external_cells": external_cells,
        "external_catchments": external_areas,
        "development_cells_by_determinand": development_by_determinand,
        "external_cells_by_determinand": external_by_determinand,
        "reasons": reasons,
    }


def save_geographic_partitions(
    development_paths: dict[str, Path],
    external_paths: dict[str, Path],
    output: Path,
) -> Path:
    """Save a role-labelled partition table and readiness provenance."""
    table = build_geographic_partitions(
        {area_id: pd.read_parquet(path) for area_id, path in development_paths.items()},
        {area_id: pd.read_parquet(path) for area_id, path in external_paths.items()},
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(output, index=False)
    provenance = {
        "rows": len(table),
        "areas": sorted(table["area_id"].unique().tolist()),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "readiness": partition_readiness(table),
        "warning": "External rows must not be used for feature or model selection.",
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output


def parse_partition_paths(values: list[str]) -> dict[str, Path]:
    """Parse repeatable AREA_ID=PATH command-line specifications."""
    parsed = {}
    for value in values:
        area_id, separator, path = value.partition("=")
        if not separator or not area_id.strip() or not path.strip():
            raise ValueError("Partition inputs must use AREA_ID=PATH")
        if area_id in parsed:
            raise ValueError(f"Duplicate partition area: {area_id}")
        parsed[area_id] = Path(path)
    return parsed
