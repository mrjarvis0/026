"""Position sizing and risk checks."""
from backend import config


def position_size(balance: float, price: float, mode: str = "paper",
                  open_count: int = 0, atr: float = 0.0) -> float:
    """Quantity to trade, sized by per-trade risk and capped by affordability.

    Two independent ceilings; the smaller wins:

    1. **Risk-based size** — a full stop-out costs at most ``risk_pct`` of
       balance:  ``qty = risk_pct * balance / (price * stop_pct)``. This is the
       knob the operator turns; realized risk never exceeds it.
    2. **Affordability cap** — split the *free* balance across the position
       slots still open, so ``MAX_CONCURRENT_POSITIONS`` can all fit in cash.
       This replaces the old fixed 0.30 notional cap, which silently dominated
       for every default and made the risk knob inert. The cap is now derived
       from concurrency, and the risk knob governs whenever the risk-based size
       is the smaller of the two (e.g. a wider stop or a lower risk_pct).
    """
    if price <= 0 or balance <= 0:
        return 0.0
    risk_pct = (config.RISK_PER_TRADE_PAPER if mode == "paper"
                else config.RISK_PER_TRADE_REAL)

    if atr > 0:
        # Dynamic risk sizing based on ATR volatility
        stop_distance = atr * 2.0
    else:
        stop_distance = price * config.STOP_LOSS_PCT

    if stop_distance <= 0:
        return 0.0

    qty_risk = (balance * risk_pct) / stop_distance

    slots_left = max(1, config.MAX_CONCURRENT_POSITIONS - open_count)
    max_notional = balance / slots_left
    qty_cap = max_notional / price

    return round(min(qty_risk, qty_cap), 8)


def stop_loss_price(entry: float, side: str = "buy", atr: float = 0.0) -> float:
    stop_dist = (atr * 2.0) if atr > 0 else (entry * config.STOP_LOSS_PCT)
    if side == "buy":
        return round(entry - stop_dist, 8)
    return round(entry + stop_dist, 8)


def take_profit_price(entry: float, side: str = "buy", atr: float = 0.0) -> float:
    tp_dist = (atr * 3.0) if atr > 0 else (entry * config.TAKE_PROFIT_PCT)
    if side == "buy":
        return round(entry + tp_dist, 8)
    return round(entry - tp_dist, 8)


def can_open_position(open_count: int) -> bool:
    return open_count < config.MAX_CONCURRENT_POSITIONS
