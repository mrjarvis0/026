"""Symbol helpers — extract a pair's base asset and count pairs per base.

Used to keep NEW_LISTING / DELISTING / PAIR_CHANGE mutually exclusive: an added
`FOO/USDT` is a genuinely new listing only if `FOO` didn't already trade.
"""
from __future__ import annotations


def base_of(symbol: str) -> str | None:
    return symbol.split("/", 1)[0] if symbol and "/" in symbol else None


def base_counts(symbols) -> dict[str, int]:
    counts: dict[str, int] = {}
    for sym in symbols:
        base = base_of(sym)
        if base:
            counts[base] = counts.get(base, 0) + 1
    return counts
