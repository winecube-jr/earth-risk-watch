"""Safe, non-destructive checks for local and cloud readiness."""

from dataclasses import asdict, dataclass
from importlib.util import find_spec

from earth_risk_watch.settings import Settings


@dataclass(frozen=True)
class Check:
    """One readiness result."""

    name: str
    ok: bool
    detail: str


def run_checks(settings: Settings | None = None) -> list[Check]:
    """Return actionable checks without initiating authentication."""
    active = settings or Settings()
    earth_engine_installed = find_spec("ee") is not None
    return [
        Check("python-package", True, "earth_risk_watch imports successfully"),
        Check(
            "earth-engine-library",
            earth_engine_installed,
            (
                "Earth Engine Python client is installed"
                if earth_engine_installed
                else "install the cloud extra: pip install -e '.[cloud]'"
            ),
        ),
        Check(
            "earth-engine-project",
            bool(active.earthengine_project),
            "set EARTHENGINE_PROJECT in .env after registration",
        ),
    ]


def checks_as_dicts(settings: Settings | None = None) -> list[dict[str, str | bool]]:
    """Return readiness results in a serializable form."""
    return [asdict(check) for check in run_checks(settings)]
