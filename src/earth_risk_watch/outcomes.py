"""Independent Environment Agency outcome preparation."""

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

ECOLOGICAL_ITEM = "Ecological"
STATUS_SCORE = {"Bad": 0, "Poor": 1, "Moderate": 2, "Good": 3, "High": 4}
REQUIRED_SOURCE_COLUMNS = {
    "Water Body ID",
    "Water Body",
    "Easting",
    "Northing",
    "Year",
    "Status",
    "Classification Level",
    "Classification Item",
}


def ecological_outcomes(source: pd.DataFrame, *, latest_only: bool = False) -> pd.DataFrame:
    """Normalize ecological status records without manufacturing observations."""
    missing = sorted(REQUIRED_SOURCE_COLUMNS.difference(source.columns))
    if missing:
        raise ValueError(f"Missing classification columns: {', '.join(missing)}")
    selected = source.loc[
        (source["Classification Level"] == "Ecological, chemical or quantitative status")
        & (source["Classification Item"] == ECOLOGICAL_ITEM)
    ].copy()
    selected["status_score"] = selected["Status"].map(STATUS_SCORE)
    selected = selected.loc[selected["status_score"].notna()]
    if latest_only and not selected.empty:
        selected = selected.loc[
            selected["Year"] == selected.groupby("Water Body ID")["Year"].transform("max")
        ]
    result = selected.rename(
        columns={
            "Water Body ID": "water_body_id",
            "Water Body": "water_body_name",
            "Easting": "easting",
            "Northing": "northing",
            "Year": "year",
            "Status": "status",
        }
    )[
        [
            "water_body_id",
            "water_body_name",
            "easting",
            "northing",
            "year",
            "status",
            "status_score",
        ]
    ]
    return result.sort_values(["water_body_id", "year"]).reset_index(drop=True)


def build_ecological_outcomes(source: Path, output: Path) -> Path:
    """Write normalized historical ecological outcomes and provenance."""
    frame = ecological_outcomes(pd.read_csv(source))
    if frame.empty:
        raise ValueError("No ecological outcomes were found")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    frame.to_parquet(temporary, index=False)
    os.replace(temporary, output)
    provenance = {
        "created_at": datetime.now(UTC).isoformat(),
        "source": str(source),
        "rows": len(frame),
        "water_bodies": int(frame["water_body_id"].nunique()),
        "years": sorted(int(year) for year in frame["year"].unique()),
        "status_mapping": STATUS_SCORE,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "warning": "Ordinal regulatory outcomes; repeated years are not independent samples.",
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output
