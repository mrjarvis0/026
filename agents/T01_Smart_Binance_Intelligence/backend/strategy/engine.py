"""Decision engine with a lightweight self-learning parameter tuner."""
import json

from backend.analysis import indicators, signals
from backend.data import database as db
from backend.trading import performance


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


def save_params(params: dict) -> None:
    save = {k: params[k] for k in DEFAULT_PARAMS if k in params}
    db.set_state("strategy_params", json.dumps(save))


def decide(ohlcv: list[list]) -> signals.Signal:
    """Analyze candles and return a trade signal using current tuned params."""
    df = indicators.compute_all(ohlcv)
    return signals.generate_signal(df, load_params())


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
    if acc < 50:
        params["net_threshold"] = min(3.0, params["net_threshold"] + 0.1)
    elif acc < 65:
        params["net_threshold"] = min(3.0, params["net_threshold"] + 0.05)
    elif acc > 75:
        params["net_threshold"] = max(1.0, params["net_threshold"] - 0.05)

    save_params(params)
    return params
