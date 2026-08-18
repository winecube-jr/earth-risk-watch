import numpy as np
import pytest

from earth_risk_watch.watershed import delineate_d8, snap_to_maximum_upstream_area


def test_delineate_d8_traces_all_cells_to_outlet() -> None:
    directions = np.array(
        [
            [2, 4, 8],
            [1, 4, 16],
            [1, 0, 16],
        ]
    )
    result = delineate_d8(directions, (2, 1))
    assert result.all()


def test_delineate_d8_excludes_other_drainage() -> None:
    directions = np.array([[1, 0, 16], [64, 64, 64]])
    result = delineate_d8(directions, (0, 1))
    assert result.tolist() == [[True, True, True], [True, True, True]]
    isolated = delineate_d8(np.array([[0, 0], [64, 64]]), (0, 0))
    assert isolated.tolist() == [[True, False], [True, False]]


def test_snap_uses_maximum_area_then_nearest_tie() -> None:
    area = np.array([[1.0, 9.0, 1.0], [9.0, 2.0, 1.0], [1.0, 1.0, 1.0]])
    assert snap_to_maximum_upstream_area(area, 1, 1, radius_pixels=1) == (0, 1)


def test_watershed_inputs_are_validated() -> None:
    with pytest.raises(ValueError, match="two-dimensional"):
        delineate_d8(np.array([1, 2]), (0, 0))
    with pytest.raises(ValueError, match="outside"):
        delineate_d8(np.zeros((2, 2)), (3, 3))
    with pytest.raises(ValueError, match="negative"):
        snap_to_maximum_upstream_area(np.zeros((2, 2)), 0, 0, radius_pixels=-1)
    with pytest.raises(ValueError, match="finite"):
        snap_to_maximum_upstream_area(np.full((2, 2), np.nan), 0, 0)
