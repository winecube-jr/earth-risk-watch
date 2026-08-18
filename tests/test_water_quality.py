from pathlib import Path

import geopandas as gpd
import httpx
import pytest
import respx
from shapely.geometry import box

from earth_risk_watch.extract.water_quality import (
    fetch_observations,
    fetch_sampling_points,
    observations_frame,
    polygon_from_geojson,
    sampling_points_frame,
)

ENDPOINT = "https://environment.data.gov.uk/water-quality/data/sampling-point"


def test_polygon_from_geojson(tmp_path: Path) -> None:
    path = tmp_path / "area.geojson"
    gpd.GeoDataFrame(
        {"name": ["area"]}, geometry=[box(-2.8, 53.9, -2.6, 54.1)], crs="EPSG:4326"
    ).to_file(path, driver="GeoJSON")
    geometry = polygon_from_geojson(path)
    assert geometry["type"] == "Polygon"


@respx.mock
def test_fetch_sampling_points_paginates() -> None:
    first = {"member": [{"properties": {"notation": "one"}}]}
    second = {"member": []}
    route = respx.post(ENDPOINT).mock(
        side_effect=[httpx.Response(200, json=first), httpx.Response(200, json=second)]
    )
    with httpx.Client() as client:
        result = fetch_sampling_points({"type": "Polygon", "coordinates": []}, client, page_size=1)
    assert len(result) == 1
    assert route.call_count == 2


def test_fetch_sampling_points_rejects_page_size() -> None:
    with pytest.raises(ValueError, match="between 1 and 250"):
        fetch_sampling_points({"type": "Polygon", "coordinates": []}, page_size=251)


def test_sampling_points_frame() -> None:
    members = [
        {
            "notation": "NW-1",
            "prefLabel": "River site",
            "geometry": {
                "asWKT": "POINT(360000 460000) <http://www.opengis.net/def/crs/EPSG/0/27700>"
            },
            "samplingPointStatus": {"prefLabel": "OPEN"},
            "samplingPointType": {"prefLabel": "RIVER"},
            "region": {"prefLabel": "NorthWest"},
            "area": {"prefLabel": "Area"},
            "subArea": {"prefLabel": "Subarea"},
        }
    ]
    frame = sampling_points_frame(members)
    assert frame.loc[0, "notation"] == "NW-1"
    assert frame.loc[0, "status"] == "OPEN"
    assert frame.crs is not None and frame.crs.to_epsg() == 4326


@respx.mock
def test_fetch_observations_paginates() -> None:
    route = respx.post(ENDPOINT.replace("sampling-point", "observation")).mock(
        side_effect=[
            httpx.Response(200, json={"member": [{"id": "one"}]}),
            httpx.Response(200, json={"member": []}),
        ]
    )
    with httpx.Client() as client:
        result = fetch_observations(["NW-1"], client, page_size=1)
    assert len(result) == 1
    assert route.call_count == 2


def test_fetch_observations_rejects_too_many_points() -> None:
    with pytest.raises(ValueError, match="between 1 and 100"):
        fetch_observations([])


def test_observations_frame() -> None:
    frame = observations_frame(
        [
            {
                "id": "observation-1",
                "hasSamplingPoint": {"notation": "NW-1", "prefLabel": "River"},
                "phenomenonTime": "2024-04-01T12:00:00",
                "hasUnit": "mg/l",
                "hasSimpleResult": "<5",
                "hasResult": {"numericValue": None, "upperBound": 5, "lowerBound": None},
                "observedProperty": {"notation": "0117", "prefLabel": "Nitrate as N"},
                "hasSample": {
                    "sampleMaterialType": {"prefLabel": "RIVER WATER"},
                    "isResultOf": {"samplingPurpose": {"prefLabel": "MONITORING"}},
                },
            }
        ]
    )
    assert frame.loc[0, "point_notation"] == "NW-1"
    assert frame.loc[0, "determinand_code"] == "0117"
    assert frame.loc[0, "reported_result"] == "<5"
    assert bool(frame.loc[0, "is_censored"])
    assert frame.loc[0, "analysis_value"] == 2.5
