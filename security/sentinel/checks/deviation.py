from __future__ import annotations

from pathlib import Path

from security.sentinel.fleet import AgentRecord
from security.sentinel.report import CheckResult, Verdict
from security.sentinel.scan import find_matches, python_string_literals

_NOTE = "declared · best-effort-scanned, not fully enforced"


def check_deviation(record: AgentRecord, policy: dict) -> CheckResult:
    if (record.manifest.get("invariants") or {}).get("reports_deviation_only") is not True:
        return CheckResult("deviation", Verdict.PASS, "reports_deviation_only not declared")
    cfg = policy["deviation"]
    terms = cfg["advice_terms"]
    exclude_dirs = set(cfg.get("exclude_dirs") or [])
    offenders: list[str] = []
    scanned = 0
    for rel in cfg["output_dirs"]:
        base = record.dir / Path(rel)
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            if exclude_dirs & set(path.relative_to(record.dir).parts):
                continue
            scanned += 1
            text = path.read_text(encoding="utf-8", errors="replace")
            rel_path = path.relative_to(record.dir)
            literals = python_string_literals(text)
            if literals is None:
                # Unparseable: best-effort raw scan so nothing is silently skipped.
                for lineno, hit in find_matches(text, terms):
                    offenders.append(f"{rel_path}:{lineno}: {hit!r}")
                continue
            # Only NON-docstring emitted strings — a docstring that says the agent
            # never gives advice must not itself read as advice.
            for lineno, value in literals:
                for _, hit in find_matches(value, terms):
                    offenders.append(f"{rel_path}:{lineno}: {hit!r}")
    if offenders:
        return CheckResult("deviation", Verdict.HOLD,
                           f"{_NOTE} — {len(offenders)} advice-like phrase(s) for review",
                           offenders, scanned)
    return CheckResult("deviation", Verdict.PASS, f"{_NOTE} — {scanned} output files clean", [], scanned)
