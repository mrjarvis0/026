# Sentinel Conformance Enforcer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only, static platform sentinel that reads the 026 fleet and proves each agent's real code matches its declared manifest (trust, execution-gate, secrets, registry agreement, deviation-only), with a per-agent report and a meaningful exit code.

**Architecture:** A `security/sentinel/` package. `policy.py` loads rules from `security/policies/sentinel.yaml` (policy-as-data). `scan.py` iterates agent source and finds pattern matches, ignoring comments/strings via `tokenize`. `fleet.py` loads the fleet from `config/agents/registry.yaml` + each `agent.yaml` + the `AGENTS.md` §3 table. Six checks (`checks/`) each return a `CheckResult`; `report.py` aggregates into a `FleetReport`; `sentinel.py` runs them and exposes a CLI. Read-only toward agents; downward-only imports (agents never import the sentinel).

**Tech Stack:** Python 3.14 (venv at `F:\026\.venv`), stdlib (`tokenize`, `re`, `dataclasses`, `pathlib`, `argparse`, `json`), `PyYAML` (already installed), `pytest` (already installed).

**Spec:** `docs/architecture/sentinel-conformance-design.md` (read it alongside this plan; the plan implements that spec's §4 checks and §6 report/exit semantics).

## Global Constraints

- **Read-only toward agents** — the sentinel never edits an agent file; it only reads/scans.
- **Downward-only imports** — the sentinel imports **no** agent package; no `import`/`sys.path` insertion into an agent dir. It treats agent files as text/data.
- **No new heavy deps** — stdlib + PyYAML only. Do not add numpy/pandas/etc.
- **Python** — run everything with `F:\026\.venv\Scripts\python.exe` (the SP-5 venv). Target ≥ 3.11 syntax; the machine has 3.14.7.
- **Verdicts** — `PASS` / `HOLD` (advisory) / `FAIL` (hard). Agent verdict = worst of its checks. Exit code: `2` if any `FAIL`; `1` if any `HOLD` and no `FAIL`; `0` if all `PASS`.
- **Not a git repo** — 026 is not git-tracked and the operator has not asked to init. Every "Checkpoint" step below is a **no-op unless the project is git-tracked**; do not run `git init` or commit unless the operator asks. Run the task's tests instead as the real gate.
- **Evidence over flags** — every `CheckResult` carries scanned locations (`file:line`), never a bare "ok".
- **Paths** — all commands assume cwd = `F:\026` unless stated. Run tests with `python -m pytest security/sentinel/tests -q`.

---

### Task 1: Package scaffold + policy-as-data + loader

**Files:**
- Create: `security/__init__.py` (empty), `security/sentinel/__init__.py`
- Create: `security/policies/sentinel.yaml`
- Create: `security/sentinel/policy.py`
- Test: `security/sentinel/tests/__init__.py` (empty), `security/sentinel/tests/test_policy.py`

**Interfaces:**
- Produces: `load_policy(path: str | Path | None = None) -> dict` in `security.sentinel.policy`; module constant `DEFAULT_POLICY: Path`.

- [ ] **Step 1: Write `security/policies/sentinel.yaml`** (the policy data)

```yaml
version: 1
execution:
  banned_primitives: [eth_sendRawTransaction, eth_sendTransaction, sendTransaction,
    sign_transaction, signTransaction, eth_sign, personal_sign, from_mnemonic,
    private_key, PRIVATE_KEY, place_order, submit_order, create_order, execute_trade]
  scan_globs: ["**/*.py"]
  exclude_dirs: [tests, fixtures, examples, sandbox, docs, __pycache__]
secrets:
  patterns:
    private_key_hex: '0x[0-9a-fA-F]{64}'
    assigned_secret: '(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*["''][A-Za-z0-9_\-]{16,}["'']'
  scan_globs: ["**/*.py", "**/*.yaml", "**/*.yml", "**/*.md", "**/*.toml"]
  exclude_globs: ["**/.env", "**/.env.*", "**/API_KEYS.md"]
  exclude_dirs: [tests, fixtures, __pycache__]
trust:
  min_level_requiring_evidence: 2
deviation:
  output_dirs: [decision, reporting, interfaces, intelligence/narrative]
  advice_terms: ['\bbuy\b', '\bsell\b', bullish, bearish, "you should", "we recommend",
    guaranteed, 'price will (rise|fall|go up|go down)']
registry:
  agents_md: AGENTS.md
  registry_file: config/agents/registry.yaml
```

- [ ] **Step 2: Write the failing test** — `security/sentinel/tests/test_policy.py`

```python
from security.sentinel.policy import load_policy

def test_load_policy_has_expected_sections():
    pol = load_policy()
    assert pol["version"] == 1
    for section in ("execution", "secrets", "trust", "deviation", "registry"):
        assert section in pol, section
    assert "eth_sendTransaction" in pol["execution"]["banned_primitives"]
    assert pol["trust"]["min_level_requiring_evidence"] == 2
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest security/sentinel/tests/test_policy.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'security.sentinel.policy'`.

- [ ] **Step 4: Write `security/sentinel/policy.py`**

```python
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
```

Also create the empty files: `security/__init__.py`, `security/sentinel/__init__.py`, `security/sentinel/tests/__init__.py`.

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest security/sentinel/tests/test_policy.py -q`
Expected: PASS.

- [ ] **Step 6: Checkpoint** — tests green. (Commit only if the operator asks / repo is git-tracked.)

---

### Task 2: Report model (verdicts, results, aggregation, renderers)

**Files:**
- Create: `security/sentinel/report.py`
- Test: `security/sentinel/tests/test_report.py`

**Interfaces:**
- Produces:
  - `Verdict` (str Enum): `PASS`, `HOLD`, `FAIL`.
  - `worst(verdicts: Iterable[Verdict]) -> Verdict`.
  - `CheckResult(check: str, verdict: Verdict, summary: str, evidence: list[str] = [], scanned: int = 0)`.
  - `AgentReport(id: str, dir: str, effective_trust: int, checks: list[CheckResult] = [])` with property `verdict -> Verdict`.
  - `FleetReport(agents: list[AgentReport] = [], sentinel_version="0.1.0", policy_version=1)` with property `verdict`, method `exit_code() -> int`, `to_json() -> str`, `to_table() -> str`.

- [ ] **Step 1: Write the failing test** — `security/sentinel/tests/test_report.py`

```python
import json
from security.sentinel.report import Verdict, worst, CheckResult, AgentReport, FleetReport

def test_worst_ordering():
    assert worst([Verdict.PASS, Verdict.HOLD, Verdict.FAIL]) == Verdict.FAIL
    assert worst([Verdict.PASS, Verdict.HOLD]) == Verdict.HOLD
    assert worst([Verdict.PASS, Verdict.PASS]) == Verdict.PASS
    assert worst([]) == Verdict.PASS

def test_agent_and_fleet_verdict_and_exit_code():
    a = AgentReport(id="A001", dir="agents/A001", effective_trust=2, checks=[
        CheckResult("manifest", Verdict.PASS, "ok"),
        CheckResult("trust", Verdict.HOLD, "capped"),
    ])
    assert a.verdict == Verdict.HOLD
    fleet = FleetReport(agents=[a])
    assert fleet.verdict == Verdict.HOLD
    assert fleet.exit_code() == 1
    fleet.agents[0].checks.append(CheckResult("execution", Verdict.FAIL, "lie"))
    assert fleet.exit_code() == 2

def test_to_json_roundtrips_structure():
    fleet = FleetReport(agents=[AgentReport("A002", "agents/A002", 2, [CheckResult("secrets", Verdict.PASS, "clean", ["scanned 5 files"], 5)])])
    data = json.loads(fleet.to_json())
    assert data["agents"][0]["id"] == "A002"
    assert data["agents"][0]["checks"][0]["verdict"] == "PASS"
    assert data["agents"][0]["verdict"] == "PASS"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest security/sentinel/tests/test_report.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'security.sentinel.report'`.

- [ ] **Step 3: Write `security/sentinel/report.py`**

```python
"""Sentinel report model: verdicts, per-check results, aggregation, renderers."""
from __future__ import annotations

import datetime
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum

_ORDER = {"PASS": 0, "HOLD": 1, "FAIL": 2}


class Verdict(str, Enum):
    PASS = "PASS"
    HOLD = "HOLD"
    FAIL = "FAIL"


def worst(verdicts: Iterable[Verdict]) -> Verdict:
    worst_v = Verdict.PASS
    for v in verdicts:
        if _ORDER[v.value] > _ORDER[worst_v.value]:
            worst_v = v
    return worst_v


@dataclass
class CheckResult:
    check: str
    verdict: Verdict
    summary: str
    evidence: list[str] = field(default_factory=list)
    scanned: int = 0

    def as_dict(self) -> dict:
        return {"check": self.check, "verdict": self.verdict.value,
                "summary": self.summary, "evidence": self.evidence, "scanned": self.scanned}


@dataclass
class AgentReport:
    id: str
    dir: str
    effective_trust: int
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def verdict(self) -> Verdict:
        return worst(c.verdict for c in self.checks)

    def as_dict(self) -> dict:
        return {"id": self.id, "dir": self.dir, "effective_trust": self.effective_trust,
                "verdict": self.verdict.value, "checks": [c.as_dict() for c in self.checks]}


@dataclass
class FleetReport:
    agents: list[AgentReport] = field(default_factory=list)
    sentinel_version: str = "0.1.0"
    policy_version: int = 1
    generated_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat())

    @property
    def verdict(self) -> Verdict:
        return worst(a.verdict for a in self.agents) if self.agents else Verdict.PASS

    def exit_code(self) -> int:
        v = self.verdict
        return 2 if v == Verdict.FAIL else 1 if v == Verdict.HOLD else 0

    def as_dict(self) -> dict:
        return {"generated_at": self.generated_at, "sentinel_version": self.sentinel_version,
                "policy_version": self.policy_version, "verdict": self.verdict.value,
                "agents": [a.as_dict() for a in self.agents]}

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2)

    def to_table(self) -> str:
        lines = [f"Sentinel {self.sentinel_version} — fleet verdict: {self.verdict.value}", ""]
        for a in self.agents:
            lines.append(f"  {a.id:<5} {a.verdict.value:<5} trust={a.effective_trust}  {a.dir}")
            for c in a.checks:
                if c.verdict != Verdict.PASS:
                    lines.append(f"      - [{c.verdict.value}] {c.check}: {c.summary}")
                    for ev in c.evidence[:10]:
                        lines.append(f"          {ev}")
        return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest security/sentinel/tests/test_report.py -q`
Expected: PASS.

- [ ] **Step 5: Checkpoint** — tests green.

---

### Task 3: Source-scan utility (comment/string-aware matching)

**Files:**
- Create: `security/sentinel/scan.py`
- Test: `security/sentinel/tests/test_scan.py`

**Interfaces:**
- Produces:
  - `iter_files(root: Path, globs: list[str], exclude_dirs: list[str] = [], exclude_globs: list[str] = []) -> Iterator[Path]`.
  - `strip_comments_and_strings(src: str) -> str` (blanks comment/string tokens, keeps newlines and character offsets).
  - `find_matches(text: str, patterns: list[str], word_boundary: bool = False) -> list[tuple[int, str]]` (returns `(lineno, matched_text)`).

- [ ] **Step 1: Write the failing test** — `security/sentinel/tests/test_scan.py`

```python
from security.sentinel.scan import strip_comments_and_strings, find_matches, iter_files

def test_find_matches_literal_and_word_boundary():
    text = "x = place_order()\nbuযy = 1\nbuy = 2\n"
    hits = find_matches(text, [r"buy"], word_boundary=True)
    assert (3, "buy") in hits
    hits2 = find_matches("a = eth_sendTransaction(tx)\n", ["eth_sendTransaction"], word_boundary=True)
    assert hits2 == [(1, "eth_sendTransaction")]

def test_strip_blanks_comments_and_strings_preserving_lines():
    src = 'a = 1  # sign_transaction here\nb = "eth_sendTransaction"\nc = sign_transaction()\n'
    stripped = strip_comments_and_strings(src)
    # line count preserved
    assert stripped.count("\n") == src.count("\n")
    # the comment mention and the string literal are gone; the live call remains
    assert "sign_transaction" in stripped.splitlines()[2]
    assert "sign_transaction" not in stripped.splitlines()[0]
    assert "eth_sendTransaction" not in stripped.splitlines()[1]

def test_iter_files_respects_exclude_dirs(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("x=1")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "t.py").write_text("x=1")
    found = {p.name for p in iter_files(tmp_path, ["**/*.py"], exclude_dirs=["tests"])}
    assert found == {"a.py"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest security/sentinel/tests/test_scan.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'security.sentinel.scan'`.

- [ ] **Step 3: Write `security/sentinel/scan.py`**

```python
"""Read-only source scanning utilities for the sentinel."""
from __future__ import annotations

import io
import re
import tokenize
from collections.abc import Iterator
from pathlib import Path


def iter_files(root: Path, globs: list[str], exclude_dirs: list[str] | None = None,
               exclude_globs: list[str] | None = None) -> Iterator[Path]:
    exclude_dirs = set(exclude_dirs or [])
    exclude_globs = exclude_globs or []
    seen: set[Path] = set()
    for pattern in globs:
        for path in root.glob(pattern):
            if not path.is_file() or path in seen:
                continue
            parts = set(path.relative_to(root).parts)
            if parts & exclude_dirs:
                continue
            if any(path.match(g) for g in exclude_globs):
                continue
            seen.add(path)
            yield path


def _line_starts(src: str) -> list[int]:
    starts = [0]
    for i, ch in enumerate(src):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def strip_comments_and_strings(src: str) -> str:
    """Replace comment/string token characters with spaces; keep newlines + offsets."""
    chars = list(src)
    starts = _line_starts(src)

    def offset(row: int, col: int) -> int:
        return starts[row - 1] + col

    string_types = {tokenize.STRING, tokenize.COMMENT}
    for name in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
        t = getattr(tokenize, name, None)
        if t is not None:
            string_types.add(t)
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in string_types:
                start = offset(tok.start[0], tok.start[1])
                end = offset(tok.end[0], tok.end[1])
                for i in range(start, min(end, len(chars))):
                    if chars[i] != "\n":
                        chars[i] = " "
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Unparseable file: fall back to raw text (caller still gets line-accurate hits).
        return src
    return "".join(chars)


def find_matches(text: str, patterns: list[str], word_boundary: bool = False) -> list[tuple[int, str]]:
    if not patterns:
        return []
    body = "|".join(f"(?:{p})" for p in patterns)
    regex = re.compile((r"\b(?:" + body + r")\b") if word_boundary else body)
    results: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in regex.finditer(line):
            results.append((lineno, m.group(0)))
    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest security/sentinel/tests/test_scan.py -q`
Expected: PASS.

- [ ] **Step 5: Checkpoint** — tests green.

---

### Task 4: Fleet loader (registry + manifests + AGENTS.md §3)

**Files:**
- Create: `security/sentinel/fleet.py`
- Test: `security/sentinel/tests/test_fleet.py`

**Interfaces:**
- Produces:
  - `@dataclass AgentRecord(id: str, dir: Path, manifest: dict, registry_row: dict, fleet_row: dict | None)`.
  - `parse_fleet_table(agents_md_text: str) -> dict[str, dict]` — maps `A0x -> {id, name, status}` from the §3 table (skips `*(reserved)*` rows).
  - `load_fleet(repo_root: Path, policy: dict) -> list[AgentRecord]`.

- [ ] **Step 1: Write the failing test** — `security/sentinel/tests/test_fleet.py`

```python
from pathlib import Path
from security.sentinel.fleet import parse_fleet_table, load_fleet
from security.sentinel.policy import load_policy

FLEET_MD = """
| ID    | Agent                     | Status    | Domain          |
| ----- | ------------------------- | --------- | --------------- |
| `A001` | Blockchain Intelligence   | substantial | On-chain        |
| `A002` | News Intelligence         | substantial | Rumor           |
| `A03` | *(reserved)* DeFi Flow    | planned   | Liquidity       |
"""

def test_parse_fleet_table_skips_reserved():
    table = parse_fleet_table(FLEET_MD)
    assert table["A001"]["name"] == "Blockchain Intelligence"
    assert table["A001"]["status"] == "substantial"
    assert "A03" not in table  # reserved row skipped

def test_load_fleet_reads_real_agents():
    root = Path(__file__).resolve().parents[3]  # F:\026
    records = load_fleet(root, load_policy())
    ids = {r.id for r in records}
    assert {"A001", "A002"} <= ids
    a001 = next(r for r in records if r.id == "A001")
    assert a001.manifest["invariants"]["execution_enabled"] is False
    assert a001.dir.name == "A001_Blockchain_Intelligence"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest security/sentinel/tests/test_fleet.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'security.sentinel.fleet'`.

- [ ] **Step 3: Write `security/sentinel/fleet.py`**

```python
"""Load the 026 fleet: registry + each agent.yaml + the AGENTS.md §3 table."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_ROW = re.compile(r"^\|\s*`(A\d+)`\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|")


@dataclass
class AgentRecord:
    id: str
    dir: Path
    manifest: dict[str, Any]
    registry_row: dict[str, Any]
    fleet_row: dict[str, Any] | None


def parse_fleet_table(agents_md_text: str) -> dict[str, dict]:
    table: dict[str, dict] = {}
    for line in agents_md_text.splitlines():
        m = _ROW.match(line)
        if not m:
            continue
        agent_id, name, status = m.group(1), m.group(2), m.group(3)
        if "*(reserved)*" in name or "reserved" in name.lower():
            continue
        table[agent_id] = {"id": agent_id, "name": name.strip(), "status": status.strip()}
    return table


def load_fleet(repo_root: Path, policy: dict) -> list[AgentRecord]:
    reg_path = repo_root / policy["registry"]["registry_file"]
    registry = yaml.safe_load(reg_path.read_text(encoding="utf-8")) or {}
    agents = registry.get("agents", {})
    fleet_table = parse_fleet_table((repo_root / policy["registry"]["agents_md"]).read_text(encoding="utf-8"))

    records: list[AgentRecord] = []
    for agent_id, row in agents.items():
        agent_dir = repo_root / row["dir"]
        manifest_path = repo_root / row["manifest"]
        manifest = {}
        if manifest_path.exists():
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        records.append(AgentRecord(
            id=agent_id, dir=agent_dir, manifest=manifest,
            registry_row=row, fleet_row=fleet_table.get(agent_id)))
    return records
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest security/sentinel/tests/test_fleet.py -q`
Expected: PASS (requires the real `config/agents/registry.yaml`, `AGENTS.md`, and both `agent.yaml` from SP-1).

- [ ] **Step 5: Checkpoint** — tests green.

---

### Task 5: Checks C1 (manifest) + C2 (trust)

**Files:**
- Create: `security/sentinel/checks/__init__.py`, `security/sentinel/checks/base.py`
- Create: `security/sentinel/checks/manifest.py`, `security/sentinel/checks/trust.py`
- Test: `security/sentinel/tests/test_checks_manifest_trust.py`

**Interfaces:**
- Produces:
  - `base.Check` = `Callable[[AgentRecord, dict], CheckResult]` (agent record, policy) — a typing alias.
  - `manifest.check_manifest(record, policy) -> CheckResult` (name `"manifest"`).
  - `trust.check_trust(record, policy) -> tuple[CheckResult, int]` — returns the result **and** the effective trust (capped to 1 on HOLD).
- Consumes: `AgentRecord` (Task 4), `CheckResult`/`Verdict` (Task 2).

- [ ] **Step 1: Write the failing test** — `security/sentinel/tests/test_checks_manifest_trust.py`

```python
from pathlib import Path
from security.sentinel.fleet import AgentRecord
from security.sentinel.report import Verdict
from security.sentinel.checks.manifest import check_manifest
from security.sentinel.checks.trust import check_trust
from security.sentinel.policy import load_policy

POLICY = load_policy()

def _rec(tmp_path, manifest, make_tests=False, detectors=None):
    d = tmp_path / "A99_Fake"
    (d / "tests").mkdir(parents=True) if make_tests else d.mkdir()
    if make_tests:
        (d / "tests" / "test_x.py").write_text("def test_x():\n    assert True\n")
    m = dict(manifest)
    if detectors is not None:
        m.setdefault("evidence", {})["detectors"] = detectors
    return AgentRecord(id="A99", dir=d, manifest=m, registry_row={"dir": str(d)}, fleet_row=None)

def test_manifest_missing_keys_fails(tmp_path):
    rec = _rec(tmp_path, {"id": "A99"})
    res = check_manifest(rec, POLICY)
    assert res.verdict == Verdict.FAIL

def test_manifest_complete_passes(tmp_path):
    rec = _rec(tmp_path, {"id": "A99", "name": "X", "status": "partial",
        "trust": {"level": 1}, "invariants": {"execution_enabled": False},
        "evidence": {}, "charter": "x"})
    assert check_manifest(rec, POLICY).verdict == Verdict.PASS

def test_trust_level2_without_evidence_holds_to_1(tmp_path):
    rec = _rec(tmp_path, {"id": "A99", "trust": {"level": 2}}, make_tests=False, detectors=[])
    res, eff = check_trust(rec, POLICY)
    assert res.verdict == Verdict.HOLD and eff == 1

def test_trust_level2_with_evidence_and_tests_passes(tmp_path):
    rec = _rec(tmp_path, {"id": "A99", "trust": {"level": 2}}, make_tests=True,
               detectors=[{"id": "DET-X-01"}])
    res, eff = check_trust(rec, POLICY)
    assert res.verdict == Verdict.PASS and eff == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest security/sentinel/tests/test_checks_manifest_trust.py -q`
Expected: FAIL — checks modules not found.

- [ ] **Step 3: Write the check modules**

`security/sentinel/checks/__init__.py`:
```python
"""Sentinel checks. Import the callables here so the runner can register them."""
```

`security/sentinel/checks/base.py`:
```python
from __future__ import annotations
from collections.abc import Callable
from security.sentinel.fleet import AgentRecord
from security.sentinel.report import CheckResult

Check = Callable[[AgentRecord, dict], CheckResult]
```

`security/sentinel/checks/manifest.py`:
```python
from __future__ import annotations
from security.sentinel.fleet import AgentRecord
from security.sentinel.report import CheckResult, Verdict

_REQUIRED = ["id", "name", "status", "trust", "invariants", "evidence", "charter"]


def check_manifest(record: AgentRecord, policy: dict) -> CheckResult:
    m = record.manifest
    if not m:
        return CheckResult("manifest", Verdict.FAIL, "agent.yaml missing or empty")
    missing = [k for k in _REQUIRED if k not in m]
    if "trust" in m and "level" not in (m.get("trust") or {}):
        missing.append("trust.level")
    if "invariants" in m and "execution_enabled" not in (m.get("invariants") or {}):
        missing.append("invariants.execution_enabled")
    if m.get("id") != record.id:
        return CheckResult("manifest", Verdict.FAIL,
                           f"manifest id {m.get('id')!r} != registry id {record.id!r}")
    if missing:
        return CheckResult("manifest", Verdict.FAIL, "missing keys: " + ", ".join(missing),
                           evidence=missing)
    return CheckResult("manifest", Verdict.PASS, "valid manifest", scanned=1)
```

`security/sentinel/checks/trust.py`:
```python
from __future__ import annotations
from security.sentinel.fleet import AgentRecord
from security.sentinel.report import CheckResult, Verdict


def _has_tests(agent_dir) -> bool:
    tests = agent_dir / "tests"
    return tests.is_dir() and any(tests.glob("test_*.py"))


def check_trust(record: AgentRecord, policy: dict) -> tuple[CheckResult, int]:
    level = int((record.manifest.get("trust") or {}).get("level", 0))
    threshold = policy["trust"]["min_level_requiring_evidence"]
    if level < threshold:
        return CheckResult("trust", Verdict.PASS, f"level {level} needs no evidence"), level
    detectors = (record.manifest.get("evidence") or {}).get("detectors") or []
    has_tests = _has_tests(record.dir)
    if detectors and has_tests:
        return CheckResult("trust", Verdict.PASS,
                           f"level {level} earned ({len(detectors)} detectors, tests present)"), level
    reasons = []
    if not detectors:
        reasons.append("no evidence.detectors")
    if not has_tests:
        reasons.append("no tests/test_*.py")
    return CheckResult("trust", Verdict.HOLD,
                       f"level {level} not earned ({'; '.join(reasons)}) -> capped to 1",
                       evidence=reasons), 1
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest security/sentinel/tests/test_checks_manifest_trust.py -q`
Expected: PASS.

- [ ] **Step 5: Checkpoint** — tests green.

---

### Task 6: Checks C3 (execution surface) + C4 (secrets)

**Files:**
- Create: `security/sentinel/checks/execution.py`, `security/sentinel/checks/secrets.py`
- Test: `security/sentinel/tests/test_checks_exec_secrets.py`

**Interfaces:**
- Produces: `execution.check_execution(record, policy) -> CheckResult` (name `"execution"`);
  `secrets.check_secrets(record, policy) -> CheckResult` (name `"secrets"`).
- Consumes: `scan.iter_files`, `scan.strip_comments_and_strings`, `scan.find_matches` (Task 3).

- [ ] **Step 1: Write the failing test** — `security/sentinel/tests/test_checks_exec_secrets.py`

```python
from security.sentinel.fleet import AgentRecord
from security.sentinel.report import Verdict
from security.sentinel.checks.execution import check_execution
from security.sentinel.checks.secrets import check_secrets
from security.sentinel.policy import load_policy

POLICY = load_policy()

def _rec(tmp_path):
    d = tmp_path / "A99_Fake"; d.mkdir()
    return d, AgentRecord("A99", d, {"invariants": {"execution_enabled": False}}, {"dir": str(d)}, None)

def test_execution_live_signing_call_fails(tmp_path):
    d, rec = _rec(tmp_path)
    (d / "mod.py").write_text("def go(w):\n    return sign_transaction(w)\n")
    res = check_execution(rec, POLICY)
    assert res.verdict == Verdict.FAIL
    assert any("mod.py:2" in e for e in res.evidence)

def test_execution_mention_in_comment_or_string_passes(tmp_path):
    d, rec = _rec(tmp_path)
    (d / "mod.py").write_text('# never call sign_transaction here\nBANNED = "eth_sendTransaction"\n')
    assert check_execution(rec, POLICY).verdict == Verdict.PASS

def test_execution_skips_tests_dir(tmp_path):
    d, rec = _rec(tmp_path)
    (d / "tests").mkdir(); (d / "tests" / "test_sec.py").write_text("x = sign_transaction\n")
    assert check_execution(rec, POLICY).verdict == Verdict.PASS

def test_secrets_hardcoded_key_fails(tmp_path):
    d, rec = _rec(tmp_path)
    (d / "conf.py").write_text('api_key = "abcd1234efgh5678ijkl"\n')
    assert check_secrets(rec, POLICY).verdict == Verdict.FAIL

def test_secrets_clean_passes(tmp_path):
    d, rec = _rec(tmp_path)
    (d / "conf.py").write_text('api_key = os.environ["X"]\n')
    assert check_secrets(rec, POLICY).verdict == Verdict.PASS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest security/sentinel/tests/test_checks_exec_secrets.py -q`
Expected: FAIL — modules not found.

- [ ] **Step 3: Write the check modules**

`security/sentinel/checks/execution.py`:
```python
from __future__ import annotations
from security.sentinel.fleet import AgentRecord
from security.sentinel.report import CheckResult, Verdict
from security.sentinel.scan import iter_files, strip_comments_and_strings, find_matches


def check_execution(record: AgentRecord, policy: dict) -> CheckResult:
    if (record.manifest.get("invariants") or {}).get("execution_enabled") is True:
        return CheckResult("execution", Verdict.PASS, "execution_enabled=true; gate not asserted")
    cfg = policy["execution"]
    offenders: list[str] = []
    scanned = 0
    for path in iter_files(record.dir, cfg["scan_globs"], cfg["exclude_dirs"]):
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        code = strip_comments_and_strings(text)
        for lineno, hit in find_matches(code, cfg["banned_primitives"], word_boundary=True):
            offenders.append(f"{path.relative_to(record.dir)}:{lineno}: {hit}")
    if offenders:
        return CheckResult("execution", Verdict.FAIL,
                           f"{len(offenders)} execution primitive(s) in live code", offenders, scanned)
    return CheckResult("execution", Verdict.PASS, f"{scanned} files scanned, 0 offenders",
                       [], scanned)
```

`security/sentinel/checks/secrets.py`:
```python
from __future__ import annotations
import re
from security.sentinel.fleet import AgentRecord
from security.sentinel.report import CheckResult, Verdict
from security.sentinel.scan import iter_files


def check_secrets(record: AgentRecord, policy: dict) -> CheckResult:
    cfg = policy["secrets"]
    regexes = [re.compile(p) for p in cfg["patterns"].values()]
    offenders: list[str] = []
    scanned = 0
    for path in iter_files(record.dir, cfg["scan_globs"], cfg.get("exclude_dirs"),
                           cfg.get("exclude_globs")):
        scanned += 1
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if any(rx.search(line) for rx in regexes):
                offenders.append(f"{path.relative_to(record.dir)}:{lineno}: <redacted>")
    if offenders:
        return CheckResult("secrets", Verdict.FAIL,
                           f"{len(offenders)} hardcoded secret(s)", offenders, scanned)
    return CheckResult("secrets", Verdict.PASS, f"{scanned} files scanned, 0 secrets", [], scanned)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest security/sentinel/tests/test_checks_exec_secrets.py -q`
Expected: PASS.

- [ ] **Step 5: Checkpoint** — tests green.

---

### Task 7: Checks C5 (registry agreement) + C6 (deviation best-effort)

**Files:**
- Create: `security/sentinel/checks/registry.py`, `security/sentinel/checks/deviation.py`
- Test: `security/sentinel/tests/test_checks_registry_deviation.py`

**Interfaces:**
- Produces: `registry.check_registry(record, policy) -> CheckResult` (name `"registry"`);
  `deviation.check_deviation(record, policy) -> CheckResult` (name `"deviation"`; verdict capped at HOLD).
- Consumes: `AgentRecord.registry_row`, `.fleet_row`, `.manifest`; `scan` utils.

- [ ] **Step 1: Write the failing test** — `security/sentinel/tests/test_checks_registry_deviation.py`

```python
from security.sentinel.fleet import AgentRecord
from security.sentinel.report import Verdict
from security.sentinel.checks.registry import check_registry
from security.sentinel.checks.deviation import check_deviation
from security.sentinel.policy import load_policy

POLICY = load_policy()

def test_registry_absent_from_fleet_table_fails(tmp_path):
    rec = AgentRecord("A99", tmp_path, {"id": "A99", "name": "X", "status": "partial"},
                      {"name": "X", "status": "partial"}, fleet_row=None)
    assert check_registry(rec, POLICY).verdict == Verdict.FAIL

def test_registry_status_drift_holds(tmp_path):
    rec = AgentRecord("A001", tmp_path, {"id": "A001", "name": "Blockchain Intelligence", "status": "partial"},
                      {"name": "Blockchain Intelligence", "status": "partial"},
                      fleet_row={"id": "A001", "name": "Blockchain Intelligence", "status": "substantial"})
    assert check_registry(rec, POLICY).verdict == Verdict.HOLD

def test_registry_all_agree_passes(tmp_path):
    row = {"id": "A001", "name": "Blockchain Intelligence", "status": "substantial"}
    rec = AgentRecord("A001", tmp_path, {"id": "A001", "name": "Blockchain Intelligence", "status": "substantial"},
                      {"name": "Blockchain Intelligence", "status": "substantial"}, fleet_row=row)
    assert check_registry(rec, POLICY).verdict == Verdict.PASS

def test_deviation_advice_word_holds_never_fails(tmp_path):
    d = tmp_path / "A99"; (d / "decision").mkdir(parents=True)
    (d / "decision" / "out.py").write_text('MSG = "you should buy now"\n')
    rec = AgentRecord("A99", d, {"invariants": {"reports_deviation_only": True}}, {}, None)
    res = check_deviation(rec, POLICY)
    assert res.verdict == Verdict.HOLD  # never FAIL

def test_deviation_clean_output_passes(tmp_path):
    d = tmp_path / "A99"; (d / "decision").mkdir(parents=True)
    (d / "decision" / "out.py").write_text('MSG = "deviation z-score 7.1, not a recommendation"\n')
    rec = AgentRecord("A99", d, {"invariants": {"reports_deviation_only": True}}, {}, None)
    assert check_deviation(rec, POLICY).verdict == Verdict.PASS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest security/sentinel/tests/test_checks_registry_deviation.py -q`
Expected: FAIL — modules not found.

- [ ] **Step 3: Write the check modules**

`security/sentinel/checks/registry.py`:
```python
from __future__ import annotations
from security.sentinel.fleet import AgentRecord
from security.sentinel.report import CheckResult, Verdict


def check_registry(record: AgentRecord, policy: dict) -> CheckResult:
    if record.fleet_row is None:
        return CheckResult("registry", Verdict.FAIL,
                           f"{record.id} enabled in registry but absent from AGENTS.md §3")
    reg_name = record.registry_row.get("name")
    man_name = record.manifest.get("name")
    tbl_name = record.fleet_row.get("name")
    names = {n for n in (reg_name, man_name, tbl_name) if n}
    if len(names) > 1:
        return CheckResult("registry", Verdict.FAIL,
                           f"name mismatch: registry={reg_name!r} manifest={man_name!r} table={tbl_name!r}")
    reg_status = record.registry_row.get("status")
    tbl_status = record.fleet_row.get("status")
    man_status = record.manifest.get("status")
    statuses = {s for s in (reg_status, tbl_status, man_status) if s}
    if len(statuses) > 1:
        return CheckResult("registry", Verdict.HOLD,
                           f"status drift: registry={reg_status!r} table={tbl_status!r} manifest={man_status!r}")
    return CheckResult("registry", Verdict.PASS, "registry, manifest and §3 agree")
```

`security/sentinel/checks/deviation.py`:
```python
from __future__ import annotations
from pathlib import Path
from security.sentinel.fleet import AgentRecord
from security.sentinel.report import CheckResult, Verdict
from security.sentinel.scan import find_matches

_NOTE = "declared · best-effort-scanned, not fully enforced"


def check_deviation(record: AgentRecord, policy: dict) -> CheckResult:
    if (record.manifest.get("invariants") or {}).get("reports_deviation_only") is not True:
        return CheckResult("deviation", Verdict.PASS, "reports_deviation_only not declared")
    cfg = policy["deviation"]
    terms = cfg["advice_terms"]
    offenders: list[str] = []
    scanned = 0
    for rel in cfg["output_dirs"]:
        base = record.dir / Path(rel)
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            scanned += 1
            text = path.read_text(encoding="utf-8", errors="replace")
            for lineno, hit in find_matches(text, terms):
                offenders.append(f"{path.relative_to(record.dir)}:{lineno}: {hit!r}")
    if offenders:
        return CheckResult("deviation", Verdict.HOLD,
                           f"{_NOTE} — {len(offenders)} advice-like phrase(s) for review",
                           offenders, scanned)
    return CheckResult("deviation", Verdict.PASS, f"{_NOTE} — {scanned} output files clean", [], scanned)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest security/sentinel/tests/test_checks_registry_deviation.py -q`
Expected: PASS.

- [ ] **Step 5: Checkpoint** — tests green.

---

### Task 8: Sentinel runner + CLI + full fleet integration test

**Files:**
- Create: `security/sentinel/sentinel.py`, `security/sentinel/__main__.py`
- Test: `security/sentinel/tests/test_sentinel_integration.py`

**Interfaces:**
- Consumes: `load_policy`, `load_fleet`, all six checks, report model.
- Produces:
  - `run_sentinel(repo_root: Path, policy: dict | None = None, only: str | None = None) -> FleetReport`.
  - `main(argv: list[str] | None = None) -> int` (CLI entry; parses `scan [--json] [--agent ID] [--policy PATH]`, prints, returns exit code).

- [ ] **Step 1: Write the failing test** — `security/sentinel/tests/test_sentinel_integration.py`

```python
from pathlib import Path
from security.sentinel.sentinel import run_sentinel, main
from security.sentinel.report import Verdict

ROOT = Path(__file__).resolve().parents[3]  # F:\026

def test_real_fleet_has_no_fail():
    report = run_sentinel(ROOT)
    ids = {a.id for a in report.agents}
    assert {"A001", "A002"} <= ids
    for a in report.agents:
        assert a.verdict != Verdict.FAIL, f"{a.id}: {[c.summary for c in a.checks if c.verdict==Verdict.FAIL]}"

def test_cli_scan_returns_exit_code(capsys):
    code = main(["scan"])
    out = capsys.readouterr().out
    assert "fleet verdict" in out
    assert code in (0, 1)  # PASS or HOLD, never FAIL for the real fleet

def test_cli_json_is_valid(capsys):
    import json
    main(["scan", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert "agents" in data and data["agents"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest security/sentinel/tests/test_sentinel_integration.py -q`
Expected: FAIL — `security.sentinel.sentinel` not found.

- [ ] **Step 3: Write `security/sentinel/sentinel.py`**

```python
"""The sentinel runner: load fleet, run every check, aggregate a FleetReport."""
from __future__ import annotations

import argparse
from pathlib import Path

from security.sentinel.policy import load_policy
from security.sentinel.fleet import load_fleet
from security.sentinel.report import AgentReport, FleetReport
from security.sentinel.checks.manifest import check_manifest
from security.sentinel.checks.trust import check_trust
from security.sentinel.checks.execution import check_execution
from security.sentinel.checks.secrets import check_secrets
from security.sentinel.checks.registry import check_registry
from security.sentinel.checks.deviation import check_deviation

_REPO_ROOT = Path(__file__).resolve().parents[2]  # F:\026


def run_sentinel(repo_root: Path, policy: dict | None = None, only: str | None = None) -> FleetReport:
    policy = policy or load_policy()
    report = FleetReport(policy_version=policy.get("version", 1))
    for rec in load_fleet(repo_root, policy):
        if only and rec.id != only:
            continue
        trust_result, effective_trust = check_trust(rec, policy)
        checks = [
            check_manifest(rec, policy),
            trust_result,
            check_execution(rec, policy),
            check_secrets(rec, policy),
            check_registry(rec, policy),
            check_deviation(rec, policy),
        ]
        report.agents.append(AgentReport(
            id=rec.id, dir=str(rec.dir.relative_to(repo_root)),
            effective_trust=effective_trust, checks=checks))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="security.sentinel")
    sub = parser.add_subparsers(dest="cmd", required=True)
    scan = sub.add_parser("scan", help="scan the fleet for conformance")
    scan.add_argument("--json", action="store_true")
    scan.add_argument("--agent", default=None)
    scan.add_argument("--policy", default=None)
    args = parser.parse_args(argv)

    policy = load_policy(args.policy) if args.policy else None
    report = run_sentinel(_REPO_ROOT, policy=policy, only=args.agent)
    print(report.to_json() if args.json else report.to_table())
    return report.exit_code()
```

`security/sentinel/__main__.py`:
```python
import sys
from security.sentinel.sentinel import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run the full sentinel test suite**

Run: `python -m pytest security/sentinel/tests -q`
Expected: PASS (all tasks' tests green, including `test_real_fleet_has_no_fail`).

- [ ] **Step 5: Run the sentinel for real (manual smoke)**

Run: `python -m security.sentinel scan`
Expected: a table ending with fleet verdict `PASS` or `HOLD` (never `FAIL`); exit code 0 or 1. Also try `python -m security.sentinel scan --json` and confirm valid JSON.

- [ ] **Step 6: Checkpoint** — full suite green + manual smoke clean.

---

### Task 9: Wire-up docs & discipline (BUILD_LOG, PROJECT_STATE, manual, optional make target)

**Files:**
- Modify: `BUILD_LOG.md` (append a session entry — never overwrite)
- Modify: `PROJECT_STATE.md` (update honest status: the sentinel now exists + runs)
- Modify: `docs/manual/02-structure.md` (`security/` section: sentinel landed)
- Modify: `Makefile` (add a `sentinel` target) — only if the operator uses make; else add `scripts/sentinel.bat`

**Interfaces:** none (documentation + convenience entry).

- [ ] **Step 1: Append a BUILD_LOG session** documenting: goal (SP-3 slice 1 sentinel), files created (tagged `BUILD-NEW`), tests run (`python -m pytest security/sentinel/tests -q` with the pass count), the fleet result (`python -m security.sentinel scan` verdict), self-critique (C6 best-effort; runtime gate + architecture-law + exec-gate money path still deferred), and where the next session starts (SP-3 slice 2 or SP-4 wiring). Place it before the `<!-- MERGED FROM CIE-OS -->` marker, per the existing convention.

- [ ] **Step 2: Update PROJECT_STATE.md** — change the "no orchestrator, no bus, no sentinel" line to record that the sentinel (conformance enforcer) now exists and passes over the fleet; keep the rest honest (bus/brain still absent).

- [ ] **Step 3: Update `docs/manual/02-structure.md`** — under `security/`, note `sentinel/` (the conformance enforcer) and `policies/sentinel.yaml` as built, with the `python -m security.sentinel scan` entry point.

- [ ] **Step 4: Add a `sentinel` convenience target** — a `Makefile` target `sentinel:` running `python -m security.sentinel scan`, or `scripts/sentinel.bat` for Windows one-click. Confirm it runs.

- [ ] **Step 5: Run the full suite once more**

Run: `python -m pytest security/sentinel/tests -q`
Expected: PASS.

- [ ] **Step 6: Checkpoint** — docs updated, suite green.

---

## Self-Review (author pass)

**Spec coverage:** C1 manifest → Task 5; C2 trust → Task 5; C3 execution → Task 6; C4 secrets → Task 6; C5 registry → Task 7; C6 deviation → Task 7; report + exit codes → Task 2; CLI → Task 8; policy-as-data → Task 1; fleet load incl. AGENTS.md §3 → Task 4; scan util (comment/string carve-out) → Task 3; test plan (fleet passes + planted violations + no-false-positive) → distributed across Tasks 5–8; laws/discipline + docs → Task 9. No spec section left unimplemented.

**Placeholder scan:** every code step contains real code; no TBD/TODO/"handle edge cases". The only intentionally deferred items are named in the spec's §2 out-of-scope (runtime gate, money exec-gate, architecture-law checks) — not part of this plan.

**Type consistency:** `CheckResult`/`Verdict`/`AgentReport`/`FleetReport` (Task 2) used identically in Tasks 5–8. `AgentRecord` fields (`id, dir, manifest, registry_row, fleet_row`) defined in Task 4 and consumed unchanged. `check_trust` returns `(CheckResult, int)` in Task 5 and is unpacked that way in Task 8. `scan.find_matches`/`strip_comments_and_strings`/`iter_files` signatures (Task 3) match their calls in Tasks 6–7.

**Note on running:** because the package is imported as `security.sentinel.*`, run pytest and the CLI from the repo root `F:\026` (already on `sys.path` for `python -m`). No `agents` import occurs anywhere (downward-only imports preserved).
