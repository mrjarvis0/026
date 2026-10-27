"""Diagnose *why* a losing trade lost — rule-based, honest, no fabrication.

Each losing TradeRecord maps to a Lesson: a category, a human message, a fix
("rule"), and a signature used to detect repeats. Winning trades yield no lesson.
"""
from __future__ import annotations

from dataclasses import dataclass

from .trades import TradeRecord


@dataclass
class Lesson:
    category: str
    message: str
    rule: str            # the corrective rule to follow next time
    signature: str       # for dedup / repeat-counting
    loss_pct: float
    direction: int


def _dir_word(d: int) -> str:
    return "long" if d > 0 else "short"


def diagnose(trade: TradeRecord) -> Lesson | None:
    """Return a Lesson for a losing trade, else None."""
    if not trade.is_loss:
        return None

    c = trade.context
    d = trade.direction
    trend = c.get("trend_regime", 0)
    vol = c.get("vol_bucket", "mid")
    ext = c.get("dist_from_high50", 0.0)
    loss = trade.pnl_pct
    dw = _dir_word(d)

    # 1) counter-trend entry (long below the long-MA, or short above it)
    if (d > 0 and trend < 0) or (d < 0 and trend > 0):
        return Lesson(
            "counter-trend",
            f"Entered {dw} against the long-term trend (price was on the wrong side of the ~200-bar MA). Lost {loss:.1%}.",
            f"Only take {dw} trades when price is on the {'above' if d > 0 else 'below'} side of the 200-bar MA.",
            f"counter-trend|{dw}", loss, d,
        )

    # 2) big adverse move held through -> stop too loose
    if loss <= -0.15:
        return Lesson(
            "loose-stop",
            f"Held a {dw} through a large adverse move ({loss:.1%}) — the stop was too loose.",
            "Cap the per-trade loss with a tighter stop (e.g. exit by -8% to -10%).",
            f"loose-stop|{dw}", loss, d,
        )

    # 3) bought an overextended top (near recent high) then reversed
    if d > 0 and ext >= -0.01:
        return Lesson(
            "overextended",
            f"Bought near the 50-bar high (overextended) and it reversed. Lost {loss:.1%}.",
            "Avoid fresh longs within ~1% of the 50-bar high; wait for a pullback or a clean base.",
            "overextended|long", loss, d,
        )

    # 4) whipsaw in a quiet/low-volatility chop
    if vol == "low" and trade.bars_held <= 3:
        return Lesson(
            "chop-whipsaw",
            f"Entered a {dw} in a low-volatility chop and got whipsawed in {trade.bars_held} bars ({loss:.1%}).",
            "Skip breakout entries when volatility (ATR%) is in its low third — require expansion first.",
            f"chop-whipsaw|{dw}", loss, d,
        )

    # 5) generic loss
    return Lesson(
        "loss",
        f"A {dw} trade lost {loss:.1%} with no single obvious cause (held {trade.bars_held} bars).",
        "Review context; consider tighter risk or a confirmation filter.",
        f"loss|{dw}", loss, d,
    )
