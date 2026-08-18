from pathlib import Path

import pytest

from earth_risk_watch.catalogue import load_catalogue


def test_catalogue_loads_and_ids_are_unique() -> None:
    catalogue = load_catalogue()
    assert len(catalogue.sources) >= 8
    assert len({source.id for source in catalogue.sources}) == len(catalogue.sources)


def test_catalogue_lookup() -> None:
    source = load_catalogue().by_id("ea-national-lidar")
    assert source.geography == "England"
    assert source.is_http


def test_catalogue_rejects_unknown_source() -> None:
    with pytest.raises(KeyError, match="Unknown data source"):
        load_catalogue().by_id("does-not-exist")


def test_catalogue_rejects_duplicate_ids(tmp_path: Path) -> None:
    config = tmp_path / "sources.yaml"
    config.write_text(
        """sources:
  - &source
    id: duplicate
    title: Example
    provider: Example
    access: http_api
    endpoint: https://example.com
    geography: England
    licence: Example
    themes: [water]
  - *source
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate"):
        load_catalogue(config)
