"""Operator control of the pause flags.   python -m bootstrap.flags list | clear <subject> | set <subject> --hours N

Every change writes an audit event (source SYS, ``by: operator``) so it is as traceable as an automatic one.
"""
from __future__ import annotations

import argparse
from datetime import timedelta
from pathlib import Path

from bootstrap import risk_flags
from bootstrap.wire import build_store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bootstrap.flags")
    common = argparse.ArgumentParser(add_help=False)          # options go after the subcommand
    common.add_argument("--file", default=None, help="flags file (default data/risk/pause_flags.json)")
    common.add_argument("--db", default=None, help="bus database path (default data/bus/bus.db)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", parents=[common])
    sub.add_parser("clear", parents=[common]).add_argument("subject")
    p_set = sub.add_parser("set", parents=[common])
    p_set.add_argument("subject")
    p_set.add_argument("--hours", type=float, default=None, help="expire after N hours (default: until cleared)")
    p_set.add_argument("--reason", default="operator pause")
    args = parser.parse_args(argv)
    path = Path(args.file) if args.file else None

    if args.cmd == "list":
        flags = risk_flags.load_flags(path)
        for subject, flag in sorted(flags.items()):
            print(f"{subject}  until {flag['expires_at'] or 'cleared'}  [{flag['reason']}]  ({flag['event_id']})")
        if not flags:
            print("[flags] none")
        return 0

    store = build_store(args.db)
    now = store.now()
    flags = risk_flags.load_flags(path)
    if args.cmd == "clear":
        if args.subject not in flags:
            print(f"[flags] no flag for {args.subject}")
            return 1
        del flags[args.subject]
        audit = risk_flags.audit_event("flag_cleared",
                                       event_id=risk_flags.operator_event_id("flag_cleared", args.subject, now),
                                       subject=args.subject, now=now, reason="cleared by operator", by="operator")
    else:
        expires = (now + timedelta(hours=args.hours)).isoformat() if args.hours else None
        event_id = risk_flags.operator_event_id("flag_set", args.subject, now)
        flags[args.subject] = {"set_at": now.isoformat(), "expires_at": expires, "reason": args.reason,
                               "event_id": event_id, "event_type": "operator", "maturity": None}
        audit = risk_flags.audit_event("flag_set", event_id=event_id, subject=args.subject, now=now,
                                       reason=args.reason, by="operator", expires_at=expires)
    store.publish(audit)
    risk_flags.save_flags(path, flags)
    print(f"[flags] {args.cmd} {args.subject}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
