"""Pre-trade guard: warn before repeating a known losing pattern.

Given a *proposed* trade (direction + current market context) and the mistakes
memory, return warnings for any recurring, costly mistake this trade would match.
The live engine calls this before entering; it can warn or skip.
"""
from __future__ import annotations

from .memory import MistakeMemory


def _dir_word(d: int) -> str:
    return "long" if d > 0 else "short"


def _candidate_signatures(direction: int, context: dict) -> list[str]:
    """Pre-trade-detectable mistake signatures for this proposed entry."""
    d = direction
    dw = _dir_word(d)
    trend = context.get("trend_regime", 0)
    ext = context.get("dist_from_high50", 0.0)
    vol = context.get("vol_bucket", "mid")
    sigs: list[str] = []
    if (d > 0 and trend < 0) or (d < 0 and trend > 0):
        sigs.append(f"counter-trend|{dw}")
    if d > 0 and ext >= -0.01:
        sigs.append("overextended|long")
    if vol == "low":
        sigs.append(f"chop-whipsaw|{dw}")
    return sigs


def check_trade(direction: int, context: dict, memory: MistakeMemory,
                min_repeats: int = 2) -> list[dict]:
    """Return warnings [{signature, repeats, avg_loss, rule, message}] for a proposed trade."""
    if direction == 0:
        return []
    agg = {g["signature"]: g for g in memory.aggregate()}
    warnings: list[dict] = []
    for sig in _candidate_signatures(direction, context):
        g = agg.get(sig)
        if g and g["repeats"] >= min_repeats:
            warnings.append({
                "signature": sig,
                "repeats": g["repeats"],
                "avg_loss": round(g["avg_loss"], 4),
                "total_loss": round(g["total_loss"], 4),
                "rule": g["rule"],
                "message": (f"⚠️ This {_dir_word(direction)} matches a past mistake "
                            f"'{g['category']}' that lost {g['repeats']}× "
                            f"(avg {g['avg_loss']:.1%}). RULE: {g['rule']}"),
            })
    return warnings
