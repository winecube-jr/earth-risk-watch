"""Fixed, leakage-safe baseline evaluation for the geographic holdout."""

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from earth_risk_watch.validation import partition_readiness

NUMERIC_FEATURES = [
    "NDVI_mean",
    "NDVI_stdDev",
    "NDMI_mean",
    "NDMI_stdDev",
    "MNDWI_mean",
    "MNDWI_stdDev",
    "BSI_mean",
    "BSI_stdDev",
    "dem_elevation_mean_m",
    "dem_elevation_std_m",
    "dem_elevation_min_m",
    "dem_elevation_max_m",
    "dem_slope_mean_degrees",
    "dem_slope_std_degrees",
]
CATEGORICAL_FEATURES = ["season"]


def _pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        [
            ("numeric", StandardScaler(), NUMERIC_FEATURES),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ]
    )
    return Pipeline([("preprocessor", preprocessor), ("model", Ridge(alpha=1.0))])


def evaluate_fixed_baseline(table: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fit on development rows and evaluate once on external rows."""
    readiness = partition_readiness(table)
    if not readiness["ready_for_geographic_validation"]:
        raise ValueError(f"Geographic validation is not ready: {readiness['reasons']}")
    required = set(NUMERIC_FEATURES + CATEGORICAL_FEATURES + ["target_mean"])
    if not required.issubset(table.columns):
        raise ValueError(f"Model table is missing columns: {sorted(required - set(table))}")
    if table[list(required)].isna().any().any():
        raise ValueError("Fixed baseline does not accept missing model values")
    predictions = []
    metrics: dict[str, Any] = {}
    for code in sorted(table["determinand_code"].astype(str).unique()):
        subset = table.loc[table["determinand_code"].astype(str) == code]
        development = subset.loc[subset["partition_role"] == "development"]
        external = subset.loc[subset["partition_role"] == "external_validation"]
        model = _pipeline()
        model.fit(
            development[NUMERIC_FEATURES + CATEGORICAL_FEATURES],
            np.log1p(development["target_mean"].to_numpy()),
        )
        predicted = np.maximum(
            np.expm1(model.predict(external[NUMERIC_FEATURES + CATEGORICAL_FEATURES])), 0
        )
        observed = external["target_mean"].to_numpy()
        baseline_value = float(development["target_mean"].median())
        baseline_mae = float(mean_absolute_error(observed, np.full(len(observed), baseline_value)))
        model_mae = float(mean_absolute_error(observed, predicted))
        result = external[
            ["area_id", "cell_id", "season", "determinand_code", "determinand", "unit"]
        ].copy()
        result["observed"] = observed
        result["predicted"] = predicted
        result["development_median_baseline"] = baseline_value
        predictions.append(result)
        metrics[code] = {
            "development_rows": len(development),
            "development_cells": int(development["cell_id"].nunique()),
            "external_rows": len(external),
            "external_cells": int(external["cell_id"].nunique()),
            "mae": model_mae,
            "r2": float(r2_score(observed, predicted)),
            "spearman": float(pd.Series(observed).corr(pd.Series(predicted), method="spearman")),
            "development_median": baseline_value,
            "baseline_mae": baseline_mae,
            "mae_skill_vs_baseline": 1 - (model_mae / baseline_mae) if baseline_mae else None,
        }
    return pd.concat(predictions, ignore_index=True), {
        "model": "Ridge(alpha=1.0) on log1p target",
        "selection": "Fixed before external evaluation; no external-catchment tuning",
        "readiness": readiness,
        "metrics_by_determinand": metrics,
    }


def save_fixed_baseline_evaluation(table_path: Path, output: Path) -> Path:
    """Save external predictions and a checksum-bearing evaluation report."""
    predictions, report = evaluate_fixed_baseline(pd.read_parquet(table_path))
    output.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_parquet(output, index=False)
    report["prediction_rows"] = len(predictions)
    report["predictions_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + ".report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return output
