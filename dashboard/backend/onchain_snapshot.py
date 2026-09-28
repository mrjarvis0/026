"""A001's own read-only view of the chain, for the dashboard's /onchain page.

Calls A001's IntelligenceService through the same bus adapter the kernel uses
(bootstrap.adapters.a001_handler) — health, coverage, flows, detectors, chains, metrics.
Read-only by construction: no network, no writes, no keys.

stdout: {"<op>": <adapter result>, ...}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root

from bootstrap.adapters import a001_handler  # noqa: E402

OPS = ("health", "coverage", "flows", "detectors", "chains", "metrics")


class _Message:  # the adapter only reads `.payload`
    def __init__(self, op: str) -> None:
        self.payload = {"op": op}


def main() -> None:
    out = {}
    for op in OPS:
        try:
            out[op] = a001_handler(_Message(op))
        except Exception as exc:  # one failing op must not hide the others
            out[op] = {"op": op, "ok": False, "error": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(out, default=str))


if __name__ == "__main__":
    main()
