"""Preregistered, site-grouped modelling for upstream development catchments."""

import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from earth_risk_watch.development import PREREGISTERED_PREDICTORS

ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)
NUTRIENT_CODES = frozenset({"0111", "0117", "0180"})
MODEL_FEATURES = (*PREREGISTERED_PREDICTORS, "season")


def _target_transform(code: str) -> str:
    return "log1p" if code in NUTRIENT_CODES else "identity"


def _transform(values: np.ndarray, name: str) -> np.ndarray:
    return np.log1p(values) if name == "log1p" else values


def _inverse(values: np.ndarray, name: str) -> np.ndarray:
    return np.maximum(np.expm1(values), 0) if name == "log1p" else values


def _pipeline(alpha: float) -> Pipeline:
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
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
    return Pipeline([("preprocessor", processor), ("model", Ridge(alpha=alpha))])


def _choose_alpha(
    rows: pd.DataFrame, code: str, *, alphas: tuple[float, ...] = ALPHAS
) -> tuple[float, dict[str, float]]:
    groups = rows["point_notation"].astype(str).to_numpy()
    site_count = len(np.unique(groups))
    if site_count < 3:
        raise ValueError(f"{code} requires at least three sites for grouped tuning")
    splits = GroupKFold(n_splits=min(5, site_count))
    transform = _target_transform(code)
    scores: dict[str, float] = {}
    for alpha in alphas:
        fold_mae = []
        for train_index, test_index in splits.split(rows, groups=groups):
            train = rows.iloc[train_index]
            test = rows.iloc[test_index]
            model = _pipeline(alpha)
            model.fit(
                train[list(MODEL_FEATURES)],
                _transform(train["target_mean"].to_numpy(), transform),
            )
            predicted = _inverse(model.predict(test[list(MODEL_FEATURES)]), transform)
            fold_mae.append(float(mean_absolute_error(test["target_mean"], predicted)))
        scores[str(alpha)] = float(np.mean(fold_mae))
    selected = min(alphas, key=lambda alpha: (scores[str(alpha)], alpha))
    return selected, scores


def _metrics(rows: pd.DataFrame) -> dict[str, float | int | None]:
    observed = rows["observed"].to_numpy()
    predicted = rows["predicted"].to_numpy()
    mae = float(mean_absolute_error(observed, predicted))
    result: dict[str, float | int | None] = {
        "rows": len(rows),
        "sites": int(rows["point_notation"].nunique()),
        "mae": mae,
        "rmse": float(mean_squared_error(observed, predicted) ** 0.5),
        "r2": float(r2_score(observed, predicted)) if len(rows) > 1 else None,
        "observed_min": float(np.min(observed)),
        "observed_max": float(np.max(observed)),
        "predicted_min": float(np.min(predicted)),
        "predicted_max": float(np.max(predicted)),
    }
    if "training_median_baseline" in rows:
        baseline_mae = float(
            mean_absolute_error(observed, rows["training_median_baseline"].to_numpy())
        )
        result["training_median_baseline_mae"] = baseline_mae
        result["mae_skill_vs_training_median"] = 1 - mae / baseline_mae if baseline_mae else None
    return result


def _covariate_shift(train: pd.DataFrame, test: pd.DataFrame) -> dict[str, Any]:
    """Describe held-out support relative to predictor ranges seen in training."""
    predictors: dict[str, dict[str, float]] = {}
    for feature in PREREGISTERED_PREDICTORS:
        train_values = train[feature].dropna()
        test_values = test[feature].dropna()
        lower = float(train_values.min())
        upper = float(train_values.max())
        outside = (test_values < lower) | (test_values > upper)
        train_std = float(train_values.std(ddof=0))
        predictors[feature] = {
            "training_min": lower,
            "training_max": upper,
            "held_out_min": float(test_values.min()),
            "held_out_max": float(test_values.max()),
            "held_out_fraction_outside_training_range": float(outside.mean()),
            "standardized_mean_difference": (
                float((test_values.mean() - train_values.mean()) / train_std)
                if train_std > 0
                else 0.0
            ),
        }
    return {
        "predictors": predictors,
        "maximum_fraction_outside_training_range": max(
            item["held_out_fraction_outside_training_range"] for item in predictors.values()
        ),
        "unseen_seasons": sorted(set(test["season"]) - set(train["season"])),
    }


def _site_bootstrap(
    rows: pd.DataFrame, *, draws: int = 1_000, seed: int = 42
) -> dict[str, dict[str, float]]:
    if draws < 100:
        raise ValueError("At least 100 site-bootstrap draws are required")
    sites = rows["point_notation"].astype(str).unique()
    if len(sites) < 2:
        raise ValueError("At least two sites are required for site bootstrap")
    grouped = {site: group for site, group in rows.groupby("point_notation")}
    rng = np.random.default_rng(seed)
    distributions: dict[str, list[float]] = {"mae": [], "rmse": [], "r2": []}
    for _ in range(draws):
        selected = rng.choice(sites, size=len(sites), replace=True)
        sample = pd.concat([grouped[site] for site in selected], ignore_index=True)
        metrics = _metrics(sample)
        for name in distributions:
            value = metrics[name]
            if value is not None and np.isfinite(value):
                distributions[name].append(float(value))
    return {
        name: {
            "lower_95": float(np.percentile(values, 2.5)),
            "median": float(np.percentile(values, 50)),
            "upper_95": float(np.percentile(values, 97.5)),
        }
        for name, values in distributions.items()
    }


def evaluate_upstream_development(
    table: pd.DataFrame, *, bootstrap_draws: int = 1_000, seed: int = 42
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, dict[str, Any]]]:
    """Evaluate both catchment-transfer directions and fit final development models."""
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
        raise ValueError(f"Upstream model table is missing columns: {sorted(missing)}")
    if table["target_mean"].isna().any() or (table["target_mean"] < 0).any():
        raise ValueError("Targets must be complete and non-negative")
    catchments = sorted(table["area_id"].astype(str).unique())
    if len(catchments) != 2:
        raise ValueError("Preregistered transfer evaluation requires exactly two catchments")

    prediction_frames = []
    report: dict[str, Any] = {
        "design": "two-way leave-one-catchment-out with site-grouped inner tuning",
        "alpha_grid": list(ALPHAS),
        "bootstrap_unit": "monitoring site",
        "bootstrap_draws": bootstrap_draws,
        "random_seed": seed,
        "determinand_results": {},
    }
    fitted: dict[str, dict[str, Any]] = {}
    codes = sorted(table["determinand_code"].astype(str).unique())
    for code in codes:
        subset = table.loc[table["determinand_code"].astype(str) == code].copy()
        transform = _target_transform(code)
        code_results: dict[str, Any] = {"target_transform": transform, "transfers": {}}
        for held_out in catchments:
            train = subset.loc[subset["area_id"] != held_out]
            test = subset.loc[subset["area_id"] == held_out]
            alpha, inner_scores = _choose_alpha(train, code)
            model = _pipeline(alpha)
            model.fit(
                train[list(MODEL_FEATURES)],
                _transform(train["target_mean"].to_numpy(), transform),
            )
            predicted = _inverse(model.predict(test[list(MODEL_FEATURES)]), transform)
            rows = test[
                ["area_id", "point_notation", "season", "determinand_code", "determinand", "unit"]
            ].copy()
            rows["observed"] = test["target_mean"].to_numpy()
            rows["predicted"] = predicted
            rows["residual"] = rows["observed"] - rows["predicted"]
            rows["training_median_baseline"] = float(train["target_mean"].median())
            rows["training_catchment"] = next(item for item in catchments if item != held_out)
            rows["selected_alpha"] = alpha
            prediction_frames.append(rows)
            code_results["transfers"][held_out] = {
                "training_rows": len(train),
                "training_sites": int(train["point_notation"].nunique()),
                "selected_alpha": alpha,
                "inner_grouped_cv_mae": inner_scores,
                "overall": _metrics(rows),
                "site_bootstrap_95": _site_bootstrap(rows, draws=bootstrap_draws, seed=seed),
                "covariate_shift": _covariate_shift(train, test),
                "by_season": {
                    str(season): _metrics(group) for season, group in rows.groupby("season")
                },
            }

        final_alpha, pooled_scores = _choose_alpha(subset, code)
        final_model = _pipeline(final_alpha)
        final_model.fit(
            subset[list(MODEL_FEATURES)],
            _transform(subset["target_mean"].to_numpy(), transform),
        )
        fitted[code] = {
            "model": final_model,
            "target_transform": transform,
            "selected_alpha": final_alpha,
            "features": list(MODEL_FEATURES),
        }
        code_results["final_development_model"] = {
            "rows": len(subset),
            "sites": int(subset["point_notation"].nunique()),
            "selected_alpha": final_alpha,
            "grouped_cv_mae": pooled_scores,
        }
        report["determinand_results"][code] = code_results
    return pd.concat(prediction_frames, ignore_index=True), report, fitted


def save_upstream_development_evaluation(
    table_path: Path,
    predictions_output: Path,
    model_output: Path,
    *,
    bootstrap_draws: int = 1_000,
    seed: int = 42,
) -> Path:
    """Save transfer predictions, diagnostics and frozen development models."""
    predictions, report, fitted = evaluate_upstream_development(
        pd.read_parquet(table_path), bootstrap_draws=bootstrap_draws, seed=seed
    )
    predictions_output.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_parquet(predictions_output, index=False)
    model_output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(fitted, model_output)
    report.update(
        {
            "input_path": str(table_path),
            "input_sha256": hashlib.sha256(table_path.read_bytes()).hexdigest(),
            "predictions_sha256": hashlib.sha256(predictions_output.read_bytes()).hexdigest(),
            "model_sha256": hashlib.sha256(model_output.read_bytes()).hexdigest(),
            "external_holdout_used": False,
            "interpretation": "Associative screening model; not causal or regulatory evidence.",
        }
    )
    predictions_output.with_suffix(predictions_output.suffix + ".report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return predictions_output
