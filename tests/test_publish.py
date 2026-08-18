import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

from earth_risk_watch.publish import build_risk_map


def test_build_risk_map(tmp_path: Path) -> None:
    screen = tmp_path / "screen.geojson"
    gpd.GeoDataFrame(
        {
            "cell_id": ["cell-1"],
            "screening_score": [80.0],
            "screening_band": ["high"],
            "sediment_pressure": [70.0],
            "runoff_susceptibility": [80.0],
            "condition_stress": [90.0],
            "top_quintile_frequency": [0.9],
            "weight_sensitivity_std": [2.0],
            "monitoring_distance_km": [1.0],
        },
        geometry=[box(-2.8, 54.0, -2.7, 54.1)],
        crs=4326,
    ).to_file(screen, driver="GeoJSON")
    points = tmp_path / "points.geojson"
    points.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"notation": "site-1", "name": "Site"},
                        "geometry": {"type": "Point", "coordinates": [-2.75, 54.05]},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output = build_risk_map(screen, points, tmp_path / "map.html")
    html = output.read_text(encoding="utf-8")
    assert "Exploratory relative screen" in html
    assert "cell-1" in html
    assert "site-1" in html
