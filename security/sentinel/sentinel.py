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
from security.sentinel.checks.contracts import check_contracts

_REPO_ROOT = Path(__file__).resolve().parents[2]  # F:\026


def run_sentinel(repo_root: Path, policy: dict | None = None, only: str | None = None) -> FleetReport:
    policy = policy or load_policy()
    report = FleetReport(policy_version=policy.get("version", 1))
    fleet = load_fleet(repo_root, policy)
    for rec in fleet:
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
            check_contracts(rec, policy, fleet),
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
