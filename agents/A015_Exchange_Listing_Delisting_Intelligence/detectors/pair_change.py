"""PAIR_CHANGE — an already-listed base asset gains/loses a specific trading pair,
without the base asset itself being newly listed or fully delisted (README §7.4).

This needs snapshot context to be honest: an added `FOO/USDT` is a *pair change*
only if `FOO` already traded (some other pair) before; otherwise it's a NEW_LISTING.
A removed pair is a *pair change* only if the base still trades after; otherwise it's
a DELISTING. Without both snapshots the distinction cannot be made, so we return []
(026 discipline: "cannot be determined" over a guess) — the old build's guess-every-
add/remove behaviour, which double-counted listings/delistings, is gone.
"""
from __future__ import annotations

from ..core import config_loader as cfg  # noqa: F401  (kept for symmetry / future per-exchange rules)
from ..core.report import INSUFFICIENT, base_report
from ..core.symbols import base_counts, base_of

_CFG_NOTE = ("One documented case (CFG multi-pair add -> +60% within minutes); "
             "smaller-magnitude sibling of NEW_LISTING, low confidence")


def detect_pair_change(changes: list[dict], old_snapshot: dict | None = None,
                       new_snapshot: dict | None = None) -> list[dict]:
    if old_snapshot is None or new_snapshot is None:
        return []  # cannot distinguish a pair change from a listing/delisting
    old_bases = base_counts(old_snapshot.keys())
    new_bases = base_counts(new_snapshot.keys())

    reports = []
    for change in changes:
        change_type = change.get("change_type")
        exchange_id, symbol = change.get("exchange"), change.get("symbol")
        if change_type not in ("added", "removed") or not exchange_id or not symbol:
            continue
        base = base_of(symbol)
        if base is None:
            continue

        if change_type == "added":
            if old_bases.get(base, 0) < 1:
                continue  # base is newly listed -> NEW_LISTING, not a pair change
            pair_added, pair_removed = True, False
        else:  # removed
            if new_bases.get(base, 0) < 1:
                continue  # base fully gone -> DELISTING, not a pair change
            pair_added, pair_removed = False, True

        report = base_report("PAIR_CHANGE", exchange_id, symbol)
        report.update({
            "base_asset": base,
            "quote_asset": symbol.split("/", 1)[1],
            "pair_added": pair_added,
            "pair_removed": pair_removed,
            "historical_context": _CFG_NOTE if exchange_id == "binance" else INSUFFICIENT,
            "median_effect_pct": None,
        })
        reports.append(report)
    return reports
