import pandas as pd
import pytest
from model_fixtures import model_rows, ridge_report

from earth_risk_watch.upstream_robust import evaluate_robust_upstream_development


def test_robust_evaluation_adds_applicability_and_advancement() -> None:
    lune = model_rows("lune")
    ribble = model_rows("ribble")
    ribble.loc[ribble["point_notation"] == "ribble-0", "tree_fraction_mean"] = 10_000.0
    ribble.loc[ribble["point_notation"] == "ribble-0", "grass_fraction_mean"] = 10_000.0
    table = pd.concat([lune, ribble], ignore_index=True)
    predictions, report, models = evaluate_robust_upstream_development(
        table, ridge_report(), bootstrap_draws=100, seed=3, n_estimators=10
    )
    assert "outside_applicability_domain" in set(predictions["applicability_status"])
    assert report["determinand_results"]["0117"]["advancement"]["eligible_for_derwent"]
    assert "applicability_support" in models["0117"]


def test_robust_evaluation_requires_two_catchments() -> None:
    with pytest.raises(ValueError, match="exactly two"):
        evaluate_robust_upstream_development(
            model_rows("lune"), ridge_report(), bootstrap_draws=100, n_estimators=10
        )
