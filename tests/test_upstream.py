import pytest

from earth_risk_watch.upstream import SOURCE_ATTRIBUTES, rows_from_hydroatlas


def feature(notation: str = "site-1") -> dict[str, object]:
    properties: dict[str, object] = {"notation": notation}
    properties.update({name: index + 1 for index, name in enumerate(SOURCE_ATTRIBUTES)})
    return {"properties": properties}


def test_rows_from_hydroatlas() -> None:
    frame = rows_from_hydroatlas([feature()])
    assert frame.loc[0, "point_notation"] == "site-1"
    assert frame.loc[0, "UP_AREA"] > frame.loc[0, "SUB_AREA"]


@pytest.mark.parametrize(
    ("features", "message"),
    [
        ([], "no upstream"),
        ([feature("same"), feature("same")], "duplicate"),
        ([{"properties": {"notation": "missing"}}], "no complete"),
    ],
)
def test_rows_from_hydroatlas_rejects_invalid_results(
    features: list[dict[str, object]], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        rows_from_hydroatlas(features)
