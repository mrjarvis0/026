"""A015 CLI. Run from repo root:

    python -m agents.A015_Exchange_Listing_Delisting_Intelligence.cli doctor
    python -m agents.A015_Exchange_Listing_Delisting_Intelligence.cli demo
    python -m agents.A015_Exchange_Listing_Delisting_Intelligence.cli poll --limit 2
"""
from __future__ import annotations

import argparse

from agents.A015_Exchange_Listing_Delisting_Intelligence.core import config_loader as cfg
from agents.A015_Exchange_Listing_Delisting_Intelligence.core import event_log, poll_status
from agents.A015_Exchange_Listing_Delisting_Intelligence.detectors import run_all
from agents.A015_Exchange_Listing_Delisting_Intelligence.tools.diff_engine import diff_snapshots


def doctor() -> int:
    ex = cfg.exchanges()
    det = cfg.detectors_cfg()
    evidence = [e for e in ex if cfg.is_evidence_backed(e)]
    status = [e for e in ex if cfg.has_fetch_status(e)]
    print(f"[A015] exchanges configured : {len(ex)}")
    print(f"[A015] evidence-backed       : {evidence}")
    print(f"[A015] fetchStatus exchanges : {status}")
    print(f"[A015] agent_enabled         : {det.get('agent_enabled')}")
    ok = len(ex) >= 3 and len(evidence) == 3 and det.get("agent_enabled") is True
    print("[A015] doctor:", "OK" if ok else "FAIL")
    return 0 if ok else 1


def _changes(old: dict, new: dict, exchange: str) -> list[dict]:
    changes = diff_snapshots(old, new)
    for c in changes:
        c.exchange = exchange
    return [{"exchange": c.exchange, "symbol": c.symbol, "change_type": c.change_type,
             "old_value": c.old_value, "new_value": c.new_value, "detected_at": c.detected_at}
            for c in changes]


def demo() -> int:
    """Offline mock pipeline (no network) — proves the detector pipeline end to end."""
    old = {"BTC/USDT": {"base": "BTC"}, "ETH/USDT": {"base": "ETH"}}
    new = {"BTC/USDT": {"base": "BTC"}, "ETH/USDT": {"base": "ETH"},
           "PEPE/USDT": {"base": "PEPE"},   # new base  -> NEW_LISTING
           "ETH/BTC": {"base": "ETH"}}      # existing base -> PAIR_CHANGE
    results = run_all(_changes(old, new, "binance"), old_snapshot=old, new_snapshot=new)
    for event_type, reports in results.items():
        print(f"\n=== {event_type} ({len(reports)}) ===")
        for r in reports:
            print(f"  {r['exchange']} {r.get('symbol')}: {r.get('historical_context')}")
    return 0


def _log_events(res: dict) -> None:
    """Detect over one exchange's diff and persist the events. Runs BEFORE the snapshot
    advances (poller contract), so a failed write never loses the diff."""
    res["reports"] = run_all(res["changes"], res["old_snapshot"], res["new_snapshot"])
    flat = [r for reports in res["reports"].values() for r in reports]
    for report in flat:   # what the bus relay needs to state the window, evidence and coverage honestly
        report.update(snapshot_digest=res["old_digest"], old_snapshot_at=res["old_snapshot_at"],
                      observed_at=res["observed_at"], spot_markets=res["spot_markets"])
    event_log.append_events(res["exchange"], flat, res["old_digest"])


def poll(limit: int | None, exchange_ids: list[str] | None = None, partial_ok: bool = False) -> int:
    """Poll, log events durably, print a summary. Exit 1 if any exchange failed — unless
    ``partial_ok`` and at least one succeeded (each exchange's health is in poll_status.json)."""
    from agents.A015_Exchange_Listing_Delisting_Intelligence.tools import ccxt_market_poller as poller
    failed = 0
    results = poller.poll(exchange_ids, limit=limit, on_changes=_log_events)
    for eid, res in results.items():
        if not res["ok"]:
            failed += 1
            print(f"[A015] {eid}: FAILED - {res['error']}")
        elif res["baseline"]:
            print(f"[A015] {eid}: baseline recorded ({len(res['new_snapshot'])} spot markets), no events")
        else:
            counts = {k: len(v) for k, v in res["reports"].items()}
            print(f"[A015] {eid}: {len(res['changes'])} changes since {res['old_snapshot_at']} -> {counts}")
    try:
        poll_status.write_poll_status(results)
    except OSError as exc:   # a status-file problem must not turn a good poll into a failure
        print(f"[A015] could not write poll_status.json: {exc}")
    return 0 if not failed or (partial_ok and failed < len(results)) else 1


def _listed_bases(exchange_ids) -> dict[str, set]:
    """Base assets currently trading per exchange, from the saved poll snapshots."""
    import json
    from pathlib import Path

    from agents.A015_Exchange_Listing_Delisting_Intelligence.core.symbols import base_of

    snap_dir = Path(__file__).resolve().parent / "memory" / "symbol_snapshots"
    out: dict[str, set] = {}
    for eid in set(exchange_ids):
        bases: set = set()
        snap = snap_dir / f"{eid}.json"
        if snap.exists():
            try:
                for symbol in json.loads(snap.read_text(encoding="utf-8")):
                    base = base_of(symbol)
                    if base:
                        bases.add(base)
            except (OSError, ValueError):
                pass
        out[eid] = bases
    return out


def pending(stale_days: float, sources: list[str] | None = None) -> int:
    """Show announced listings NOT yet trading (announced, kaafi din ho gaye, still not listed)."""
    from agents.A015_Exchange_Listing_Delisting_Intelligence.detectors.pending_listing import (
        detect_pending_listings,
    )
    from agents.A015_Exchange_Listing_Delisting_Intelligence.tools.text_feeds import announcements as feeds

    anns = feeds.fetch_all(sources)
    listed = _listed_bases(a.get("exchange") for a in anns)
    reports = detect_pending_listings(anns, listed, stale_days=stale_days)
    # stalest first; unknown-date last
    reports.sort(key=lambda r: (r["days_since_announcement"] is None, -(r["days_since_announcement"] or 0)))
    stale = sum(1 for r in reports if r["is_stale"])
    print(f"[A015] pending (announced, not yet listed): {len(reports)}  |  stale (>= {stale_days}d): {stale}")
    for r in reports:
        age = f"{r['days_since_announcement']}d ago" if r["days_since_announcement"] is not None else "date unknown"
        flag = "  [STALE]" if r["is_stale"] else ""
        print(f"  {r['exchange']:9} {r['token']:12} announced {age}{flag}")
        print(f"            {r['title']}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="a015", description="A015 Exchange Listing/Delisting Intelligence")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Validate config + evidence gating")
    sub.add_parser("demo", help="Offline mock detector pipeline")
    poll_p = sub.add_parser("poll", help="Live poll (needs ccxt + network)")
    poll_p.add_argument("--limit", type=int, default=2)
    poll_p.add_argument("--exchange", action="append", help="exchange id (repeatable); overrides --limit")
    poll_p.add_argument("--partial-ok", action="store_true",
                        help="exit 0 if at least one exchange succeeded (the supervisor uses this)")
    pend_p = sub.add_parser("pending", help="Announced-but-not-yet-listed (needs network)")
    pend_p.add_argument("--stale-days", type=float, default=3.0)
    pend_p.add_argument("--source", action="append", help="okx | binance (repeatable; default: all)")
    args = parser.parse_args(argv)
    if args.command == "doctor":
        return doctor()
    if args.command == "demo":
        return demo()
    if args.command == "poll":
        return poll(None if args.exchange else args.limit, args.exchange, args.partial_ok)
    if args.command == "pending":
        return pending(args.stale_days, args.source)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
