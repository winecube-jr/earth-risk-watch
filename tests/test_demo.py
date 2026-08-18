import json
from pathlib import Path

from earth_risk_watch.demo import build_demo_manifest


def test_demo_manifest(tmp_path: Path) -> None:
    target = build_demo_manifest(tmp_path)
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["source_count"] >= 8
    assert "sentinel-2-sr" in payload["source_ids"]
    assert "not an environmental risk result" in payload["warning"]
