from earth_risk_watch.readiness import checks_as_dicts, run_checks
from earth_risk_watch.settings import Settings


def test_readiness_reports_missing_project() -> None:
    checks = run_checks(Settings(earthengine_project=None))
    project = next(check for check in checks if check.name == "earth-engine-project")
    assert not project.ok


def test_checks_are_serializable() -> None:
    assert all("name" in item and "ok" in item for item in checks_as_dicts())
