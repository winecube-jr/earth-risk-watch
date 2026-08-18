"""Client for the current Environment Agency Water Quality Explorer API."""

import hashlib
import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import httpx
import pandas as pd
from shapely import from_wkt
from shapely.geometry import mapping

from earth_risk_watch.catalogue import load_catalogue
from earth_risk_watch.http_client import open_data_client

CORE_DETERMINANDS = ("0061", "0076", "0068", "0111", "0117", "0180")


def polygon_from_geojson(path: Path) -> dict[str, Any]:
    """Dissolve polygonal features into one API-compatible geometry."""
    frame = gpd.read_file(path).to_crs("EPSG:4326")
    polygons = frame.loc[frame.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
    if polygons.empty:
        raise ValueError("GeoJSON contains no polygonal features")
    return dict(mapping(polygons.geometry.union_all()))


def fetch_sampling_points(
    geometry: dict[str, Any],
    client: httpx.Client | None = None,
    *,
    page_size: int = 250,
) -> list[dict[str, Any]]:
    """Retrieve every sampling point within a polygon using bounded pages."""
    if not 1 <= page_size <= 250:
        raise ValueError("page_size must be between 1 and 250")
    endpoint = load_catalogue().by_id("ea-water-quality").endpoint

    def retrieve(active_client: httpx.Client) -> list[dict[str, Any]]:
        members: list[dict[str, Any]] = []
        skip = 0
        while True:
            response = active_client.post(
                endpoint,
                params={"skip": skip, "limit": page_size},
                json=geometry,
                headers={"Accept": "application/ld+json"},
            )
            response.raise_for_status()
            payload = response.json()
            page = payload.get("member", [])
            if not isinstance(page, list):
                raise ValueError("Expected a paginated member list")
            members.extend(page)
            if len(page) < page_size:
                break
            skip += page_size
        return members

    if client is not None:
        return retrieve(client)
    with open_data_client() as managed_client:
        return retrieve(managed_client)


def sampling_points_frame(members: list[dict[str, Any]]) -> gpd.GeoDataFrame:
    """Normalize JSON-LD sampling points and their BNG WKT geometries."""
    records: list[dict[str, Any]] = []
    for member in members:
        geometry_value = member.get("geometry", {}).get("asWKT")
        if not isinstance(geometry_value, str):
            continue
        wkt = geometry_value.split(" <", maxsplit=1)[0]
        records.append(
            {
                "notation": member.get("notation"),
                "name": member.get("prefLabel"),
                "status": member.get("samplingPointStatus", {}).get("prefLabel"),
                "point_type": member.get("samplingPointType", {}).get("prefLabel"),
                "region": member.get("region", {}).get("prefLabel"),
                "area": member.get("area", {}).get("prefLabel"),
                "sub_area": member.get("subArea", {}).get("prefLabel"),
                "geometry": from_wkt(wkt),
            }
        )
    if not records:
        raise ValueError("No sampling points contained usable geometries")
    return gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:27700").to_crs("EPSG:4326")


def save_sampling_points(geometry_path: Path, output: Path) -> Path:
    """Save pilot sampling points and a checksum-bearing provenance record."""
    geometry = polygon_from_geojson(geometry_path)
    members = fetch_sampling_points(geometry)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = sampling_points_frame(members)
    frame.to_file(output, driver="GeoJSON")
    body = output.read_bytes()
    provenance = {
        "source_id": "ea-water-quality",
        "sampling_points": len(frame),
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output


def fetch_observations(
    point_notations: list[str],
    client: httpx.Client | None = None,
    *,
    date_from: str = "2024-01-01",
    date_to: str = "2024-12-31",
    determinands: tuple[str, ...] = CORE_DETERMINANDS,
    page_size: int = 250,
) -> list[dict[str, Any]]:
    """Retrieve bounded, paginated observations for at most 100 sampling points."""
    if not point_notations or len(point_notations) > 100:
        raise ValueError("point_notations must contain between 1 and 100 values")
    if not 1 <= page_size <= 250:
        raise ValueError("page_size must be between 1 and 250 for JSON-LD")
    endpoint = (
        load_catalogue()
        .by_id("ea-water-quality")
        .endpoint.replace("/sampling-point", "/observation")
    )
    params: dict[str, str | int] = {
        "pointNotation": ",".join(point_notations),
        "dateFrom": date_from,
        "dateTo": date_to,
        "determinand": ",".join(determinands),
        "limit": page_size,
    }

    def retrieve(active_client: httpx.Client) -> list[dict[str, Any]]:
        members: list[dict[str, Any]] = []
        skip = 0
        while True:
            params["skip"] = skip
            response = active_client.post(
                endpoint,
                params=params,
                json=None,
                headers={"Accept": "application/ld+json"},
            )
            response.raise_for_status()
            page = response.json().get("member", [])
            if not isinstance(page, list):
                raise ValueError("Expected a paginated member list")
            members.extend(page)
            if len(page) < page_size:
                break
            skip += page_size
        return members

    if client is not None:
        return retrieve(client)
    with open_data_client() as managed_client:
        return retrieve(managed_client)


def observations_frame(members: list[dict[str, Any]]) -> pd.DataFrame:
    """Flatten SOSA JSON-LD observations into an analysis-ready table."""
    records = []
    for member in members:
        point = member.get("hasSamplingPoint", {})
        result = member.get("hasResult", {})
        observed = member.get("observedProperty", {})
        sample = member.get("hasSample", {})
        sampling = sample.get("isResultOf", {})
        records.append(
            {
                "observation_id": member.get("id"),
                "point_notation": point.get("notation"),
                "point_name": point.get("prefLabel"),
                "observed_at": member.get("phenomenonTime"),
                "determinand_code": observed.get("notation"),
                "determinand": observed.get("prefLabel"),
                "reported_result": member.get("hasSimpleResult"),
                "value": result.get("numericValue"),
                "lower_bound": result.get("lowerBound"),
                "upper_bound": result.get("upperBound"),
                "unit": member.get("hasUnit"),
                "sample_material": sample.get("sampleMaterialType", {}).get("prefLabel"),
                "sampling_purpose": sampling.get("samplingPurpose", {}).get("prefLabel"),
            }
        )
    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        return frame
    frame["observed_at"] = pd.to_datetime(frame["observed_at"], errors="coerce")
    for column in ("value", "lower_bound", "upper_bound"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["is_censored"] = frame["value"].isna() & (
        frame["lower_bound"].notna() | frame["upper_bound"].notna()
    )
    frame["analysis_value"] = frame["value"]
    upper_censored = frame["value"].isna() & frame["upper_bound"].notna()
    lower_censored = frame["value"].isna() & frame["lower_bound"].notna()
    frame.loc[upper_censored, "analysis_value"] = frame.loc[upper_censored, "upper_bound"] / 2
    frame.loc[lower_censored, "analysis_value"] = frame.loc[lower_censored, "lower_bound"]
    return frame


def save_pilot_observations(sampling_points_path: Path, output: Path) -> Path:
    """Save 2024 core water-quality observations at open river sites."""
    points = gpd.read_file(sampling_points_path)
    selected = points.loc[
        (points["status"] == "OPEN") & (points["point_type"] == "FRESHWATER - RIVERS")
    ]
    notations = selected["notation"].dropna().astype(str).tolist()
    members = fetch_observations(notations)
    frame = observations_frame(members)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    body = output.read_bytes()
    provenance = {
        "source_id": "ea-water-quality",
        "period": {"from": "2024-01-01", "to": "2024-12-31"},
        "site_scope": "open FRESHWATER - RIVERS points within pilot boundary",
        "sampling_points_requested": len(notations),
        "determinand_codes": list(CORE_DETERMINANDS),
        "observations": len(frame),
        "censored_value_rule": (
            "upper-bound results use half the bound; lower-bound results use the bound"
        ),
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    output.with_suffix(output.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return output
