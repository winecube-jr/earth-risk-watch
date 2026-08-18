from pathlib import Path

import pytest

from earth_risk_watch.areas import load_study_areas


def test_load_study_areas() -> None:
    registry = load_study_areas()
    area = registry.by_id("lune-management")
    assert area.entity_id == "3053"
    assert len(area.operational_catchment_ids) == 6
    assert area.base_endpoint.endswith("ManagementCatchment/3053")


def test_study_area_ids_must_be_unique(tmp_path: Path) -> None:
    config = tmp_path / "areas.yaml"
    config.write_text(
        """areas:
  - id: duplicate
    name: A
    entity_type: OperationalCatchment
    entity_id: '1'
    role: test
  - id: duplicate
    name: B
    entity_type: OperationalCatchment
    entity_id: '2'
    role: test
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unique"):
        load_study_areas(config)
