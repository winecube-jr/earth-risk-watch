"""Preregistered robust comparison and applicability-domain diagnostics."""

import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from earth_risk_watch.development import PREREGISTERED_PREDICTORS
from earth_risk_watch.upstream_model import (
    MODEL_FEATURES,
    _inverse,
    _metrics,
    _site_bootstrap,
    _target_transform,
    _transform,
)

FOREST_PARAMETERS: dict[str, object] = {
    "n_estimators": 500,
    "min_samples_leaf": 5,
    "max_features": 0.7,
    "bootstrap": True,
    "random_state": 42,
    "n_jobs": -1,
}


def _forest_pipeline(*, n_estimators: int = 500) -> Pipeline:
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median"))])
    processor = ColumnTransformer(
        [
            ("numeric", numeric, list(PREREGISTERED_PREDICTORS)),
            (
                "season",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                ["season"],
            ),
        ]
    )
    forest = RandomForestRegressor(**(FOREST_PARAMETERS | {"n_estimators": n_estimators}))
    return Pipeline([("preprocessor", processor), ("model", forest)])


def _support_profile(rows: pd.DataFrame) -> dict[str, Any]:
    sites = rows.drop_duplicates("point_notation")
    predictors: dict[str, dict[str, float]] = {}
    for feature in PREREGISTERED_PREDICTORS:
        values = sites[feature].dropna()
        predictors[feature] = {
            "minimum": float(values.min()),
            "maximum": float(values.max()),
            "median": float(values.median()),
            "iqr": float(values.quantile(0.75) - values.quantile(0.25)),
        }
    return {"predictors": predictors, "seasons": sorted(rows["season"].astype(str).unique())}


def _attach_applicability(rows: pd.DataFrame, support: dict[str, Any]) -> pd.DataFrame:
    result = rows.copy()
    outside_count = np.zeros(len(result), dtype=int)
    maximum_robust_z = np.zeros(len(result), dtype=float)
    for feature in PREREGISTERED_PREDICTORS:
        profile = support["predictors"][feature]
        values = result[feature].to_numpy(dtype=float)
        outside_count += (values < profile["minimum"]) | (values > profile["maximum"])
        deviation = np.abs(values - profile["median"])
        robust_z = (
            deviation / profile["iqr"] if profile["iqr"] > 0 else np.where(deviation, np.inf, 0)
        )
        maximum_robust_z = np.maximum(maximum_robust_z, robust_z)
    unseen_season = ~result["season"].astype(str).isin(support["seasons"])
    outside = (outside_count >= 2) | (maximum_robust_z > 4) | unseen_season
    result["predictors_outside_training_range"] = outside_count
    result["fraction_predictors_outside_training_range"] = outside_count / len(
        PREREGISTERED_PREDICTORS
    )
    result["maximum_absolute_robust_z"] = maximum_robust_z
    result["unseen_season"] = unseen_season
    result["applicability_status"] = np.where(
        outside, "outside_applicability_domain", "within_applicability_domain"
    )
    return result


def _advancement_decision(
    code: str, forest_results: dict[str, Any], ridge_report: dict[str, Any]
) -> dict[str, Any]:
    ridge = ridge_report["determinand_results"][code]["transfers"]
    candidates = {
        "ridge": {
            "mae": [item["overall"]["mae"] for item in ridge.values()],
            "skill": [item["overall"]["mae_skill_vs_training_median"] for item in ridge.values()],
        },
        "random_forest": {
            "mae": [item["overall"]["mae"] for item in forest_results["transfers"].values()],
            "skill": [
                item["overall"]["mae_skill_vs_training_median"]
                for item in forest_results["transfers"].values()
            ],
        },
    }
    eligible = [
        name
        for name, values in candidates.items()
        if all(skill is not None and skill > 0 for skill in values["skill"])
    ]
    selected = min(
        eligible,
        key=lambda name: (float(np.mean(candidates[name]["mae"])), name != "ridge"),
        default=None,
    )
    return {
        "eligible_candidates": eligible,
        "selected_candidate": selected,
        "eligible_for_derwent": selected is not None,
        "reason": (
            "Selected the eligible candidate with lowest mean transfer MAE."
            if selected
            else "No candidate beats its training-median baseline in both transfer directions."
        ),
    }


def evaluate_robust_upstream_development(
    table: pd.DataFrame,
    ridge_report: dict[str, Any],
    *,
    bootstrap_draws: int = 1_000,
    seed: int = 42,
    n_estimators: int = 500,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, dict[str, Any]]]:
    """Run fixed random-forest transfer comparisons without opening the holdout."""
    required = set(MODEL_FEATURES) | {
        "area_id",
        "point_notation",
        "determinand_code",
        "determinand",
        "unit",
        "target_mean",
    }
    missing = required.difference(table.columns)
    if missing:
        raise ValueError(f"Robust model table is missing columns: {sorted(missing)}")
    catchments = sorted(table["area_id"].astype(str).unique())
    if len(catchments) != 2:
        raise ValueError("Robust transfer evaluation requires exactly two catchments")
    prediction_frames = []
    report: dict[str, Any] = {
        "design": "fixed random forest on identical two-way catchment transfers",
        "forest_parameters": FOREST_PARAMETERS | {"n_estimators": n_estimators},
        "applicability_rule": (
            "outside when >=2 predictors exceed training range, maximum robust z >4, "
            "or season is unseen"
        ),
        "bootstrap_unit": "monitoring site",
        "bootstrap_draws": bootstrap_draws,
        "random_seed": seed,
        "determinand_results": {},
    }
    fitted: dict[str, dict[str, Any]] = {}
    for code in sorted(table["determinand_code"].astype(str).unique()):
        subset = table.loc[table["determinand_code"].astype(str) == code].copy()
        transform = _target_transform(code)
        code_results: dict[str, Any] = {"target_transform": transform, "transfers": {}}
        for held_out in catchments:
            train = subset.loc[subset["area_id"] != held_out]
            test = subset.loc[subset["area_id"] == held_out]
            support = _support_profile(train)
            assessed = _attach_applicability(test, support)
            model = _forest_pipeline(n_estimators=n_estimators)
            model.fit(
                train[list(MODEL_FEATURES)],
                _transform(train["target_mean"].to_numpy(), transform),
            )
            predicted = _inverse(model.predict(test[list(MODEL_FEATURES)]), transform)
            columns = [
                "area_id",
                "point_notation",
                "season",
                "determinand_code",
                "determinand",
                "unit",
                "predictors_outside_training_range",
                "fraction_predictors_outside_training_range",
                "maximum_absolute_robust_z",
                "unseen_season",
                "applicability_status",
            ]
            rows = assessed[columns].copy()
            rows["observed"] = test["target_mean"].to_numpy()
            rows["predicted"] = predicted
            rows["residual"] = rows["observed"] - rows["predicted"]
            rows["training_median_baseline"] = float(train["target_mean"].median())
            rows["training_catchment"] = next(item for item in catchments if item != held_out)
            prediction_frames.append(rows)
            code_results["transfers"][held_out] = {
                "training_rows": len(train),
                "training_sites": int(train["point_notation"].nunique()),
                "overall": _metrics(rows),
                "site_bootstrap_95": _site_bootstrap(rows, draws=bootstrap_draws, seed=seed),
                "by_season": {
                    str(season): _metrics(group) for season, group in rows.groupby("season")
                },
                "by_applicability": {
                    str(status): _metrics(group)
                    for status, group in rows.groupby("applicability_status")
                },
                "outside_applicability_rows": int(
                    (rows["applicability_status"] == "outside_applicability_domain").sum()
                ),
            }
        final_support = _support_profile(subset)
        final_model = _forest_pipeline(n_estimators=n_estimators)
        final_model.fit(
            subset[list(MODEL_FEATURES)],
            _transform(subset["target_mean"].to_numpy(), transform),
        )
        fitted[code] = {
            "model": final_model,
            "target_transform": transform,
            "features": list(MODEL_FEATURES),
            "applicability_support": final_support,
            "development_target_median": float(subset["target_mean"].median()),
            "development_target_minimum": float(subset["target_mean"].min()),
            "development_target_maximum": float(subset["target_mean"].max()),
        }
        code_results["advancement"] = _advancement_decision(code, code_results, ridge_report)
        report["determinand_results"][code] = code_results
    return pd.concat(prediction_frames, ignore_index=True), report, fitted


def save_robust_upstream_evaluation(
    table_path: Path,
    ridge_report_path: Path,
    predictions_output: Path,
    model_output: Path,
    *,
    bootstrap_draws: int = 1_000,
    seed: int = 42,
) -> Path:
    """Save the frozen forest comparison, applicability evidence and models."""
    ridge_report = json.loads(ridge_report_path.read_text(encoding="utf-8"))
    predictions, report, fitted = evaluate_robust_upstream_development(
        pd.read_parquet(table_path),
        ridge_report,
        bootstrap_draws=bootstrap_draws,
        seed=seed,
    )
    predictions_output.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_parquet(predictions_output, index=False)
    model_output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(fitted, model_output)
    report.update(
        {
            "input_sha256": hashlib.sha256(table_path.read_bytes()).hexdigest(),
            "ridge_report_sha256": hashlib.sha256(ridge_report_path.read_bytes()).hexdigest(),
            "predictions_sha256": hashlib.sha256(predictions_output.read_bytes()).hexdigest(),
            "model_sha256": hashlib.sha256(model_output.read_bytes()).hexdigest(),
            "external_holdout_used": False,
        }
    )
    predictions_output.with_suffix(predictions_output.suffix + ".report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return predictions_output
