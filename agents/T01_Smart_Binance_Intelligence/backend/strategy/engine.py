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
    """Analyze candles and return a trade signal using current tuned params.
    It evaluates multiple scenarios (Conservative, Standard, Aggressive) and
    picks the best signal (highest confidence if actions align, or defaulting to Standard).
    """
    df = indicators.compute_all(ohlcv)

    current_params = load_params()

    scenarios = {
        "standard": dict(current_params),
        "conservative": dict(current_params, net_threshold=current_params["net_threshold"] + 0.5),
        "aggressive": dict(current_params, net_threshold=max(1.0, current_params["net_threshold"] - 0.5)),
    }

    evaluations = {}
    for name, p in scenarios.items():
        evaluations[name] = signals.generate_signal(df, p)

    # Default to standard
    best_signal = evaluations["standard"]

    # If aggressive or conservative has a higher confidence for the SAME action, prefer it.
    # We mainly just want to pick the scenario that gives us the most confident actionable signal.
    actionable_signals = [sig for sig in evaluations.values() if sig.action in ("buy", "sell")]

    if actionable_signals:
        # Sort by confidence descending
        actionable_signals.sort(key=lambda s: s.confidence, reverse=True)
        best_signal = actionable_signals[0]

    return best_signal


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
