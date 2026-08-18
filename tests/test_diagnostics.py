import pandas as pd
import pytest

from earth_risk_watch.diagnostics import (
    evaluation_diagnostics,
    evaluation_rows,
    grouped_bootstrap_intervals,
)


def fixtures() -> tuple[pd.DataFrame, pd.DataFrame]:
    predictions = pd.DataFrame(
        {
            "area_id": ["external"] * 4,
            "cell_id": ["a", "a", "b", "b"],
            "season": ["spring", "summer"] * 2,
            "determinand_code": ["0117"] * 4,
            "observed": [1.0, 2.0, 3.0, 4.0],
            "predicted": [1.2, 2.2, 2.8, 3.8],
            "development_median_baseline": [2.0] * 4,
        }
    )
    partitions = predictions[["area_id", "cell_id", "season", "determinand_code"]].copy()
    partitions["partition_role"] = "external_validation"
    partitions["observation_count"] = [2, 2, 3, 3]
    partitions["site_count"] = 1
    partitions["censored_fraction"] = [0.0, 0.5, 0.0, 0.5]
    return predictions, partitions


def test_evaluation_diagnostics_is_cell_grouped_and_deterministic() -> None:
    predictions, partitions = fixtures()
    first = evaluation_diagnostics(predictions, partitions, draws=100, seed=7)
    assert first == evaluation_diagnostics(predictions, partitions, draws=100, seed=7)
    result = first["determinand_diagnostics"]["0117"]
    assert result["overall"]["cells"] == 2
    assert set(result["by_season"]) == {"spring", "summer"}
    assert set(result["by_censoring"]) == {"contains_censored_results", "uncensored"}


def test_evaluation_rows_rejects_duplicate_keys() -> None:
    predictions, partitions = fixtures()
    with pytest.raises(ValueError, match="unique"):
        evaluation_rows(pd.concat([predictions, predictions]), partitions)


def test_grouped_bootstrap_validates_support() -> None:
    predictions, partitions = fixtures()
    rows = evaluation_rows(predictions, partitions)
    with pytest.raises(ValueError, match="100"):
        grouped_bootstrap_intervals(rows, draws=10)
    with pytest.raises(ValueError, match="two cells"):
        grouped_bootstrap_intervals(rows.loc[rows["cell_id"] == "a"], draws=100)
