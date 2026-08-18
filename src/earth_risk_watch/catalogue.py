"""Validated metadata catalogue for environmental data sources."""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, HttpUrl

from earth_risk_watch.settings import repository_root


class DataSource(BaseModel):
    """A remotely hosted environmental dataset."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    provider: str
    access: str
    endpoint: str
    geography: str
    licence: str
    themes: list[str]

    @property
    def is_http(self) -> bool:
        """Return whether the endpoint is an HTTP URL rather than a collection ID."""
        try:
            HttpUrl(self.endpoint)
        except (TypeError, ValueError):
            return False
        return True


class Catalogue(BaseModel):
    """Collection of unique data sources."""

    model_config = ConfigDict(extra="forbid")
    sources: list[DataSource]

    def by_id(self, source_id: str) -> DataSource:
        """Look up a source or raise an informative error."""
        matches = [source for source in self.sources if source.id == source_id]
        if not matches:
            raise KeyError(f"Unknown data source: {source_id}")
        return matches[0]

    def validate_unique_ids(self) -> None:
        """Reject ambiguous duplicate source identifiers."""
        ids = [source.id for source in self.sources]
        duplicates = sorted({source_id for source_id in ids if ids.count(source_id) > 1})
        if duplicates:
            raise ValueError(f"Duplicate data-source IDs: {', '.join(duplicates)}")


def load_catalogue(path: Path | None = None) -> Catalogue:
    """Load and validate the configured source catalogue."""
    catalogue_path = path or repository_root() / "config" / "data_sources.yaml"
    with catalogue_path.open(encoding="utf-8") as stream:
        raw = yaml.safe_load(stream)
    catalogue = Catalogue.model_validate(raw)
    catalogue.validate_unique_ids()
    return catalogue
