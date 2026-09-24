"""Unified CCXT market poller — one generic poller for all exchanges (README §6).

Per exchange: `fetch_markets()` -> diff against the stored snapshot -> persist the
new snapshot -> return the changes plus both snapshots (the pair-change detector
needs them). `ccxt` is imported lazily so importing this module (e.g. from the
kernel adapter or tests) never requires ccxt or the network.
"""
from __future__ import annotations

from pathlib import Path

from ..core import config_loader as cfg
from .diff_engine import diff_snapshots, load_snapshot, save_snapshot

_SNAPSHOT_DIR = Path(__file__).resolve().parents[1] / "memory" / "symbol_snapshots"


def _init_exchange(exchange_id: str):
    import ccxt  # lazy: only needed for a live poll
    return getattr(ccxt, exchange_id)({"enableRateLimit": True, "timeout": 30000})


def _fetch_markets(exchange, exchange_id: str) -> dict:
    try:
        return {m["symbol"]: m for m in exchange.fetch_markets() if m.get("symbol")}
    except Exception as exc:  # network/exchange error must not crash the poll loop
        print(f"[A015] fetch_markets error for {exchange_id}: {type(exc).__name__}: {exc}")
        return {}


def _to_dict(change) -> dict:
    return {
        "exchange": change.exchange,
        "symbol": change.symbol,
        "change_type": change.change_type,
        "old_value": change.old_value,
        "new_value": change.new_value,
        "detected_at": change.detected_at,
    }


def poll_exchange(exchange_id: str) -> dict:
    """Poll one exchange. Returns {changes, old_snapshot, new_snapshot}."""
    current = _fetch_markets(_init_exchange(exchange_id), exchange_id)
    if not current:
        return {"changes": [], "old_snapshot": {}, "new_snapshot": {}}
    _SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_file = str(_SNAPSHOT_DIR / f"{exchange_id}.json")
    old = load_snapshot(snapshot_file)
    changes = diff_snapshots(old, current)
    for change in changes:
        change.exchange = exchange_id
    save_snapshot(current, snapshot_file)
    return {"changes": [_to_dict(c) for c in changes], "old_snapshot": old, "new_snapshot": current}


def poll(exchange_ids: list[str] | None = None, limit: int | None = None) -> dict[str, dict]:
    """Poll a set of exchanges (default: all configured). `limit` caps the count."""
    ids = exchange_ids or list(cfg.exchanges().keys())
    if limit is not None:
        ids = ids[:limit]
    return {eid: poll_exchange(eid) for eid in ids}
