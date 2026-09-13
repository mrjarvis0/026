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
        for lineno, line in enumerate(
                path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if any(rx.search(line) for rx in regexes):
                offenders.append(f"{path.relative_to(record.dir)}:{lineno}: <redacted>")
    if offenders:
        return CheckResult("secrets", Verdict.FAIL,
                           f"{len(offenders)} hardcoded secret(s)", offenders, scanned)
    return CheckResult("secrets", Verdict.PASS, f"{scanned} files scanned, 0 secrets", [], scanned)
