"""Uncertainty and failure diagnostics for external catchment evaluations."""

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score

KEY_COLUMNS = ["area_id", "cell_id", "season", "determinand_code"]


def evaluation_rows(predictions: pd.DataFrame, partitions: pd.DataFrame) -> pd.DataFrame:
    """Attach monitoring support and censoring context to external predictions."""
    context_columns = KEY_COLUMNS + ["observation_count", "site_count", "censored_fraction"]
    if predictions.duplicated(KEY_COLUMNS).any() or partitions.duplicated(KEY_COLUMNS).any():
        raise ValueError("Evaluation keys must be unique")
    context = partitions.loc[partitions["partition_role"] == "external_validation", context_columns]
    rows = predictions.merge(context, on=KEY_COLUMNS, how="left", validate="one_to_one")
    if rows[context_columns[4:]].isna().any().any():
        raise ValueError("Predictions are missing external monitoring context")
    rows["censoring_group"] = np.where(
        rows["censored_fraction"] > 0, "contains_censored_results", "uncensored"
    )
    rows["absolute_error"] = (rows["observed"] - rows["predicted"]).abs()
    return rows


def _metrics(rows: pd.DataFrame) -> dict[str, float | int | None]:
    observed = rows["observed"].to_numpy()
    predicted = rows["predicted"].to_numpy()
    baseline = rows["development_median_baseline"].to_numpy()
    mae = float(mean_absolute_error(observed, predicted))
    baseline_mae = float(mean_absolute_error(observed, baseline))
    return {
        "rows": len(rows),
        "cells": int(rows["cell_id"].nunique()),
        "mae": mae,
        "r2": float(r2_score(observed, predicted)) if len(rows) > 1 else None,
        "spearman": (
            float(rows["observed"].corr(rows["predicted"], method="spearman"))
            if len(rows) > 1
            else None
        ),
        "mae_skill_vs_baseline": 1 - mae / baseline_mae if baseline_mae else None,
    }


def grouped_bootstrap_intervals(
    rows: pd.DataFrame, *, draws: int = 1_000, seed: int = 42
) -> dict[str, dict[str, float]]:
    """Bootstrap whole monitoring cells and preserve all their seasonal rows."""
    if draws < 100:
        raise ValueError("At least 100 bootstrap draws are required")
    cells = rows["cell_id"].unique()
    if len(cells) < 2:
        raise ValueError("At least two cells are required for grouped bootstrap")
    rng = np.random.default_rng(seed)
    distributions: dict[str, list[float]] = {
        "mae": [],
        "r2": [],
        "spearman": [],
        "mae_skill_vs_baseline": [],
    }
    grouped = {cell: group for cell, group in rows.groupby("cell_id")}
    for _ in range(draws):
        selected = rng.choice(cells, size=len(cells), replace=True)
        sample = pd.concat([grouped[cell] for cell in selected], ignore_index=True)
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


def evaluation_diagnostics(
    predictions: pd.DataFrame,
    partitions: pd.DataFrame,
    *,
    draws: int = 1_000,
    seed: int = 42,
) -> dict[str, Any]:
    """Build per-determinand uncertainty, season, and censoring diagnostics."""
    rows = evaluation_rows(predictions, partitions)
    report: dict[str, Any] = {
        "bootstrap_unit": "monitoring cell",
        "bootstrap_draws": draws,
        "random_seed": seed,
        "determinand_diagnostics": {},
    }
    for code, group in rows.groupby("determinand_code"):
        report["determinand_diagnostics"][str(code)] = {
            "overall": _metrics(group),
            "cell_grouped_bootstrap": grouped_bootstrap_intervals(group, draws=draws, seed=seed),
            "by_season": {str(name): _metrics(part) for name, part in group.groupby("season")},
            "by_censoring": {
                str(name): _metrics(part) for name, part in group.groupby("censoring_group")
            },
        }
    return report


def save_evaluation_diagnostics(
    predictions_path: Path,
    partitions_path: Path,
    output: Path,
    *,
    draws: int = 1_000,
    seed: int = 42,
) -> Path:
    """Save deterministic grouped-bootstrap external evaluation diagnostics."""
    report = evaluation_diagnostics(
        pd.read_parquet(predictions_path),
        pd.read_parquet(partitions_path),
        draws=draws,
        seed=seed,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return output
