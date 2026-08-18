"""Environment Agency storm-overflow extraction and upstream summaries."""

import hashlib
import io
import json
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

from earth_risk_watch.http_client import get_bytes, open_data_client

EDM_2024_URL = (
    "https://environment.data.gov.uk/api/file/download?"
    "fileDataSetId=c55e170e-3c75-49a5-8026-a961ff94c8e0&"
    "fileName=EDM_2024_Storm_Overflow_Annual_Return.zip"
)


def os_grid_reference_to_xy(reference: object) -> tuple[float, float] | None:
    """Convert a two-letter OS National Grid reference to BNG coordinates."""
    compact = re.sub(r"\s+", "", str(reference).upper())
    match = re.fullmatch(r"([A-HJ-Z]{2})(\d{2,10})", compact)
    if match is None or len(match.group(2)) % 2:
        return None
    first, second = (ord(letter) - ord("A") for letter in match.group(1))
    if first > 7:
        first -= 1
    if second > 7:
        second -= 1
    easting_100km = ((first - 2) % 5) * 5 + second % 5
    northing_100km = 19 - (first // 5) * 5 - second // 5
    if not (0 <= easting_100km <= 6 and 0 <= northing_100km <= 12):
        return None
    digits = match.group(2)
    half = len(digits) // 2
    easting = int(digits[:half].ljust(5, "0")) + easting_100km * 100_000
    northing = int(digits[half:].ljust(5, "0")) + northing_100km * 100_000
    return float(easting), float(northing)


def _normalized_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [re.sub(r"\s+", " ", str(column)).strip() for column in frame.columns]
    return frame


def _column(frame: pd.DataFrame, prefix: str) -> str:
    matches = [column for column in frame if column.startswith(prefix)]
    if len(matches) != 1:
        raise ValueError(f"Expected one EDM column starting with {prefix!r}; found {matches}")
    return str(matches[0])


def rows_from_edm_workbook(workbook: bytes) -> gpd.GeoDataFrame:
    """Normalize all company sheets in the official 2024 EDM workbook."""
    sheets = pd.read_excel(io.BytesIO(workbook), sheet_name=None, header=1)
    records: list[pd.DataFrame] = []
    for sheet_name, raw in sheets.items():
        frame = _normalized_columns(raw)
        duration_column = _column(frame, "Total Duration")
        reporting_matches = [
            column
            for column in frame
            if column.startswith("EDM Operation") and "reporting period EDM operational" in column
        ]
        if len(reporting_matches) != 1:
            raise ValueError(f"Expected one EDM reporting column in {sheet_name!r}")
        normalized = pd.DataFrame(
            {
                "overflow_id": frame[_column(frame, "Unique ID")],
                "water_company": frame[_column(frame, "Water Company Name")],
                "site_name": frame[_column(frame, "Site Name (EA Consents Database)")],
                "permit_reference": frame[_column(frame, "EA Permit Reference")],
                "asset_type": frame[_column(frame, "Storm Discharge Asset Type")],
                "outlet_grid_reference": frame[_column(frame, "Outlet Discharge NGR")],
                "spill_count_2024": pd.to_numeric(
                    frame[_column(frame, "Counted spills using")], errors="coerce"
                ),
                "spill_duration_hours_2024": pd.to_timedelta(
                    frame[duration_column], errors="coerce"
                ).dt.total_seconds()
                / 3_600,
                "edm_coverage_percent_2024": pd.to_numeric(
                    frame[reporting_matches[0]], errors="coerce"
                ),
            }
        )
        text_columns = [
            "overflow_id",
            "water_company",
            "site_name",
            "permit_reference",
            "asset_type",
            "outlet_grid_reference",
        ]
        normalized[text_columns] = normalized[text_columns].astype("string")
        records.append(normalized)
    combined = pd.concat(records, ignore_index=True)
    coordinates = combined["outlet_grid_reference"].map(os_grid_reference_to_xy)
    valid = coordinates.notna() & combined["overflow_id"].notna()
    combined = combined.loc[valid].copy()
    xy = coordinates.loc[valid]
    geometry = gpd.points_from_xy(
        [coordinate[0] for coordinate in xy],
        [coordinate[1] for coordinate in xy],
        crs="EPSG:27700",
    )
    result = gpd.GeoDataFrame(combined, geometry=geometry, crs="EPSG:27700")
    return result.sort_values("overflow_id").reset_index(drop=True)


def extract_edm_2024(output: Path) -> Path:  # pragma: no cover
    """Download and normalize the official 2024 national annual return."""
    with open_data_client(timeout_seconds=180) as client:
        archive = get_bytes(client, EDM_2024_URL, max_bytes=10_000_000)
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        workbook_names = [
            name
            for name in bundle.namelist()
            if name.endswith("all water and sewerage companies.xlsx")
        ]
        if len(workbook_names) != 1:
            raise ValueError("EDM archive does not contain one national company workbook")
        workbook = bundle.read(workbook_names[0])
    frame = rows_from_edm_workbook(workbook)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    provenance: dict[str, Any] = {
        "created_at": datetime.now(UTC).isoformat(),
        "source": EDM_2024_URL,
        "publisher": "Environment Agency",
        "reporting_year": 2024,
        "rows_with_valid_grid_reference": len(frame),
        "water_companies": int(frame["water_company"].nunique()),
        "licence": "Open Government Licence 3.0",
        "archive_sha256": hashlib.sha256(archive).hexdigest(),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "warning": "Company-reported storm-overflow activity; not treatment load or impact.",
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output


def build_upstream_edm_features(watersheds_path: Path, edm_path: Path) -> pd.DataFrame:
    """Summarize 2024 storm-overflow activity inside each complete watershed."""
    watersheds = gpd.read_file(watersheds_path)
    edm = gpd.read_parquet(edm_path).to_crs(watersheds.crs)
    records = []
    for watershed in watersheds.itertuples(index=False):
        upstream = edm.loc[edm.geometry.intersects(watershed.geometry)]
        monitored = upstream.loc[
            upstream["spill_count_2024"].notna() & upstream["spill_duration_hours_2024"].notna()
        ]
        records.append(
            {
                "point_notation": watershed.point_notation,
                "upstream_overflow_count": len(upstream),
                "upstream_monitored_overflow_count": len(monitored),
                "upstream_spill_count_2024": float(monitored["spill_count_2024"].sum()),
                "upstream_spill_duration_hours_2024": float(
                    monitored["spill_duration_hours_2024"].sum()
                ),
                "upstream_mean_edm_coverage_percent_2024": float(
                    monitored["edm_coverage_percent_2024"].mean()
                )
                if len(monitored)
                else float("nan"),
                "upstream_edm_coverage_available_2024": bool(len(monitored)),
                "upstream_low_coverage_overflow_count_2024": int(
                    (monitored["edm_coverage_percent_2024"] < 90).sum()
                ),
            }
        )
    return pd.DataFrame(records).sort_values("point_notation").reset_index(drop=True)


def save_upstream_edm_features(watersheds_path: Path, edm_path: Path, output: Path) -> Path:
    """Save watershed-level storm-overflow activity with provenance."""
    frame = build_upstream_edm_features(watersheds_path, edm_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    provenance = {
        "created_at": datetime.now(UTC).isoformat(),
        "grain": "point_notation",
        "reporting_year": 2024,
        "watersheds_sha256": hashlib.sha256(watersheds_path.read_bytes()).hexdigest(),
        "edm_sha256": hashlib.sha256(edm_path.read_bytes()).hexdigest(),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "assignment": "EDM outlet intersects complete D8 watershed polygon",
        "warning": "Exposure proxy only; counts and duration do not quantify pollutant load.",
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output
