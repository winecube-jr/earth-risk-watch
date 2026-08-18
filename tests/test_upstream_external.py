import pandas as pd
import pytest
from model_fixtures import model_rows, ridge_report

from earth_risk_watch.upstream_external import evaluate_upstream_external_holdout
from earth_risk_watch.upstream_robust import evaluate_robust_upstream_development


def test_external_evaluation_uses_only_frozen_selection() -> None:
    development = pd.concat([model_rows("lune"), model_rows("ribble")], ignore_index=True)
    _, _, fitted = evaluate_robust_upstream_development(
        development, ridge_report(), bootstrap_draws=100, n_estimators=10
    )
    holdout = model_rows("derwent").assign(topology_consistent=True, touches_raster_boundary=False)
    selection = {
        "external_holdout": {"area_id": "derwent"},
        "selected_models": {"0117": "random_forest"},
    }
    predictions, report = evaluate_upstream_external_holdout(
        holdout,
        development,
        fitted,
        selection,
        area_id="derwent",
        bootstrap_draws=100,
    )
    assert set(predictions["determinand_code"]) == {"0117"}
    assert report["evaluation"] == "one-shot untouched external holdout"
    assert "predictor_outside_training_range_fraction" in report["determinand_results"]["0117"]


def test_external_evaluation_rejects_wrong_area() -> None:
    selection = {
        "external_holdout": {"area_id": "derwent"},
        "selected_models": {"0117": "random_forest"},
    }
    with pytest.raises(ValueError, match="frozen external holdout"):
        evaluate_upstream_external_holdout(
            pd.DataFrame(), {}, {}, selection, area_id="other", bootstrap_draws=100
        )
