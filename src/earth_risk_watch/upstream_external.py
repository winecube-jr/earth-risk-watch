"""One-shot evaluation of frozen upstream models on the untouched holdout."""

import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import yaml

from earth_risk_watch.upstream_model import MODEL_FEATURES, _inverse, _metrics, _site_bootstrap
from earth_risk_watch.upstream_robust import _attach_applicability


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate_upstream_external_holdout(
    holdout: pd.DataFrame,
    development: pd.DataFrame,
    fitted: dict[str, dict[str, Any]],
    selection: dict[str, Any],
    *,
    area_id: str,
    bootstrap_draws: int = 1_000,
    seed: int = 42,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Evaluate only preregistered eligible outcomes without refitting."""
    if area_id != selection["external_holdout"]["area_id"]:
        raise ValueError("Area does not match the frozen external holdout")
    required = set(MODEL_FEATURES) | {
        "point_notation",
        "season",
        "determinand_code",
        "determinand",
        "unit",
        "target_mean",
        "topology_consistent",
        "touches_raster_boundary",
    }
    missing = required.difference(holdout.columns)
    if missing:
        raise ValueError(f"External table is missing columns: {sorted(missing)}")
    if not holdout["topology_consistent"].all() or holdout["touches_raster_boundary"].any():
        raise ValueError("External table contains invalid or truncated watersheds")
    overlap = set(holdout["point_notation"].astype(str)).intersection(
        development["point_notation"].astype(str)
    )
    if overlap:
        raise ValueError(f"External sites overlap development: {sorted(overlap)}")
    selected = selection["selected_models"]
    prediction_frames = []
    report: dict[str, Any] = {
        "area_id": area_id,
        "evaluation": "one-shot untouched external holdout",
        "bootstrap_unit": "monitoring site",
        "bootstrap_draws": bootstrap_draws,
        "random_seed": seed,
        "determinand_results": {},
    }
    for code, candidate in selected.items():
        if candidate != "random_forest":
            raise ValueError(f"Unsupported selected model for {code}: {candidate}")
        rows = holdout.loc[holdout["determinand_code"].astype(str) == str(code)].copy()
        if rows.empty:
            raise ValueError(f"External table contains no rows for selected determinand {code}")
        bundle = fitted[str(code)]
        assessed = _attach_applicability(rows, bundle["applicability_support"])
        predicted = _inverse(
            bundle["model"].predict(rows[list(MODEL_FEATURES)]), bundle["target_transform"]
        )
        columns = [
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
        result = assessed[columns].copy()
        result.insert(0, "area_id", area_id)
        result["observed"] = rows["target_mean"].to_numpy()
        result["predicted"] = predicted
        result["residual"] = result["observed"] - result["predicted"]
        result["training_median_baseline"] = bundle["development_target_median"]
        prediction_frames.append(result)
        report["determinand_results"][str(code)] = {
            "selected_model": candidate,
            "target_transform": bundle["target_transform"],
            "overall": _metrics(result),
            "site_bootstrap_95": _site_bootstrap(result, draws=bootstrap_draws, seed=seed),
            "by_season": {
                str(season): _metrics(group) for season, group in result.groupby("season")
            },
            "by_applicability": {
                str(status): _metrics(group)
                for status, group in result.groupby("applicability_status")
            },
            "outside_applicability_rows": int(
                (result["applicability_status"] == "outside_applicability_domain").sum()
            ),
        }
    return pd.concat(prediction_frames, ignore_index=True), report


def save_upstream_external_holdout_evaluation(
    holdout_path: Path,
    development_path: Path,
    model_path: Path,
    selection_path: Path,
    output: Path,
    *,
    area_id: str,
    bootstrap_draws: int = 1_000,
    seed: int = 42,
) -> Path:
    """Verify frozen inputs, evaluate once and save checksum-bearing evidence."""
    selection = yaml.safe_load(selection_path.read_text(encoding="utf-8"))
    if _sha256(model_path) != selection["artifacts"]["robust_model_sha256"]:
        raise ValueError("Robust model checksum does not match the frozen selection")
    predictions, report = evaluate_upstream_external_holdout(
        pd.read_parquet(holdout_path),
        pd.read_parquet(development_path),
        joblib.load(model_path),
        selection,
        area_id=area_id,
        bootstrap_draws=bootstrap_draws,
        seed=seed,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_parquet(output, index=False)
    report.update(
        {
            "holdout_input_sha256": _sha256(holdout_path),
            "development_input_sha256": _sha256(development_path),
            "model_sha256": _sha256(model_path),
            "selection_sha256": _sha256(selection_path),
            "predictions_sha256": _sha256(output),
            "warning": "Associative screening evidence; not causal or regulatory evidence.",
        }
    )
    output.with_suffix(output.suffix + ".report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return output
