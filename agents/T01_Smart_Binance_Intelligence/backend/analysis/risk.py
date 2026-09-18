"""Position sizing and risk checks."""
from backend import config


def _stop_distance(price: float, atr: float) -> float:
    """Absolute price distance to the stop.

    Volatility-adaptive when ATR stops are enabled and a real ATR reading is
    available (distance = ATR * ATR_STOP_MULT); otherwise the flat STOP_LOSS_PCT
    of price. Keeping this in one place guarantees position_size and
    stop_loss_price always agree on the stop, so realized risk matches the sizing.
    """
    if config.USE_ATR_STOPS and atr and atr > 0:
        return atr * config.ATR_STOP_MULT
    return price * config.STOP_LOSS_PCT


def _target_distance(price: float, atr: float) -> float:
    """Absolute price distance to the take-profit (ATR-adaptive or flat %)."""
    if config.USE_ATR_STOPS and atr and atr > 0:
        return atr * config.ATR_TP_MULT
    return price * config.TAKE_PROFIT_PCT


def position_size(balance: float, price: float, mode: str = "paper",
                  open_count: int = 0, atr: float = 0.0) -> float:
    """Quantity to trade, sized by per-trade risk and capped by affordability.

    Two independent ceilings; the smaller wins:

    1. **Risk-based size** — a full stop-out costs at most ``risk_pct`` of
       balance:  ``qty = risk_pct * balance / stop_distance``. This is the
       knob the operator turns; realized risk never exceeds it. ``stop_distance``
       is the same volatility-adaptive (ATR) or flat-% distance the actual stop
       uses, so a wider volatility stop automatically shrinks the position.
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
    stop_distance = _stop_distance(price, atr)
    if stop_distance <= 0:
        return 0.0

    qty_risk = (balance * risk_pct) / stop_distance

    slots_left = max(1, config.MAX_CONCURRENT_POSITIONS - open_count)
    max_notional = balance / slots_left
    qty_cap = max_notional / price

    return round(min(qty_risk, qty_cap), 8)


def stop_loss_price(entry: float, side: str = "buy", atr: float = 0.0) -> float:
    dist = _stop_distance(entry, atr)
    if side == "buy":
        return round(entry - dist, 8)
    return round(entry + dist, 8)


def take_profit_price(entry: float, side: str = "buy", atr: float = 0.0) -> float:
    dist = _target_distance(entry, atr)
    if side == "buy":
        return round(entry + dist, 8)
    return round(entry - dist, 8)


def maybe_trail_stop(current_stop: float | None, price: float, entry: float,
                     side: str = "buy") -> float | None:
    """New stop for a profitable long that should trail, else None.

    Only ratchets the stop in the profitable direction (up, for a long) once the
    trade is in profit; it never loosens an existing stop. Returns None when
    trailing is disabled, the trade isn't in profit, or the trailed level would
    not improve on the current stop.
    """
    if not config.TRAIL_ENABLED or side != "buy" or price <= entry:
        return None
    candidate = round(price * (1 - config.TRAIL_PCT), 8)
    if current_stop is None or candidate > current_stop:
        return candidate
    return None


def can_open_position(open_count: int) -> bool:
    return open_count < config.MAX_CONCURRENT_POSITIONS
