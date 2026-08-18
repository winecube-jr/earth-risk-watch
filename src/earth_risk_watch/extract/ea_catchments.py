"""Environment Agency Catchment Data Explorer extraction."""

import csv
import hashlib
import io
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import httpx

from earth_risk_watch.areas import StudyArea, load_study_areas
from earth_risk_watch.catalogue import load_catalogue
from earth_risk_watch.http_client import get_bytes, open_data_client


def fetch_pilot_classifications(client: httpx.Client | None = None) -> bytes:
    """Fetch and minimally validate pilot water-body classifications."""
    source = load_catalogue().by_id("ea-catchment-api")
    if client is not None:
        payload = get_bytes(client, source.endpoint)
    else:
        with open_data_client() as managed_client:
            payload = get_bytes(managed_client, source.endpoint)
    rows = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    if rows.fieldnames is None or not rows.fieldnames:
        raise ValueError("Expected a CSV response with named columns")
    if next(rows, None) is None:
        raise ValueError("Expected at least one classification record")
    return payload


def save_pilot_classifications(output: Path, client: httpx.Client | None = None) -> Path:
    """Atomically save the response and a compact provenance sidecar."""
    body = fetch_pilot_classifications(client)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_bytes(body)
    os.replace(temporary, output)

    provenance = {
        "source_id": "ea-catchment-api",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "sha256": hashlib.sha256(body).hexdigest(),
        "bytes": len(body),
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output


def fetch_pilot_geometry(client: httpx.Client | None = None) -> dict[str, object]:
    """Fetch the official provisional pilot boundary as GeoJSON."""
    endpoint = (
        "https://environment.data.gov.uk/catchment-planning/OperationalCatchment/3290.geojson"
    )
    if client is not None:
        payload = get_bytes(client, endpoint)
    else:
        with open_data_client() as managed_client:
            payload = get_bytes(managed_client, endpoint)
    parsed = json.loads(payload)
    if not isinstance(parsed, dict) or parsed.get("type") not in {
        "Feature",
        "FeatureCollection",
    }:
        raise ValueError("Expected a GeoJSON Feature or FeatureCollection")
    return parsed


def save_pilot_geometry(output: Path, client: httpx.Client | None = None) -> Path:
    """Atomically save the official pilot boundary."""
    geometry = fetch_pilot_geometry(client)
    body = (json.dumps(geometry, separators=(",", ":")) + "\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_bytes(body)
    os.replace(temporary, output)
    return output


def fetch_area_file(
    area: StudyArea,
    suffix: str,
    client: httpx.Client | None = None,
    *,
    max_bytes: int = 25_000_000,
) -> bytes:
    """Fetch a bounded file for any configured CDE study area."""
    endpoint = f"{area.base_endpoint}{suffix}"
    if client is not None:
        return get_bytes(client, endpoint, max_bytes=max_bytes)
    with open_data_client(timeout_seconds=90) as managed_client:
        return get_bytes(managed_client, endpoint, max_bytes=max_bytes)


def save_study_area(
    area_id: str,
    output_dir: Path,
    client: httpx.Client | None = None,
) -> tuple[Path, Path]:
    """Save official geometry and classifications for a configured study area."""
    area = load_study_areas().by_id(area_id)
    geometry_body = fetch_area_file(area, ".geojson", client)
    geometry = json.loads(geometry_body)
    if not isinstance(geometry, dict) or geometry.get("type") not in {
        "Feature",
        "FeatureCollection",
    }:
        raise ValueError("Expected a GeoJSON Feature or FeatureCollection")
    classifications = fetch_area_file(area, "/classifications.csv", client)
    rows = csv.DictReader(io.StringIO(classifications.decode("utf-8-sig")))
    if not rows.fieldnames or next(rows, None) is None:
        raise ValueError("Expected classification CSV records")
    output_dir.mkdir(parents=True, exist_ok=True)
    geometry_path = output_dir / f"{area.id}.geojson"
    classifications_path = output_dir / f"{area.id}-classifications.csv"
    geometry_path.write_bytes((json.dumps(geometry, separators=(",", ":")) + "\n").encode())
    classifications_path.write_bytes(classifications)
    provenance = {
        "study_area": area.model_dump(),
        "geometry_sha256": hashlib.sha256(geometry_path.read_bytes()).hexdigest(),
        "classifications_sha256": hashlib.sha256(classifications).hexdigest(),
    }
    (output_dir / f"{area.id}.provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return geometry_path, classifications_path
