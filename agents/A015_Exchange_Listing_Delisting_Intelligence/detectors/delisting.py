"""DELISTING — a base asset fully disappears from the market set.

Annotation splits by `stated_reason` (README §7.2) and is evidence-gated. The
reason isn't derivable from a structured diff alone (a text feed would supply it),
so from a bare diff it is `unspecified` (honest, low confidence).

When the new snapshot is known, a removed `FOO/QUOTE` whose base `FOO` still trades
is a *pair removal* (PAIR_CHANGE), not a delisting — so it is skipped here.
"""
from __future__ import annotations

from ..core import config_loader as cfg
from ..core.report import INSUFFICIENT, base_report
from ..core.symbols import base_counts, base_of

# Evidence-backed delisting magnitudes, by exchange, for known reasons (README §3.2).
_DELISTING_EVIDENCE = {
    "binance": (-25, "typical crash -25% to -30%, high variance; liquidity depth drives magnitude"),
    "bybit": (-20, "limited data; approximate typical crash"),
    "coinbase": (-15, "limited data; historically mildest reversal"),
}
_KNOWN_REASONS = {"low-liquidity", "regulatory", "compliance"}


def _annotation(exchange_id: str, stated_reason: str) -> tuple[int | None, str]:
    if not cfg.is_evidence_backed(exchange_id):
        return None, INSUFFICIENT
    if stated_reason in _KNOWN_REASONS and exchange_id in _DELISTING_EVIDENCE:
        pct, note = _DELISTING_EVIDENCE[exchange_id]
        return pct, f"{stated_reason} delisting: {note}"
    return None, "Delisting reason not specified; confidence low"


def detect_delisting(changes: list[dict], stated_reason: str = "unspecified",
                     new_snapshot: dict | None = None) -> list[dict]:
    new_bases = base_counts(new_snapshot.keys()) if new_snapshot else None
    reports = []
    for change in changes:
        if change.get("change_type") != "removed":
            continue
        exchange_id, symbol = change.get("exchange"), change.get("symbol")
        if not exchange_id or not symbol:
            continue
        if new_bases is not None:
            base = base_of(symbol)
            if base and new_bases.get(base, 0) >= 1:
                continue  # base still trades -> PAIR_CHANGE (pair removed), not a delisting
        pct, note = _annotation(exchange_id, stated_reason)
        report = base_report("DELISTING", exchange_id, symbol)
        report.update({
            "stated_reason": stated_reason,
            "last_seen_ts": change.get("detected_at"),
            "historical_context": note,
            "median_crash_pct": pct,
        })
        reports.append(report)
    return reports
