"""The risk flagger (Slice 2a): A015 facts about Binance markets -> ``data/risk/pause_flags.json``.

A recorder of restrictions, not an actor: it may react to ``implemented`` detectors (``min_maturity=
"implemented"``) because a flag only ever *blocks* new entries, and the maturity is stored with the flag.
Idempotent by event_id; the audit event is published BEFORE the file write, so a crash between them is
repaired by redelivery without a second audit event.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from bootstrap import risk_flags
from orchestrator.event_bus.envelope import make_event_id
from orchestrator.event_bus.store import ConsumeStats, EventStore

NAME = "risk_flagger"
TYPES = ["a015.listing.delisted", "a015.listing.new", "a015.market.status_changed"]
EXCHANGE = "binance"
BREAK_TTL = timedelta(hours=24)
PAUSING_STATUSES = {"BREAK", "HALT"}
BATCH = 200
MAX_ATTEMPTS = 20


def decide(event: dict, flags: dict, now) -> tuple[str, dict] | None:
    """('set', flag) | ('clear', {'reason'}) | None. Pure: no I/O."""
    data = event.get("data") or {}
    if data.get("exchange") != EXCHANGE:
        return None
    subject, kind = event["subject"], event["type"]
    maturity = (event.get("detector") or {}).get("maturity")
    status_to = data.get("status_to")
    if kind == "a015.listing.new" or (kind == "a015.market.status_changed" and status_to == "TRADING"):
        if subject not in flags:
            return None
        return "clear", {"reason": "market listed again" if kind == "a015.listing.new" else "market trading again"}
    if kind == "a015.listing.delisted":
        reason, expires = "delisted by the exchange", None
    elif kind == "a015.market.status_changed" and status_to in PAUSING_STATUSES:
        reason, expires = f"market status {status_to}", (now + BREAK_TTL).isoformat()
    else:
        return None
    existing = flags.get(subject)
    if existing and existing["event_id"] == event["event_id"]:
        return None                                       # redelivery
    if existing and existing["expires_at"] is None and expires is not None:
        return None                                       # a temporary pause never shortens a permanent one
    return "set", {"set_at": now.isoformat(), "expires_at": expires, "reason": reason,
                   "event_id": event["event_id"], "event_type": kind, "maturity": maturity}


def flagger_handler(store: EventStore, path: Path | None = None):
    def handle(event: dict) -> None:
        now = store.now()
        flags = risk_flags.active_flags(risk_flags.load_flags(path), now)
        decision = decide(event, flags, now)
        if decision is None:
            return
        action, flag = decision
        trigger = {"event_id": event["event_id"], "trace_id": event["trace_id"]}
        subject = event["subject"]
        if action == "set":
            flags[subject] = flag
            audit = risk_flags.audit_event("flag_set", event_id=make_event_id("flag_set", event["event_id"]),
                                           subject=subject, now=now, reason=flag["reason"], by=NAME,
                                           expires_at=flag["expires_at"], trigger=trigger)
        else:
            del flags[subject]
            audit = risk_flags.audit_event("flag_cleared", event_id=make_event_id("flag_cleared", event["event_id"]),
                                           subject=subject, now=now, reason=flag["reason"], by=NAME, trigger=trigger)
        store.publish(audit)                              # idempotent by event_id
        risk_flags.save_flags(path, flags)

    return handle


def run_once(store: EventStore, path: Path | None = None) -> ConsumeStats:
    handler = flagger_handler(store, path)
    total = ConsumeStats()
    for _ in range(100):
        s = store.consume(NAME, handler, types=TYPES, min_maturity="implemented", batch=BATCH,
                          max_attempts=MAX_ATTEMPTS)
        total.delivered += s.delivered
        total.skipped_other_type += s.skipped_other_type
        total.skipped_low_maturity += s.skipped_low_maturity
        total.failed += s.failed
        total.parked += s.parked
        total.last_seq = s.last_seq or total.last_seq
        if s.delivered + s.skipped_other_type + s.skipped_low_maturity + s.parked == 0:
            break
    return total
