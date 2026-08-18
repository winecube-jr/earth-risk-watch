"""Application configuration and repository paths."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed runtime settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    earthengine_project: str | None = None
    earth_risk_log_level: str = "INFO"


def repository_root() -> Path:
    """Return the repository root without relying on the current directory."""
    return Path(__file__).resolve().parents[2]
