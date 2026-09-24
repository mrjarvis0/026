"""NEW_LISTING — a genuinely new base asset appears in the market set.

Historical annotation is evidence-gated (README §3.4): only the three studied
exchanges get a quantified effect; everyone else is `insufficient sample`.

When the previous snapshot is known, an added `FOO/QUOTE` whose base `FOO` already
traded is a *pair add* (PAIR_CHANGE), not a new listing — so it is skipped here and
the two detectors never double-count. Without a snapshot, every add is flagged
(best effort).
"""
from __future__ import annotations

from ..core import config_loader as cfg
from ..core.report import INSUFFICIENT, base_report
from ..core.symbols import base_counts, base_of

# The ONLY evidence-backed listing annotations (README §3.1). Never borrowed elsewhere.
_LISTING_EVIDENCE = {
    "binance": (41, "~41% median day-1 effect, wide variance, pump-then-dump (~98% eventual giveback)"),
    "bybit": (61, "~61% median day-1 effect, ~92% dump rate"),
    "coinbase": (25, "~20-30% median effect, historically mildest reversal"),
}


def _annotation(exchange_id: str) -> tuple[int | None, str]:
    if cfg.is_evidence_backed(exchange_id) and exchange_id in _LISTING_EVIDENCE:
        return _LISTING_EVIDENCE[exchange_id]
    return None, INSUFFICIENT


def detect_new_listing(changes: list[dict], old_snapshot: dict | None = None) -> list[dict]:
    old_bases = base_counts(old_snapshot.keys()) if old_snapshot else None
    reports = []
    for change in changes:
        if change.get("change_type") != "added":
            continue
        exchange_id, symbol = change.get("exchange"), change.get("symbol")
        if not exchange_id or not symbol:
            continue
        if old_bases is not None:
            base = base_of(symbol)
            if base and old_bases.get(base, 0) >= 1:
                continue  # existing base gaining a pair -> PAIR_CHANGE, not a new listing
        pct, note = _annotation(exchange_id)
        report = base_report("NEW_LISTING", exchange_id, symbol)
        report.update({
            "first_seen_ts": change.get("detected_at"),
            "trading_pairs": [symbol],
            "historical_context": note,
            "median_day_1_effect_pct": pct,
        })
        reports.append(report)
    return reports
