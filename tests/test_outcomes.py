from pathlib import Path

import pandas as pd
import pytest

from earth_risk_watch.outcomes import build_ecological_outcomes, ecological_outcomes


def source_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Water Body ID": ["GB1", "GB1", "GB1", "GB2"],
            "Water Body": ["River One"] * 3 + ["River Two"],
            "Easting": [400_000] * 4,
            "Northing": [300_000] * 4,
            "Year": [2019, 2022, 2022, 2022],
            "Status": ["Moderate", "Good", "Fail", "Poor"],
            "Classification Level": [
                "Ecological, chemical or quantitative status",
                "Ecological, chemical or quantitative status",
                "Ecological, chemical or quantitative status",
                "Ecological, chemical or quantitative status",
            ],
            "Classification Item": ["Ecological", "Ecological", "Chemical", "Ecological"],
        }
    )


def test_ecological_outcomes() -> None:
    result = ecological_outcomes(source_frame())
    assert len(result) == 3
    assert result["status_score"].tolist() == [2, 3, 1]


def test_latest_ecological_outcomes() -> None:
    result = ecological_outcomes(source_frame(), latest_only=True)
    assert len(result) == 2
    assert set(result["year"]) == {2022}


def test_outcomes_reject_missing_schema() -> None:
    with pytest.raises(ValueError, match="Missing classification columns"):
        ecological_outcomes(pd.DataFrame({"Status": ["Good"]}))


def test_build_ecological_outcomes(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    output = tmp_path / "outcomes.parquet"
    source_frame().to_csv(source, index=False)
    build_ecological_outcomes(source, output)
    result = pd.read_parquet(output)
    assert len(result) == 3
    assert output.with_suffix(".parquet.provenance.json").exists()
