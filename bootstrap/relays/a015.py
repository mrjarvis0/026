"""A015 -> event bus relay (polling publisher; design spec section 10).

A015 stays bus-unaware: it writes its facts to ``memory/event_log/*.json`` and its poll results to
``memory/poll_status.json``. This relay turns them into validated envelopes and publishes them
(idempotent by ``event_id``, so re-reading is always safe), and copies the poll results into
``source_health`` — the coverage proof for "nothing happened". A bad report or file is recorded
as rejected and skipped; it never stalls the relay.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from agents.A015_Exchange_Listing_Delisting_Intelligence.core import event_log, poll_status
from agents.A015_Exchange_Listing_Delisting_Intelligence.core.symbols import base_of
from orchestrator.event_bus.envelope import EnvelopeError
from orchestrator.event_bus.store import EventStore

EVENT_TYPES = {
    "NEW_LISTING": "a015.listing.new",
    "DELISTING": "a015.listing.delisted",
    "STATUS_CHANGE": "a015.market.status_changed",
    "PAIR_CHANGE": "a015.market.pair_changed",
}
_DATA_FIELDS = {
    "NEW_LISTING": ("exchange", "symbol", "trading_pairs", "historical_context", "median_day_1_effect_pct"),
    "DELISTING": ("exchange", "symbol", "stated_reason", "historical_context", "median_crash_pct"),
    "STATUS_CHANGE": ("exchange", "symbol", "status_from", "status_to", "historical_context"),
    "PAIR_CHANGE": ("exchange", "symbol", "base_asset", "quote_asset", "pair_added", "pair_removed",
                    "historical_context", "median_effect_pct"),
}
_NEEDS_BASE = ("NEW_LISTING", "DELISTING")


@dataclass
class RelayResult:
    published: int = 0
    duplicates: int = 0
    files: int = 0
    health_updated: int = 0
    rejected: list[str] = field(default_factory=list)


def _need(report: dict, key: str):
    if report.get(key) is None:
        raise EnvelopeError(f"report missing {key!r}")
    return report[key]


def to_envelope(report: dict, detector_maturity: dict[str, str]) -> dict:
    """Pure mapping of one A015 report to an envelope (spec section 6)."""
    kind = report.get("event_type")
    if kind not in EVENT_TYPES:
        raise EnvelopeError(f"unknown A015 event_type {kind!r}")
    if kind == "STATUS_CHANGE" and report.get("status_from") == report.get("status_to"):
        # a fact that is not a transition is not an event (older detector versions logged BREAK -> BREAK)
        raise EnvelopeError("STATUS_CHANGE is not a transition (status_from == status_to)")
    event_id = _need(report, "event_id")
    exchange, symbol = _need(report, "exchange"), _need(report, "symbol")
    observed_at = report.get("observed_at") or _need(report, "detected_at")
    old_at = report.get("old_snapshot_at")
    data = {name: report.get(name) for name in _DATA_FIELDS[kind] if name in report}
    if kind in _NEEDS_BASE:
        data["base"] = base_of(symbol)
    return {
        "event_id": event_id,
        "type": EVENT_TYPES[kind],
        "schema_version": 1,
        "source": "A015",
        "subject": f"market:{exchange}:{symbol}",
        "event_time": None,                                   # a poll can only bound it
        "event_window": {"from": old_at, "to": observed_at} if old_at else None,
        "observed_at": observed_at,
        "known_at": None,
        "trace_id": "trc_" + event_id[4:],
        "causation_id": None,
        "detector": {"id": kind, "maturity": detector_maturity.get(kind, "implemented"), "ceiling": None},
        "confidence": None,                                   # A015 reports carry none: cannot be determined
        "coverage": {"complete": True, "as_of": observed_at, "lag_s": None,
                     "note": f"spot only, {report.get('spot_markets', '?')} markets"},
        "evidence": [{"source": f"ccxt.fetch_markets:{exchange}",
                      "locator": f"snapshot:{report.get('snapshot_digest') or 'unknown'}",
                      "retrieved_at": observed_at}],
        "untrusted": False,
        "data": data,
    }


def manifest_detector_maturity() -> dict[str, str]:
    from bootstrap.adapters import a015 as adapter
    detectors = (adapter.load_manifest().get("evidence") or {}).get("detectors") or []
    return {d["id"]: d["maturity"] for d in detectors}


def _record_poll_health(store: EventStore, result: RelayResult, poll_status_path) -> None:
    for exchange_id, st in poll_status.read_poll_status(poll_status_path).items():
        try:
            baseline = bool(st.get("baseline"))
            ok = bool(st["ok"]) and not baseline
            detail = ("baseline poll: a snapshot exists but no diff was checked" if baseline
                      else (st.get("error") or f"ok, {st.get('spot_markets', '?')} spot markets"))
            store.record_health(f"A015:{exchange_id}", ok=ok, detail=detail,
                                at=datetime.fromisoformat(st["polled_at"]))
            result.health_updated += 1
        except (KeyError, TypeError, ValueError, AttributeError):
            result.rejected.append(f"poll_status[{exchange_id}]: malformed entry")


def relay_once(store: EventStore, *, event_log_dir=None, poll_status_path=None,
               detector_maturity: dict[str, str] | None = None) -> RelayResult:
    result = RelayResult()
    maturity = detector_maturity if detector_maturity is not None else manifest_detector_maturity()
    # Health first: it is cheap and is the coverage proof, so a long backlog (the first run after a
    # long gap published thousands of events) can never leave every source "never seen".
    _record_poll_health(store, result, poll_status_path)

    log_dir = Path(event_log_dir or event_log.EVENT_LOG_DIR)
    last = store.get_state("a015", "last_file", "") or ""
    files = sorted(p for p in log_dir.glob("*.json") if p.name > last) if log_dir.is_dir() else []
    for path in files:
        result.files += 1
        try:
            reports = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(reports, list):
                raise ValueError("not a list of reports")
        except (OSError, ValueError) as exc:
            result.rejected.append(f"{path.name}: unreadable ({exc})")
            store.set_state("a015", "last_file", path.name)
            continue
        envelopes = []
        for index, rep in enumerate(reports):
            try:
                envelope = to_envelope(rep, maturity)
                store.validate(envelope)
            except EnvelopeError as exc:
                result.rejected.append(f"{path.name}[{index}]: {exc}")
                continue
            envelopes.append(envelope)
        for _, duplicate in store.publish_many(envelopes):      # one transaction per file
            result.duplicates += duplicate
            result.published += not duplicate
        store.set_state("a015", "last_file", path.name)   # StoreBusy above leaves the mark; re-read is safe
    return result
