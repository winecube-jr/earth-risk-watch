"""Small deterministic data builders shared by model tests."""

import pandas as pd

from earth_risk_watch.development import PREREGISTERED_PREDICTORS


def model_rows(area: str, sites: int = 6) -> pd.DataFrame:
    rows = []
    for site in range(sites):
        for season_index, season in enumerate(("winter", "summer")):
            row: dict[str, object] = {
                "area_id": area,
                "point_notation": f"{area}-{site}",
                "season": season,
                "determinand_code": "0117",
                "determinand": "Nitrate",
                "unit": "mg/l",
                "target_mean": 0.1 + site + season_index,
            }
            row.update(
                {
                    feature: float(site + season_index + offset + 1)
                    for offset, feature in enumerate(PREREGISTERED_PREDICTORS)
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def ridge_report(skill: float = 0.1) -> dict[str, object]:
    transfer = {"overall": {"mae": 1.0, "mae_skill_vs_training_median": skill}}
    return {"determinand_results": {"0117": {"transfers": {"lune": transfer, "ribble": transfer}}}}
