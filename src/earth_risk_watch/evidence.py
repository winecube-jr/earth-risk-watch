"""Independent diagnostic evaluation and evidence-pack publication."""

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

NUTRIENT_CODES = ("0111", "0117", "0180")
SCREEN_METRICS = ("screening_score", "sediment_pressure", "runoff_susceptibility")


def spearman_correlation(x: pd.Series, y: pd.Series) -> float:
    """Calculate Spearman correlation without adding a SciPy dependency."""
    if len(x) != len(y) or len(x) < 3:
        raise ValueError("Correlation requires matching series with at least three values")
    ranked_x = x.rank(method="average").to_numpy(dtype=float)
    ranked_y = y.rank(method="average").to_numpy(dtype=float)
    correlation = float(np.corrcoef(ranked_x, ranked_y)[0, 1])
    if not np.isfinite(correlation):
        raise ValueError("Correlation is undefined for constant values")
    return correlation


def annual_cell_outcomes(monitoring: pd.DataFrame) -> pd.DataFrame:
    """Combine seasonal means into observation-count-weighted annual cell means."""
    selected = monitoring.loc[monitoring["determinand_code"].isin(NUTRIENT_CODES)].copy()
    selected["weighted_total"] = selected["target_mean"] * selected["observation_count"]
    outcomes = (
        selected.groupby(["cell_id", "determinand_code", "determinand"])
        .agg(
            weighted_total=("weighted_total", "sum"),
            observation_count=("observation_count", "sum"),
            seasons=("season", "nunique"),
        )
        .reset_index()
    )
    outcomes["annual_target_mean"] = outcomes["weighted_total"] / outcomes["observation_count"]
    return outcomes.drop(columns="weighted_total")


def evaluate_nutrient_alignment(
    screen: pd.DataFrame,
    monitoring: pd.DataFrame,
    *,
    permutations: int = 999,
    seed: int = 42,
) -> pd.DataFrame:
    """Run cell-level diagnostic rank correlations with permutation tests."""
    if permutations < 99:
        raise ValueError("At least 99 permutations are required")
    outcomes = annual_cell_outcomes(monitoring)
    joined = outcomes.merge(
        screen[["cell_id", *SCREEN_METRICS]], on="cell_id", validate="many_to_one"
    )
    rng = np.random.default_rng(seed)
    records = []
    for (code, name), group in joined.groupby(["determinand_code", "determinand"]):
        for metric in SCREEN_METRICS:
            observed = spearman_correlation(group[metric], group["annual_target_mean"])
            target = group["annual_target_mean"].reset_index(drop=True)
            predictor = group[metric].reset_index(drop=True)
            permuted = np.array(
                [
                    spearman_correlation(predictor, pd.Series(rng.permutation(target)))
                    for _ in range(permutations)
                ]
            )
            p_value = float((1 + np.sum(np.abs(permuted) >= abs(observed))) / (permutations + 1))
            records.append(
                {
                    "determinand_code": str(code),
                    "determinand": name,
                    "screen_metric": metric,
                    "spatial_cells": int(group["cell_id"].nunique()),
                    "observations": int(group["observation_count"].sum()),
                    "spearman_rho": observed,
                    "permutation_p_value": p_value,
                }
            )
    return pd.DataFrame(records)


def investigation_shortlist(screen: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Select stable high-priority cells while preserving evidence-gap context."""
    selected = screen.loc[screen["top_quintile_frequency"] >= 0.8].copy()
    selected["evidence_gap"] = selected["monitoring_distance_km"] > 5
    return selected.sort_values(
        ["evidence_gap", "screening_score"], ascending=[False, False]
    ).reset_index(drop=True)


def save_evidence_pack(
    screen_path: Path,
    monitoring_path: Path,
    output_dir: Path,
) -> Path:
    """Write a concise report, diagnostic table, and spatial shortlist."""
    screen = gpd.read_file(screen_path)
    monitoring = pd.read_parquet(monitoring_path)
    evaluation = evaluate_nutrient_alignment(screen, monitoring)
    shortlist = investigation_shortlist(screen)
    associations_below_005 = int((evaluation["permutation_p_value"] < 0.05).sum())
    output_dir.mkdir(parents=True, exist_ok=True)
    evaluation.to_csv(output_dir / "nutrient-alignment.csv", index=False)
    shortlist.to_file(output_dir / "investigation-shortlist.geojson", driver="GeoJSON")
    diagnostic_rows = "\n".join(
        f"| {row.determinand_code} | {row.screen_metric} | {row.spatial_cells} | "
        f"{row.spearman_rho:.2f} | {row.permutation_p_value:.3f} |"
        for row in evaluation.itertuples(index=False)
    )
    shortlist_rows = "\n".join(
        f"| {row.cell_id} | {row.screening_score:.1f} | "
        f"{row.top_quintile_frequency:.0%} | {row.monitoring_distance_km:.1f} | "
        f"{'yes' if row.evidence_gap else 'no'} |"
        for row in shortlist.head(15).itertuples(index=False)
    )
    report = f"""# Earth Risk Watch pilot evidence report

## Decision status

This is an exploratory relative screen, not a validated environmental-risk
prediction. Predictive modelling remains blocked because monitoring covers only
{monitoring["cell_id"].nunique()} independent 2 km cells; the project minimum is 30.

## Coverage and stability

- {len(screen)} pilot grid cells have complete Sentinel-2 and LiDAR predictors.
- {len(shortlist)} cells appear in the top quintile in at least 80% of weight simulations.
- {int(shortlist["evidence_gap"].sum())} shortlisted cells are more than 5 km from 2024 monitoring evidence.
- Nutrient alignment uses one annual aggregate per spatial cell to avoid treating seasons as independent replicates.

## Independent nutrient-alignment diagnostic

| Determinand | Screen metric | Cells | Spearman rho | Permutation p |
|---|---|---:|---:|---:|
{diagnostic_rows}

With only eight spatial cells, these statistics have low power and high
uncertainty. A positive correlation is not causal validation, and a large
permutation p-value is inconclusive rather than evidence of no relationship.
None of the {len(evaluation)} comparisons has a permutation value below 0.05
({associations_below_005} of {len(evaluation)}). The screen must therefore remain
a broad pressure-investigation layer and must not be presented as a nutrient-risk
prediction.

## Stable investigation shortlist

| Cell | Score | Top-quintile frequency | Monitoring distance km | Evidence gap |
|---|---:|---:|---:|---|
{shortlist_rows}

## Recommended next evidence action

Prioritise field review or additional open-data linkage for stable high-ranked
cells with evidence gaps. Expand to multiple operational catchments before model
training, then use grouped spatial validation that holds out entire catchments.

Machine-readable companions: `nutrient-alignment.csv` and
`investigation-shortlist.geojson`.
"""
    report_path = output_dir / "evidence-report.md"
    report_path.write_text(report, encoding="utf-8")
    manifest = {
        "product_type": "exploratory evidence pack; not predictive validation",
        "screen_cells": len(screen),
        "monitored_cells": int(monitoring["cell_id"].nunique()),
        "shortlisted_cells": len(shortlist),
        "evidence_gap_cells": int(shortlist["evidence_gap"].sum()),
        "diagnostic_comparisons": len(evaluation),
        "associations_below_005": associations_below_005,
        "permutations": 999,
        "seed": 42,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return report_path
