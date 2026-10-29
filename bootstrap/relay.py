"""Relay + health monitor CLI.   python -m bootstrap.relay --once

Publishes A015's new facts to the event bus, records source health, and — for every polled source
that is stale or never seen — publishes one ``system.source.stale`` per outage (platform source
``SYS``). Exit 1 if the store is busy or anything was rejected.
"""
from __future__ import annotations

import argparse
from datetime import timezone

from bootstrap.relays import a015 as relay_a015
from bootstrap.wire import build_store, load_bus_config
from orchestrator.event_bus.envelope import make_event_id
from orchestrator.event_bus.store import EventStore, StoreBusy

MAX_REJECTED_SHOWN = 5    # a replay of old junk can reject thousands; the log needs the count, not every line

__all__ = ["load_bus_config", "monitor_once", "main"]


def monitor_once(store: EventStore, sources: list[str], max_age_s: float) -> list[str]:
    """Publish one ``system.source.stale`` per outage; clear the flag when a source is fresh again.
    Returns the sources that became stale on this call."""
    stale = set(store.stale_sources(sources, max_age_s))
    newly: list[str] = []
    for source in sources:
        key = f"stale:{source}"
        flagged = store.get_state("monitor", key) == "1"
        if source in stale and not flagged:
            health = store.health(source)
            last_ok = health["last_ok_at"] if health else None
            now = store.now().astimezone(timezone.utc).isoformat()
            event_id = make_event_id("stale", source, str(last_ok))
            store.publish({
                "event_id": event_id, "type": "system.source.stale", "schema_version": 1, "source": "SYS",
                "subject": f"source:{source}", "event_time": None, "event_window": None,
                "observed_at": now, "known_at": None, "trace_id": "trc_" + event_id[4:], "causation_id": None,
                "detector": None, "confidence": None,
                "coverage": {"complete": None, "as_of": now, "lag_s": None,
                             "note": "health monitor: no successful non-baseline poll within max_age_s"},
                "evidence": [], "untrusted": False,
                "data": {"source": source, "max_age_s": max_age_s, "last_ok_at": last_ok},
            })
            store.set_state("monitor", key, "1")
            newly.append(source)
        elif source not in stale and flagged:
            store.set_state("monitor", key, "0")
    return newly


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bootstrap.relay")
    parser.add_argument("--once", action="store_true", help="run one relay + monitor pass and exit")
    parser.add_argument("--db", default=None, help="bus database path (default data/bus/bus.db)")
    args = parser.parse_args(argv)
    cfg = load_bus_config()
    try:
        store = build_store(args.db)
        result = relay_a015.relay_once(store)
        sources = [f"A015:{e}" for e in cfg["a015_exchanges"]]
        max_age = cfg["a015_every_min"] * 60 * cfg["stale_factor"]
        newly_stale = monitor_once(store, sources, max_age)
    except StoreBusy as exc:
        print(f"[relay] bus database busy: {exc}")
        return 1
    print(f"[relay] published {result.published}, duplicates {result.duplicates}, files {result.files}, "
          f"health {result.health_updated}, stale {newly_stale}, rejected {len(result.rejected)}")
    for line in result.rejected[:MAX_REJECTED_SHOWN]:
        print(f"[relay] rejected: {line}")
    if len(result.rejected) > MAX_REJECTED_SHOWN:
        print(f"[relay] ... and {len(result.rejected) - MAX_REJECTED_SHOWN} more rejected")
    return 1 if result.rejected else 0


if __name__ == "__main__":
    raise SystemExit(main())
