"""Unified CCXT market poller — one generic poller for all exchanges (README §6).

Per exchange: `fetch_markets()` -> keep tracked market types -> diff against the stored
snapshot -> hand the result to ``on_changes`` (which logs the events durably) -> and only
THEN advance the snapshot. If logging fails the snapshot stays put and the same diff is
re-detected next poll (at-least-once; event ids are stable, see core/event_log.py).
`ccxt` is imported lazily so importing this module (e.g. from the kernel adapter or tests)
never requires ccxt or the network.

Honest by construction: a failed fetch, a first poll and a quiet exchange are three different
results (`ok`, `baseline`, empty `changes`) — never one empty list.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from ..core import config_loader as cfg
from .diff_engine import diff_snapshots, load_snapshot, save_snapshot

_SNAPSHOT_DIR = Path(__file__).resolve().parents[1] / "memory" / "symbol_snapshots"

# Spot only: dated futures/options roll over constantly (noise), and a derivative's base
# ("BTC/USDT:USDT" -> BTC) would otherwise count as an already-listed asset.
TRACKED_MARKET_TYPES = ("spot",)
# A fetch returning less than this share of the previous snapshot is a truncated list, not a
# wave of delistings: refuse it (keep the snapshot) instead of emitting mass false DELISTINGs.
MIN_KEEP_FRACTION = 0.5


def _init_exchange(exchange_id: str):
    import ccxt  # lazy: only needed for a live poll
    return getattr(ccxt, exchange_id)({"enableRateLimit": True, "timeout": 30000})


def _tracked(markets: dict) -> dict:
    return {s: m for s, m in markets.items() if m.get("type", "spot") in TRACKED_MARKET_TYPES}


def _to_dict(change) -> dict:
    return {
        "exchange": change.exchange,
        "symbol": change.symbol,
        "change_type": change.change_type,
        "old_value": change.old_value,
        "new_value": change.new_value,
        "detected_at": change.detected_at,
    }


def _digest(snapshot: dict) -> str:
    return hashlib.sha1(json.dumps(snapshot, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:12]


def _result(exchange_id: str, **fields) -> dict:
    base = {"exchange": exchange_id, "ok": True, "error": None, "baseline": False, "changes": [],
            "old_snapshot": {}, "new_snapshot": {}, "old_digest": "", "old_snapshot_at": None,
            "observed_at": datetime.now(timezone.utc).isoformat(), "spot_markets": 0}
    return {**base, **fields}


def _failed(exchange_id: str, error: str) -> dict:
    return _result(exchange_id, ok=False, error=error)


def poll_exchange(exchange_id: str, on_changes: Callable[[dict], None] | None = None) -> dict:
    """Poll one exchange. Returns {exchange, ok, error, baseline, changes, old_snapshot,
    new_snapshot, old_digest, old_snapshot_at}. ``on_changes(result)`` runs before the
    snapshot advances; if it raises, the poll is reported failed and the snapshot is kept."""
    try:
        markets = _init_exchange(exchange_id).fetch_markets()
        current = _tracked({m["symbol"]: m for m in markets if m.get("symbol")})
    except Exception as exc:  # network/exchange error must not crash the poll loop
        return _failed(exchange_id, f"fetch_markets {type(exc).__name__}: {exc}")
    if not current:
        return _failed(exchange_id, "exchange returned no tracked markets")

    _SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = _SNAPSHOT_DIR / f"{exchange_id}.json"
    old = _tracked(load_snapshot(str(path)))
    if not old:  # first poll (or unreadable snapshot): record a baseline, claim nothing
        save_snapshot(current, str(path))
        return _result(exchange_id, baseline=True, new_snapshot=current, spot_markets=len(current))
    if len(current) < MIN_KEEP_FRACTION * len(old):
        return _failed(exchange_id, f"market list shrank {len(old)} -> {len(current)}; "
                                    "treated as a failed fetch, snapshot kept")

    changes = diff_snapshots(old, current)
    for change in changes:
        change.exchange = exchange_id
    result = _result(
        exchange_id, changes=[_to_dict(c) for c in changes], old_snapshot=old, new_snapshot=current,
        spot_markets=len(current),
        old_digest=_digest(old) if changes else "",
        old_snapshot_at=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat())
    if on_changes is not None:
        try:
            on_changes(result)
        except Exception as exc:
            return _failed(exchange_id, f"on_changes failed ({type(exc).__name__}: {exc}); snapshot kept")
    save_snapshot(current, str(path))
    return result


def poll(exchange_ids: list[str] | None = None, limit: int | None = None,
         on_changes: Callable[[dict], None] | None = None) -> dict[str, dict]:
    """Poll a set of exchanges (default: all configured). `limit` caps the count."""
    ids = exchange_ids or list(cfg.exchanges().keys())
    if limit is not None:
        ids = ids[:limit]
    return {eid: poll_exchange(eid, on_changes) for eid in ids}
