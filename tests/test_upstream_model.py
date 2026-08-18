import numpy as np
import pandas as pd
import pytest

from earth_risk_watch.development import PREREGISTERED_PREDICTORS
from earth_risk_watch.upstream_model import evaluate_upstream_development


def model_rows(area: str, sites: int = 6) -> pd.DataFrame:
    rows = []
    for site in range(sites):
        for season_index, season in enumerate(("winter", "summer")):
            row: dict[str, object] = {
                "area_id": area,
                "point_notation": f"{area}-{site}",
                "season": season,
                "determinand_code": "0117",
                "determinand": "Nitrate",
                "unit": "mg/l",
                "target_mean": 0.1 + site + season_index,
            }
            row.update(
                {
                    feature: float(site + season_index + offset + 1)
                    for offset, feature in enumerate(PREREGISTERED_PREDICTORS)
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def test_upstream_evaluation_holds_out_both_catchments() -> None:
    table = pd.concat([model_rows("lune"), model_rows("ribble")], ignore_index=True)
    predictions, report, models = evaluate_upstream_development(table, bootstrap_draws=100, seed=4)
    assert set(predictions["area_id"]) == {"lune", "ribble"}
    assert len(predictions) == len(table)
    assert set(report["determinand_results"]["0117"]["transfers"]) == {"lune", "ribble"}
    assert report["determinand_results"]["0117"]["target_transform"] == "log1p"
    assert models["0117"]["features"][-1] == "season"
    assert np.isfinite(predictions["predicted"]).all()
    transfer = report["determinand_results"]["0117"]["transfers"]["lune"]
    assert "mae_skill_vs_training_median" in transfer["overall"]
    assert "covariate_shift" in transfer


def test_upstream_evaluation_requires_two_catchments() -> None:
    with pytest.raises(ValueError, match="exactly two"):
        evaluate_upstream_development(model_rows("lune"), bootstrap_draws=100)
