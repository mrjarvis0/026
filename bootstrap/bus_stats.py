"""Bus health report.   python -m bootstrap.bus_stats

Lag per consumer, parked (dead-letter) events and the freshness of every polled source.
Exit 1 when anything needs attention: a parked event or a stale / never-seen source.
"""
from __future__ import annotations

import argparse

from bootstrap.wire import build_store, load_bus_config
from orchestrator.event_bus.store import StoreBusy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bootstrap.bus_stats")
    parser.add_argument("--db", default=None, help="bus database path (default data/bus/bus.db)")
    parser.add_argument("--approvals", action="store_true", help="also list held actions awaiting the operator")
    args = parser.parse_args(argv)
    cfg = load_bus_config()
    try:
        store = build_store(args.db)
        stats = store.stats()
        sources = [f"A015:{e}" for e in cfg["a015_exchanges"]]
        stale = store.stale_sources(sources, cfg["a015_every_min"] * 60 * cfg["stale_factor"])
    except StoreBusy as exc:
        print(f"[bus] database busy: {exc}")
        return 1
    print(f"[bus] events {stats['events']} (head seq {stats['head_seq']}), parked {stats['parked']}")
    for name, c in sorted(stats["consumers"].items()):
        print(f"[bus] consumer {name}: cursor {c['cursor']} lag {c['lag']}")
    for source in sources:
        h = stats["sources"].get(source)
        state = "STALE" if source in stale else "fresh"
        print(f"[bus] source {source}: {state}" + (f" (last ok {h['last_ok_at']}; {h['detail']})" if h else " (never seen)"))
    if args.approvals:
        for item in store.pending_approvals():
            action = item["action"] or {}
            print(f"[bus] approval #{item['id']} -> {item['to_agent']}: {item['reason']}"
                  f" (action {action.get('tool')}/{action.get('kind')}, trace {item['trace_id']})")
    return 1 if stats["parked"] or stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
