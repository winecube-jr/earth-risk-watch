import pandas as pd
import pytest

from earth_risk_watch.development import (
    PREREGISTERED_PREDICTORS,
    build_upstream_development_table,
    derive_upstream_predictors,
    development_diagnostics,
)


def table(site: str) -> pd.DataFrame:
    values: dict[str, object] = {
        "point_notation": site,
        "season": "winter",
        "determinand_code": "0117",
        "target_mean": 2.0,
        "outlet_upstream_area_km2": 50.0,
        "delineated_to_upstream_pixel_ratio": 1.0,
        "topology_consistent": True,
        "touches_raster_boundary": False,
        "tree_fraction_mean": 0.2,
        "grass_fraction_mean": 0.4,
        "cropland_fraction_mean": 0.3,
        "built_up_fraction_mean": 0.05,
        "water_fraction_mean": 0.04,
        "wetland_fraction_mean": 0.01,
        "precipitation_2024_mm_mean": 900.0,
        "maximum_daily_precipitation_2024_mm_mean": 20.0,
        "soil_moisture_layer_1_mean_2024_mean": 0.3,
        "upstream_overflow_count": 2,
        "upstream_spill_count_2024": 10.0,
        "upstream_spill_duration_hours_2024": 30.0,
        "tree_fraction_coverage_fraction": 1.0,
    }
    return pd.DataFrame([values])


def test_build_upstream_development_table_derives_density_features() -> None:
    result = build_upstream_development_table({"lune": table("one"), "ribble": table("two")})
    assert result["area_id"].tolist() == ["lune", "ribble"]
    assert result.loc[0, "upstream_overflow_density_per_100_km2"] == pytest.approx(4)
    assert result.loc[0, "upstream_spill_density_per_100_km2"] == pytest.approx(20)
    assert set(PREREGISTERED_PREDICTORS).issubset(result.columns)
    diagnostics = development_diagnostics(result)
    assert diagnostics["sites"] == 2
    assert diagnostics["duplicate_outcome_keys"] == 0
    assert diagnostics["target_support_by_determinand"]["0117"]["sites"] == 2


def test_development_table_rejects_site_overlap() -> None:
    with pytest.raises(ValueError, match="multiple catchments"):
        build_upstream_development_table({"lune": table("same"), "ribble": table("same")})


def test_development_table_rejects_legacy_routing_contract() -> None:
    legacy = table("one").drop(columns="topology_consistent")
    with pytest.raises(ValueError, match="corrected watershed fields"):
        build_upstream_development_table({"lune": legacy, "ribble": table("two")})


def test_development_table_rejects_missing_raster_coverage() -> None:
    missing = table("one")
    missing["tree_fraction_coverage_fraction"] = 0.0
    with pytest.raises(ValueError, match="raster coverage"):
        build_upstream_development_table({"lune": missing, "ribble": table("two")})


def test_development_table_rejects_schema_mismatch() -> None:
    mismatch = table("two").assign(extra=1)
    with pytest.raises(ValueError, match="schema mismatch"):
        build_upstream_development_table({"lune": table("one"), "ribble": mismatch})


def test_derive_upstream_predictors_recreates_frozen_features() -> None:
    result = derive_upstream_predictors(table("one"))
    assert result.loc[0, "upstream_overflow_density_per_100_km2"] == pytest.approx(4)
    assert result.loc[0, "upstream_spill_hours_per_100_km2"] == pytest.approx(60)
