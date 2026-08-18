import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from earth_risk_watch.evidence import (
    evaluate_nutrient_alignment,
    investigation_shortlist,
    spearman_correlation,
)


def test_spearman_correlation() -> None:
    assert spearman_correlation(pd.Series([1, 2, 3]), pd.Series([10, 20, 30])) == pytest.approx(1)
    with pytest.raises(ValueError, match="at least three"):
        spearman_correlation(pd.Series([1, 2]), pd.Series([1, 2]))


def test_evaluate_nutrient_alignment() -> None:
    cells = [f"cell-{index}" for index in range(6)]
    screen = pd.DataFrame(
        {
            "cell_id": cells,
            "screening_score": range(6),
            "sediment_pressure": range(6),
            "runoff_susceptibility": range(6),
        }
    )
    monitoring = pd.DataFrame(
        {
            "cell_id": cells,
            "season": ["spring"] * 6,
            "determinand_code": ["0117"] * 6,
            "determinand": ["Nitrate as N"] * 6,
            "target_mean": range(6),
            "observation_count": [2] * 6,
        }
    )
    result = evaluate_nutrient_alignment(screen, monitoring, permutations=99)
    assert len(result) == 3
    assert (result["spatial_cells"] == 6).all()
    assert np.allclose(result["spearman_rho"], 1)


def test_investigation_shortlist() -> None:
    screen = gpd.GeoDataFrame(
        {
            "cell_id": ["near", "gap", "unstable"],
            "screening_score": [80.0, 85.0, 90.0],
            "top_quintile_frequency": [0.9, 0.95, 0.5],
            "monitoring_distance_km": [1.0, 6.0, 7.0],
        },
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1), box(2, 0, 3, 1)],
        crs=27700,
    )
    result = investigation_shortlist(screen)
    assert result["cell_id"].tolist() == ["gap", "near"]
    assert result["evidence_gap"].tolist() == [True, False]
