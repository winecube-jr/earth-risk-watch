import numpy as np
import pandas as pd

from earth_risk_watch.model import NUMERIC_FEATURES, evaluate_fixed_baseline
from earth_risk_watch.validation import build_geographic_partitions


def model_table(cells: int, prefix: str) -> pd.DataFrame:
    index = np.arange(cells, dtype=float)
    values: dict[str, object] = {
        "cell_id": [f"{prefix}-{value}" for value in range(cells)],
        "season": ["spring"] * cells,
        "determinand_code": ["0117"] * cells,
        "determinand": ["Nitrate"] * cells,
        "unit": ["mg/l"] * cells,
        "target_mean": 1 + index / 10,
    }
    values.update({feature: index + offset for offset, feature in enumerate(NUMERIC_FEATURES)})
    return pd.DataFrame(values)


def test_evaluate_fixed_baseline_uses_external_holdout() -> None:
    table = build_geographic_partitions(
        {"development": model_table(30, "development")},
        {"external": model_table(10, "external")},
    )
    predictions, report = evaluate_fixed_baseline(table)
    assert len(predictions) == 10
    assert set(predictions["area_id"]) == {"external"}
    assert report["readiness"]["ready_for_geographic_validation"] is True
    assert "0117" in report["metrics_by_determinand"]
