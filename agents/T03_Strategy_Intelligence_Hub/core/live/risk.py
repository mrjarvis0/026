"""RiskEngine — the "never let the account go to zero" enforcer.

The user's hard rule for the futures scalper: *the money must never go to zero, at
any cost.* That goal is in direct conflict with "max leverage" (max leverage is the
fastest road to zero), so this module makes capital-preservation the OVERRIDING rule:

- **Position sizing by risk, not by leverage.** Each trade risks at most
  `risk_per_trade_pct` of equity given its stop distance — so a string of losses bleeds
  slowly instead of blowing up. Leverage is *capped* (never maxed).
- **Circuit breakers** halt trading before catastrophe: a daily-loss limit, a max
  drawdown from peak, and an absolute equity floor.

**Honest caveat (R-E.5):** with leverage, gaps/liquidations can occasionally exceed a
stop, so no leveraged system is 100% ruin-proof. But bounded leverage + tiny per-trade
risk + circuit breakers push the probability of ruin very low. That is what "never zero"
means in practice here — not a mathematical guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class RiskLimits:
    max_leverage: float = 3.0          # hard cap on notional/equity (NOT maxed)
    risk_per_trade_pct: float = 0.01   # risk <= 1% of equity per trade
    daily_loss_limit_pct: float = 0.05 # halt for the day at -5% on the day
    max_drawdown_pct: float = 0.25     # halt entirely at -25% from peak equity
    equity_floor: float = 0.0          # absolute floor in quote ccy (0 = disabled)
    max_trades_per_day: int = 50       # scalpers trade a lot — still cap it

    @classmethod
    def from_dict(cls, d: dict | None) -> "RiskLimits":
        d = d or {}
        return cls(**{k: type(getattr(cls, k, 0.0))(d[k]) for k in d
                      if k in cls.__dataclass_fields__})


@dataclass
class RiskState:
    peak_equity: float = 0.0
    day: str = ""
    day_start_equity: float = 0.0
    trades_today: int = 0
    halted: bool = False
    halt_reason: str = ""


class RiskEngine:
    def __init__(self, limits: RiskLimits, state: RiskState | None = None) -> None:
        self.limits = limits
        self.state = state or RiskState()

    # -- housekeeping --
    def update_equity(self, equity: float) -> None:
        """Call each cycle with current equity: rolls the day and tracks peak."""
        today = date.today().isoformat()
        if self.state.day != today:
            self.state.day = today
            self.state.day_start_equity = equity
            self.state.trades_today = 0
            # a new day clears a *daily-loss* halt, but not a drawdown/floor halt
            if self.state.halt_reason.startswith("daily-loss"):
                self.state.halted = False
                self.state.halt_reason = ""
        self.state.peak_equity = max(self.state.peak_equity, equity)

    # -- circuit breakers --
    def can_trade(self, equity: float) -> tuple[bool, str]:
        """Whether a NEW position may be opened now (exits are always allowed)."""
        lim, st = self.limits, self.state
        if lim.equity_floor > 0 and equity <= lim.equity_floor:
            return self._halt(f"equity-floor: {equity:.2f} <= {lim.equity_floor:.2f}")
        if st.peak_equity > 0:
            dd = 1.0 - equity / st.peak_equity
            if dd >= lim.max_drawdown_pct:
                return self._halt(f"max-drawdown: {dd:.1%} >= {lim.max_drawdown_pct:.0%}")
        if st.day_start_equity > 0:
            day_pnl = equity / st.day_start_equity - 1.0
            if day_pnl <= -lim.daily_loss_limit_pct:
                return False, f"daily-loss limit hit ({day_pnl:.1%}); halted until tomorrow"
        if st.trades_today >= lim.max_trades_per_day:
            return False, f"max_trades_per_day ({lim.max_trades_per_day}) reached"
        if st.halted:
            return False, f"halted: {st.halt_reason}"
        return True, "ok"

    def _halt(self, reason: str) -> tuple[bool, str]:
        self.state.halted = True
        self.state.halt_reason = reason
        return False, f"HALTED — {reason}"

    # -- the core: how big a position keeps per-trade risk within the cap --
    def position_size(self, equity: float, price: float, stop_distance_pct: float) -> float:
        """Units to trade so a stop-out costs <= risk_per_trade_pct of equity, capped by leverage.

        stop_distance_pct: fractional distance from entry to stop (e.g. 0.01 = 1%).
        """
        if price <= 0 or stop_distance_pct <= 0:
            return 0.0
        risk_amount = equity * self.limits.risk_per_trade_pct
        per_unit_risk = price * stop_distance_pct
        units = risk_amount / per_unit_risk
        # cap notional by max leverage
        max_units_by_lev = (equity * self.limits.max_leverage) / price
        units = min(units, max_units_by_lev)
        return max(0.0, units)

    def register_trade(self) -> None:
        self.state.trades_today += 1
