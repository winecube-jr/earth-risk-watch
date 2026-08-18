import pandas as pd
import pytest

from earth_risk_watch.validation import (
    build_geographic_partitions,
    parse_partition_paths,
    partition_readiness,
)


def table(cells: int, prefix: str = "cell") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "cell_id": [f"{prefix}-{index}" for index in range(cells)],
            "determinand_code": ["0117"] * cells,
            "target_mean": range(cells),
        }
    )


def test_partition_readiness_keeps_external_cells_out_of_development_count() -> None:
    combined = build_geographic_partitions({"lune": table(29, "lune")}, {"wyre": table(13, "wyre")})
    result = partition_readiness(combined)
    assert result["development_cells"] == 29
    assert result["external_cells"] == 13
    assert result["ready_for_geographic_validation"] is False
    assert "Only 29 development cells" in str(result["reasons"])


def test_partition_readiness_accepts_separate_supported_groups() -> None:
    combined = build_geographic_partitions(
        {"development": table(30, "development")}, {"external": table(10, "external")}
    )
    assert partition_readiness(combined)["ready_for_geographic_validation"] is True


def test_partitions_reject_role_overlap_and_missing_role() -> None:
    with pytest.raises(ValueError, match="both roles"):
        build_geographic_partitions({"same": table(30)}, {"same": table(10)})
    with pytest.raises(ValueError, match="At least one"):
        build_geographic_partitions({}, {"external": table(10)})


def test_partitions_reject_cell_overlap_across_roles() -> None:
    with pytest.raises(ValueError, match="cannot cross"):
        build_geographic_partitions({"development": table(30)}, {"external": table(10)})


def test_partition_readiness_requires_schema() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        partition_readiness(pd.DataFrame({"cell_id": ["cell-1"]}))


def test_parse_partition_paths() -> None:
    result = parse_partition_paths(["lune=/tmp/lune.parquet", "ribble=/tmp/ribble.parquet"])
    assert result["lune"].name == "lune.parquet"
    with pytest.raises(ValueError, match="AREA_ID=PATH"):
        parse_partition_paths(["invalid"])
    with pytest.raises(ValueError, match="Duplicate"):
        parse_partition_paths(["lune=/tmp/a", "lune=/tmp/b"])
