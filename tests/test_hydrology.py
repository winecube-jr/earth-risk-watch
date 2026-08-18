import pytest

from earth_risk_watch.hydrology import rows_from_hydrology_earth_engine


def feature(cell_id: str = "cell-1", water: float = 0.25) -> dict[str, object]:
    return {
        "properties": {
            "cell_id": cell_id,
            "upa_mean": 10.0,
            "upa_max": 100.0,
            "hnd_mean": 3.0,
            "hnd_stdDev": 1.0,
            "wth_max": 12.0,
            "wat_mean": water,
        }
    }


def test_rows_from_hydrology_earth_engine() -> None:
    frame = rows_from_hydrology_earth_engine([feature()])
    assert frame.loc[0, "upstream_area_max_km2"] == 100.0
    assert frame.loc[0, "permanent_water_fraction"] == 0.25


@pytest.mark.parametrize(
    ("features", "message"),
    [
        ([], "no hydrology"),
        ([feature("same"), feature("same")], "duplicate"),
        ([{"properties": {"cell_id": "missing"}}], "incomplete"),
        ([feature(water=1.5)], "between zero and one"),
    ],
)
def test_rows_from_hydrology_rejects_invalid_results(
    features: list[dict[str, object]], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        rows_from_hydrology_earth_engine(features)
