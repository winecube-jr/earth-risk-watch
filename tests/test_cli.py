from pathlib import Path

import httpx
import respx
from typer.testing import CliRunner

from earth_risk_watch.cli import app

runner = CliRunner()


def test_catalogue_list() -> None:
    result = runner.invoke(app, ["catalogue", "list"])
    assert result.exit_code == 0
    assert "ea-national-lidar" in result.stdout


def test_catalogue_show() -> None:
    result = runner.invoke(app, ["catalogue", "show", "sentinel-2-sr"])
    assert result.exit_code == 0
    assert "COPERNICUS/S2_SR_HARMONIZED" in result.stdout


def test_demo(tmp_path: Path) -> None:
    result = runner.invoke(app, ["demo", "--output", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "manifest.json").exists()


def test_doctor_reports_actionable_missing_cloud_setup(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("EARTHENGINE_PROJECT", raising=False)
    monkeypatch.chdir(Path("/tmp"))
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "earth-engine-project" in result.stdout


def test_sentinel_plan() -> None:
    result = runner.invoke(app, ["sentinel-plan"])
    assert result.exit_code == 0
    assert "COPERNICUS/S2_SR_HARMONIZED" in result.stdout
    assert "NDVI" in result.stdout


@respx.mock
def test_extract_ea_pilot(tmp_path: Path) -> None:
    endpoint = (
        "https://environment.data.gov.uk/catchment-planning/"
        "OperationalCatchment/3290/classifications.csv"
    )
    respx.get(endpoint).mock(
        return_value=httpx.Response(200, content=b"waterBody,status\nGB001,good\n")
    )
    output = tmp_path / "england.csv"
    result = runner.invoke(app, ["extract-ea-pilot", "--output", str(output)])
    assert result.exit_code == 0
    assert output.exists()
