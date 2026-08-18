"""Typed study-area registry for reusable catchment pipelines."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from earth_risk_watch.settings import repository_root


class StudyArea(BaseModel):
    """One official Catchment Data Explorer analysis area."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    entity_type: Literal["OperationalCatchment", "ManagementCatchment"]
    entity_id: str
    role: str
    operational_catchment_ids: list[str] = Field(default_factory=list)

    @property
    def base_endpoint(self) -> str:
        """Return the official resource URL without a format suffix."""
        return (
            "https://environment.data.gov.uk/catchment-planning/"
            f"{self.entity_type}/{self.entity_id}"
        )


class StudyAreaRegistry(BaseModel):
    """Validated collection of uniquely identified study areas."""

    model_config = ConfigDict(extra="forbid")
    areas: list[StudyArea]

    def by_id(self, area_id: str) -> StudyArea:
        """Find a configured area by stable project identifier."""
        matches = [area for area in self.areas if area.id == area_id]
        if not matches:
            raise KeyError(f"Unknown study area: {area_id}")
        return matches[0]


def load_study_areas(path: Path | None = None) -> StudyAreaRegistry:
    """Load the project study-area registry."""
    source = path or repository_root() / "config" / "study_areas.yaml"
    with source.open(encoding="utf-8") as stream:
        registry = StudyAreaRegistry.model_validate(yaml.safe_load(stream))
    identifiers = [area.id for area in registry.areas]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Study area IDs must be unique")
    return registry
