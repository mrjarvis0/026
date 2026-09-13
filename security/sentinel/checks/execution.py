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
