import io
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, box

from earth_risk_watch.wastewater import (
    build_upstream_edm_features,
    os_grid_reference_to_xy,
    rows_from_edm_workbook,
)


def test_os_grid_reference_to_xy() -> None:
    assert os_grid_reference_to_xy("SP 90370 74740") == (490370.0, 274740.0)
    assert os_grid_reference_to_xy("SJ5049211756") == (350492.0, 311756.0)
    assert os_grid_reference_to_xy("Unpermitted") is None
    assert os_grid_reference_to_xy("SP123") is None


def test_rows_from_edm_workbook_normalizes_company_sheet() -> None:
    source = pd.DataFrame(
        {
            "Unique ID": ["OVERFLOW-1"],
            "Water Company Name": ["Example Water"],
            "Site Name\n(EA Consents Database)": ["Example CSO"],
            "EA Permit Reference\n(EA Consents Database)": ["PERMIT-1"],
            "Storm Discharge Asset Type": ["SO on sewer network"],
            "Outlet Discharge NGR\n(EA Consents Database)": ["SP9037074740"],
            "Total Duration (hh:mm:ss) all spills": ["1 day, 02:30:00"],
            "Counted spills using 12-24h count method": [7],
            "EDM Operation -\n% of reporting period EDM operational": [99.5],
        }
    )
    workbook = io.BytesIO()
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        source.to_excel(writer, sheet_name="Example 2024", startrow=1, index=False)

    result = rows_from_edm_workbook(workbook.getvalue())

    assert result.loc[0, "overflow_id"] == "OVERFLOW-1"
    assert result.loc[0, "spill_duration_hours_2024"] == pytest.approx(26.5)
    assert result.loc[0, "spill_count_2024"] == 7
    assert result.geometry.iloc[0] == Point(490370, 274740)


def test_build_upstream_edm_features_includes_zero_exposure(tmp_path: Path) -> None:
    watersheds_path = tmp_path / "watersheds.geojson"
    gpd.GeoDataFrame(
        {
            "point_notation": ["site-1", "site-2"],
            "geometry": [box(0, 0, 10, 10), box(20, 20, 30, 30)],
        },
        crs="EPSG:27700",
    ).to_file(watersheds_path, driver="GeoJSON")
    edm_path = tmp_path / "edm.parquet"
    gpd.GeoDataFrame(
        {
            "overflow_id": ["a", "b"],
            "spill_count_2024": [3.0, 5.0],
            "spill_duration_hours_2024": [4.0, 6.0],
            "edm_coverage_percent_2024": [99.0, 80.0],
            "geometry": [Point(2, 2), Point(4, 4)],
        },
        crs="EPSG:27700",
    ).to_parquet(edm_path, index=False)

    result = build_upstream_edm_features(watersheds_path, edm_path).set_index("point_notation")

    assert result.loc["site-1", "upstream_overflow_count"] == 2
    assert result.loc["site-1", "upstream_spill_count_2024"] == 8
    assert result.loc["site-1", "upstream_spill_duration_hours_2024"] == 10
    assert result.loc["site-1", "upstream_low_coverage_overflow_count_2024"] == 1
    assert result.loc["site-2", "upstream_overflow_count"] == 0
    assert result.loc["site-2", "upstream_spill_count_2024"] == 0
