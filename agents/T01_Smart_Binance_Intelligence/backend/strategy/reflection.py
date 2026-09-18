"""Per-trade loss attribution + targeted self-correction (roadmap #16).

Where `engine.self_tune()` nudges the ONE global `net_threshold` from aggregate
accuracy, this asks *why* recent trades lost — the sub-signal family that opened
each one, the market regime at entry (trend vs chop, from ADX), and how it exited
(stop-loss / take-profit / signal) — then corrects the **specific** cause and
leaves everything else alone:

- losses clustering in a choppy/low-ADX regime  -> raise `adx_min` (regime filter),
- losses clustering on one sub-signal family      -> down-weight *that* family,
- losses mostly from stop-outs                     -> widen the ATR stop.

Each correction targets a *different* knob than `self_tune`, so the two learning
loops never fight over the same dial.
"""
import logging
from collections import Counter

from backend import config
from backend.data import database as db
from backend.strategy import engine

log = logging.getLogger("trading.reflection")


def diagnose(mode: str = "paper") -> dict | None:
    """A read-only diagnosis of recent losses, or None when there isn't enough
    signal yet (too few trades, or the recent loss rate isn't elevated). Split out
    so it can be surfaced on the dashboard and tested without side effects."""
    closed = db.get_closed_trades(mode=mode, limit=30)
    real = [t for t in closed if t.get("exit_reason") != "reset"]
    if len(real) < config.REFLECT_MIN_TRADES:
        return None
    losses = [t for t in real if (t.get("pnl") or 0.0) < 0]
    if not losses:
        return None
    loss_rate = len(losses) / len(real)
    if loss_rate < config.REFLECT_LOSS_RATE:
        return None
    return {
        "loss_rate": round(loss_rate, 3),
        "n_losses": len(losses),
        "by_regime": dict(Counter((t.get("entry_regime") or "unknown") for t in losses)),
        "by_factor": dict(Counter((t.get("entry_factor") or "unknown") for t in losses)),
        "by_exit": dict(Counter((t.get("exit_reason") or "unknown") for t in losses)),
    }


def diagnose_and_correct(mode: str = "paper") -> list[str]:
    """Diagnose the dominant loss cause(s) and apply targeted corrections to the
    persisted strategy params. Returns the list of changes made (empty if none).

    All corrections are bounded and only tighten (raise a filter, down-weight, or
    widen a stop) — the conservative direction — so a bad diagnosis can't make the
    bot reckless."""
    d = diagnose(mode)
    if not d:
        return []
    n = d["n_losses"]
    params = engine.load_params()
    changes: list[str] = []

    # 1) Concentrated in chop -> add/raise a regime filter, don't trade less overall.
    if d["by_regime"].get("chop", 0) >= 0.5 * n:
        new = min(30.0, float(params.get("adx_min", 0.0) or 0.0) + 5.0)
        if new != (params.get("adx_min") or 0.0):
            params["adx_min"] = new
            changes.append(f"adx_min->{new:.0f}")

    # 2) Concentrated on one sub-signal family -> down-weight only that family.
    fac = {k: v for k, v in d["by_factor"].items() if k not in ("unknown", "", None)}
    if fac:
        top, cnt = max(fac.items(), key=lambda kv: kv[1])
        if cnt >= 0.5 * n:
            fw = dict(params.get("factor_weights") or {})
            new = round(max(0.5, float(fw.get(top, 1.0)) - 0.2), 2)
            if new != round(float(fw.get(top, 1.0)), 2):
                fw[top] = new
                params["factor_weights"] = fw
                changes.append(f"weight[{top}]->{new}")

    # 3) Mostly stop-outs -> stops are too tight for this tape; widen the ATR stop.
    if d["by_exit"].get("stop_loss", 0) >= 0.6 * n:
        base = float(params.get("atr_stop_mult", 0.0) or 0.0) or config.ATR_STOP_MULT
        new = round(min(3.0, base + 0.25), 2)
        if new != round(float(params.get("atr_stop_mult", 0.0) or 0.0), 2):
            params["atr_stop_mult"] = new
            changes.append(f"atr_stop_mult->{new}")

    if changes:
        engine.save_params(params)
        log.info("reflection: recent loss_rate %.0f%% (%d losses) -> %s",
                 d["loss_rate"] * 100, n, ", ".join(changes))
    return changes
