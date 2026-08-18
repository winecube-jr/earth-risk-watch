import json
from pathlib import Path

import httpx
import respx

from earth_risk_watch.extract.ea_catchments import (
    fetch_pilot_classifications,
    fetch_pilot_geometry,
    save_pilot_classifications,
    save_pilot_geometry,
)

ENDPOINT = (
    "https://environment.data.gov.uk/catchment-planning/"
    "OperationalCatchment/3290/classifications.csv"
)
CSV = b"waterBody,classification\nGB001,good\n"


@respx.mock
def test_fetch_pilot_classifications() -> None:
    respx.get(ENDPOINT).mock(return_value=httpx.Response(200, content=CSV))
    with httpx.Client() as client:
        assert fetch_pilot_classifications(client) == CSV


@respx.mock
def test_save_pilot_classifications_with_provenance(tmp_path: Path) -> None:
    respx.get(ENDPOINT).mock(return_value=httpx.Response(200, content=CSV))
    target = tmp_path / "england.csv"
    with httpx.Client() as client:
        save_pilot_classifications(target, client)
    assert "GB001,good" in target.read_text(encoding="utf-8")
    sidecar = json.loads(target.with_suffix(".csv.provenance.json").read_text(encoding="utf-8"))
    assert sidecar["source_id"] == "ea-catchment-api"
    assert len(sidecar["sha256"]) == 64


@respx.mock
def test_pilot_geometry(tmp_path: Path) -> None:
    endpoint = (
        "https://environment.data.gov.uk/catchment-planning/OperationalCatchment/3290.geojson"
    )
    payload = {"type": "FeatureCollection", "features": []}
    respx.get(endpoint).mock(return_value=httpx.Response(200, json=payload))
    with httpx.Client() as client:
        assert fetch_pilot_geometry(client)["type"] == "FeatureCollection"
        target = save_pilot_geometry(tmp_path / "pilot.geojson", client)
    assert json.loads(target.read_text(encoding="utf-8"))["type"] == "FeatureCollection"
