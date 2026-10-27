"""Decision engine with a lightweight self-learning parameter tuner."""
import json
import sys
from pathlib import Path

from backend.analysis import indicators, signals
from backend.data import database as db
from backend.trading import performance
from backend import config as _cfg

# ---------------------------------------------------------------------------
# T03 Strategy Intelligence Hub — optional consensus overlay
# ---------------------------------------------------------------------------

def _t03_root() -> Path | None:
    """Locate T03 sibling directory using the fleet layout (agents/ siblings)."""
    t01_root = Path(__file__).resolve().parent.parent.parent
    candidate = t01_root.parent / "T03_Strategy_Intelligence_Hub"
    return candidate if candidate.is_dir() else None


def _t03_consensus() -> tuple[int, float]:
    """Return (net_direction, strength) from T03's 8 strategy agents.

    net_direction: +1 (majority LONG), -1 (majority SHORT), 0 (neutral/chop)
    strength: fraction of strategies agreeing (0.0–1.0)
    Returns (0, 0.0) silently on any failure.
    """
    if not _cfg.T03_ENABLED:
        return 0, 0.0
    try:
        t03 = _t03_root()
        if t03 is None:
            return 0, 0.0
        t03_str = str(t03)
        if t03_str not in sys.path:
            sys.path.insert(0, t03_str)
        from bridge import scan_consensus  # noqa: PLC0415
        c = scan_consensus(_cfg.T03_SYMBOL, timeframe=_cfg.T03_TIMEFRAME, use_cache=True)
        total_active = c["long"] + c["short"]
        if total_active == 0:
            return 0, 0.0
        strength = max(c["long"], c["short"]) / max(total_active, 1)
        direction = 1 if c["bias"] == "LONG" else (-1 if c["bias"] == "SHORT" else 0)
        return direction, round(strength, 3)
    except Exception:
        return 0, 0.0


DEFAULT_PARAMS = {
    "rsi_buy": 45.0,
    "rsi_sell": 60.0,
    "net_threshold": 1.0,
    "macd_eps": 0.0002,
    "trend_band": 0.001,
    # Tuned by the loss-reflection engine (roadmap #16); all default to no-op so
    # behaviour is unchanged until a diagnosed losing streak adjusts them.
    "adx_min": 0.0,             # regime gate (block entries when ADX < this)
    "atr_stop_mult": 0.0,       # 0 = use config.ATR_STOP_MULT; >0 overrides (wider stops)
    "factor_weights": {},       # per-family score multipliers (down-weight a losing sub-signal)
}


def load_params() -> dict:
    raw = db.get_state("strategy_params")
    if raw:
        try:
            p = dict(DEFAULT_PARAMS)
            loaded = json.loads(raw)
            # migrate away from the old min_confidence key
            loaded.pop("min_confidence", None)
            p.update(loaded)
            return p
        except json.JSONDecodeError:
            pass
    return dict(DEFAULT_PARAMS)


def _describe_change(old: dict, new: dict) -> str:
    """One-line diff of two param snapshots, e.g. 'net_threshold 1.0->1.1, adx_min 0->5'."""
    parts = []
    for k in DEFAULT_PARAMS:
        o, n = old.get(k), new.get(k)
        if o != n:
            parts.append(f"{k} {o}->{n}")
    return ", ".join(parts) or "params updated"


def save_params(params: dict, source: str = "manual", reason: str = "") -> None:
    """Persist tuned params, and journal the change in param_history (F3) — but
    only when the snapshot actually differs, so read-only reloads make no noise."""
    old = load_params()
    save = {k: params[k] for k in DEFAULT_PARAMS if k in params}
    db.set_state("strategy_params", json.dumps(save))
    new = load_params()
    if new != old:
        db.insert_param_history(source, reason or _describe_change(old, new),
                                json.dumps(new))


def decide(ohlcv: list[list]) -> signals.Signal:
    """Analyze candles and return a trade signal using current tuned params.

    T03 soft veto: if T03's 8-strategy consensus strongly disagrees with T01's
    signal (opposite direction, strength >= 0.75), the signal is held. T03 is
    optional — fails silently when unavailable.
    """
    df = indicators.compute_all(ohlcv)
    sig = signals.generate_signal(df, load_params())

    # T03 consensus overlay (soft veto, never modifies confidence upward)
    if sig.action in ("buy", "sell") and _cfg.T03_ENABLED:
        t1_dir = 1 if sig.action == "buy" else -1
        t3_dir, t3_str = _t03_consensus()
        if t3_dir != 0 and t3_dir != t1_dir and t3_str >= 0.75:
            # Strong disagreement → hold
            details = {**(sig.details or {}), "t03_veto": True,
                       "t03_direction": t3_dir, "t03_strength": t3_str}
            return signals.Signal(
                action="hold",
                confidence=0.0,
                reason=f"T03 veto: {sig.action} blocked (T03 strength={t3_str:.2f})",
                price=sig.price,
                details=details,
            )
        elif t3_dir != 0:
            # Note agreement or mild disagreement in details only
            details = {**(sig.details or {}), "t03_direction": t3_dir,
                       "t03_strength": t3_str, "t03_agrees": t3_dir == t1_dir}
            return signals.Signal(
                action=sig.action, confidence=sig.confidence,
                reason=sig.reason, price=sig.price, details=details,
            )

    return sig


def predict_scenarios(df) -> dict:
    """Foresight telemetry: what a conservative / standard / aggressive threshold
    would each decide on the current bar. **Non-acting** — the bot always trades on
    the standard tuned signal (bot.py). This just surfaces "aggressive would buy,
    standard holds" on the dashboard, without the earlier version's bug where it
    silently acted on the loosest threshold (confidence is threshold-independent,
    so a confidence sort there was a no-op that always picked 'aggressive')."""
    base = load_params()
    variants = {
        "conservative": dict(base, net_threshold=base["net_threshold"] + 0.5),
        "standard": base,
        "aggressive": dict(base, net_threshold=max(1.0, base["net_threshold"] - 0.5)),
    }
    out = {}
    for name, pp in variants.items():
        sig = signals.generate_signal(df, pp)
        out[name] = {
            "action": sig.action,
            "net": sig.details.get("net_score"),
            "threshold": round(pp["net_threshold"], 2),
            "confidence": round(sig.confidence, 2),
        }
    return out


def self_tune() -> dict:
    """Adjust the net-score threshold from recent paper-trading accuracy.

    Weak accuracy → demand a stronger net score (fewer, higher-quality
    trades). Strong accuracy → loosen slightly to trade more often.
    Threshold is clamped to a sane [1.0, 3.0] band so the engine never
    goes fully silent or hyperactive.
    """
    metrics = performance.compute_metrics("paper")
    params = load_params()
    total = metrics["total_trades"]
    last = int(db.get_state("tune_last_trades", "0") or 0)

    # Learn once per newly-closed trade, never on wall-clock alone: if no new
    # trade has closed since the last tune, leave the threshold untouched.
    if total < 10 or total <= last:
        return params
    db.set_state("tune_last_trades", str(total))

    acc = metrics["accuracy"]
    before = params["net_threshold"]
    if acc < 50:
        params["net_threshold"] = min(3.0, params["net_threshold"] + 0.1)
    elif acc < 65:
        params["net_threshold"] = min(3.0, params["net_threshold"] + 0.05)
    elif acc > 75:
        params["net_threshold"] = max(1.0, params["net_threshold"] - 0.05)

    save_params(params, source="self_tune",
                reason=(f"accuracy {acc:.1f}% over {total} paper trades: "
                        f"net_threshold {before:.2f}->{params['net_threshold']:.2f}"))
    return params
