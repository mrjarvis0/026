"""The `contracts` check: the event contracts an agent declares must be real.

FAIL: a `produces` type has no schema in config/events/ (or names the wrong schema_version).
HOLD: a `consumes` pattern matches no producer in the fleet nor a platform type (an orphan — the
      class of bug that let namespaces `market` / `markets` drift apart), or names an unknown
      `min_maturity`. PASS: nothing declared, or every declaration is satisfied.

Reads the schema files itself (type / schema_version / platform only): `security` may not import
`orchestrator` (downward-only imports, tests/test_architecture.py).
"""
from __future__ import annotations

from pathlib import Path

import yaml

from security.sentinel.fleet import AgentRecord
from security.sentinel.report import CheckResult, Verdict

_SCHEMA_DIR = Path(__file__).resolve().parents[3] / "config" / "events"
_MATURITIES = {"implemented", "validated"}


def load_schema_index(directory: Path | None = None) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for path in sorted((directory or _SCHEMA_DIR).glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if "type" in raw:
            index[raw["type"]] = {"schema_version": int(raw.get("schema_version", 1)),
                                  "platform": bool(raw.get("platform", False))}
    return index


def _matches(pattern: str, type_: str) -> bool:
    return type_.startswith(pattern[:-1]) if pattern.endswith(".*") else pattern == type_


def _declared(manifest: dict, key: str) -> list[dict]:
    return [e if isinstance(e, dict) else {"type": str(e)} for e in (manifest.get(key) or [])]


def check_contracts(record: AgentRecord, policy: dict, fleet: list[AgentRecord],
                    schemas: dict[str, dict] | None = None) -> CheckResult:
    schemas = schemas if schemas is not None else load_schema_index()
    produces, consumes = _declared(record.manifest, "produces"), _declared(record.manifest, "consumes")
    if not produces and not consumes:
        return CheckResult("contracts", Verdict.PASS, "no event contracts declared")

    failures: list[str] = []
    for entry in produces:
        type_, version = entry.get("type"), entry.get("schema_version")
        if type_ not in schemas:
            failures.append(f"{type_}: no schema in config/events/")
        elif version is not None and version != schemas[type_]["schema_version"]:
            failures.append(f"{type_}: declares schema_version {version}, schema is {schemas[type_]['schema_version']}")
    if failures:
        return CheckResult("contracts", Verdict.FAIL, f"{len(failures)} produced type(s) without a valid schema",
                           failures, len(produces))

    available = {e["type"] for r in fleet for e in _declared(r.manifest, "produces")}
    available |= {t for t, s in schemas.items() if s["platform"]}
    holds: list[str] = []
    for entry in consumes:
        pattern = entry.get("type", "")
        if entry.get("min_maturity", "validated") not in _MATURITIES:
            holds.append(f"{pattern}: unknown min_maturity {entry.get('min_maturity')!r}")
        if not any(_matches(pattern, t) for t in available):
            holds.append(f"{pattern}: no producer in the fleet (orphan consume)")
    if holds:
        return CheckResult("contracts", Verdict.HOLD, f"{len(holds)} consumed pattern(s) unsatisfied",
                           holds, len(consumes))
    return CheckResult("contracts", Verdict.PASS,
                       f"{len(produces)} produced / {len(consumes)} consumed type(s) declared and satisfied",
                       [], len(produces) + len(consumes))
