"""Load the sentinel's policy-as-data (security/policies/sentinel.yaml)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_POLICY = Path(__file__).resolve().parents[1] / "policies" / "sentinel.yaml"


def load_policy(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else DEFAULT_POLICY
    with open(p, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"policy at {p} is not a mapping")
    return data
