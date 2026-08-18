"""Credential-free vertical slice used to verify the project foundation."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from earth_risk_watch.catalogue import load_catalogue


def build_demo_manifest(output: Path) -> Path:
    """Create a deterministic-shape provenance manifest from configured sources."""
    output.mkdir(parents=True, exist_ok=True)
    catalogue = load_catalogue()
    manifest: dict[str, Any] = {
        "product": "earth-risk-watch-foundation-demo",
        "created_at": datetime.now(UTC).isoformat(),
        "source_count": len(catalogue.sources),
        "source_ids": sorted(source.id for source in catalogue.sources),
        "warning": "Foundation manifest only; this is not an environmental risk result.",
    }
    target = output / "manifest.json"
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return target
