from datetime import date

import pytest

from earth_risk_watch.satellite import (
    INDEX_BANDS,
    Season,
    SentinelJob,
    load_seasons,
    load_sentinel_job,
)


def test_load_sentinel_job() -> None:
    job = load_sentinel_job()
    assert job.collection == "COPERNICUS/S2_SR_HARMONIZED"
    assert job.output_scale_metres == 10
    assert job.manifest()["index_bands"] == list(INDEX_BANDS)


def test_load_seasons() -> None:
    seasons = load_seasons()
    assert [season.name for season in seasons] == ["winter", "spring", "summer", "autumn"]
    assert all(season.start_date < season.end_date for season in seasons)


def test_season_validation() -> None:
    with pytest.raises(ValueError, match="name"):
        Season(" ", date(2024, 1, 1), date(2024, 2, 1))
    with pytest.raises(ValueError, match="before"):
        Season("winter", date(2024, 2, 1), date(2024, 1, 1))


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"end_date": date(2024, 1, 1)}, "start_date"),
        ({"maximum_scene_cloud_percent": 101}, "between 0 and 100"),
        ({"output_scale_metres": 0}, "positive"),
        ({"composite": "mosaic"}, "median"),
    ],
)
def test_sentinel_job_validation(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "collection": "collection",
        "start_date": date(2024, 1, 1),
        "end_date": date(2025, 1, 1),
        "maximum_scene_cloud_percent": 60,
        "output_scale_metres": 10,
        "composite": "median",
    }
    values.update(changes)
    with pytest.raises(ValueError, match=message):
        SentinelJob(**values)  # type: ignore[arg-type]
