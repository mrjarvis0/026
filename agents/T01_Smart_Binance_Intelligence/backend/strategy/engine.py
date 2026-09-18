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
    """Analyze candles and return a trade signal using current tuned params."""
    df = indicators.compute_all(ohlcv)
    return signals.generate_signal(df, load_params())


def self_tune() -> dict:
    """Adjust parameters dynamically using real historical performance metrics.

    Uses actual feedback (Sharpe Ratio and Profit Factor) from closed paper trades
    to adjust the required confidence threshold. High quality performance loosens
    the threshold to capture more trades, poor performance tightens it to wait for
    higher-quality setups.
    """
    metrics = performance.compute_metrics("paper")
    params = load_params()
    total = metrics.get("total_trades", 0)
    last = int(db.get_state("tune_last_trades", "0") or 0)

    # Learn once per newly-closed trade, never on wall-clock alone
    if total < 10 or total <= last:
        return params
    db.set_state("tune_last_trades", str(total))

    sharpe = metrics.get("sharpe", 0.0)
    pf = metrics.get("profit_factor", 0.0)

    # Evaluate risk-adjusted returns (Sharpe) and absolute gross profitability
    if sharpe < 0.5 or pf < 1.0:
        # Struggling to maintain edge: tighten threshold to filter out weak signals
        params["net_threshold"] = min(3.0, params["net_threshold"] + 0.1)
    elif sharpe > 1.5 and pf > 1.5:
        # Edge is exceptionally strong: loosen threshold to capture more volume
        params["net_threshold"] = max(1.0, params["net_threshold"] - 0.05)
    else:
        # Performance is middling/acceptable, maintain current tuning
        pass

    save_params(params)
    return params
