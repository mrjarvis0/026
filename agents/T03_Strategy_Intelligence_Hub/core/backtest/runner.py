"""Backtest runner.

Default engine is a **controlled vectorized backtester** (numpy/pandas only): it
applies each bar's target position on the *next* bar (`shift(1)`) so there is no
look-ahead, charges commission on turnover, and builds an equity curve. This keeps
control flow explicit and dependency-light (Constitution R-C.5 / R-D.8).

`engine="backtesting"` opts into the `backtesting.py` library for intrabar order
fills; if that package is missing it falls back to the vectorized engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..strategy_base import StrategySpec
from .metrics import benchmark_metrics, compute_metrics


@dataclass
class BacktestResult:
    equity: pd.Series
    strat_returns: pd.Series
    applied_pos: pd.Series
    asset_returns: pd.Series
    metrics: dict = field(default_factory=dict)
    engine: str = "vectorized"
    meta: dict = field(default_factory=dict)

    def equity_frame(self) -> pd.DataFrame:
        """Strategy equity vs buy-&-hold, normalized to the same starting cash."""
        start = float(self.equity.iloc[0])
        bh = (1.0 + self.asset_returns).cumprod() * start
        return pd.DataFrame({"strategy": self.equity, "buy_and_hold": bh})

    def save(self, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        self.equity_frame().to_csv(out_dir / "equity_curve.csv")


def _vectorized(
    strategy: StrategySpec,
    data: pd.DataFrame,
    cash: float,
    commission: float,
    periods_per_year: int,
    risk_free_rate: float,
) -> BacktestResult:
    data = strategy.validate_ohlcv(data)
    signals = strategy.generate_signals(data)
    if "position" not in signals.columns:
        raise ValueError("generate_signals must return a 'position' column")

    target = signals["position"].reindex(data.index).fillna(0.0).clip(-1, 1)
    if "size" in signals.columns:
        size = signals["size"].reindex(data.index).fillna(1.0).clip(0, 1)
        target = target * size

    # act on the NEXT bar -> no look-ahead
    applied_pos = target.shift(1).fillna(0.0)
    asset_returns = data["Close"].pct_change().fillna(0.0)

    gross = applied_pos * asset_returns
    turnover = applied_pos.diff().abs().fillna(applied_pos.abs())
    strat_returns = gross - turnover * commission
    equity = (1.0 + strat_returns).cumprod() * cash

    metrics = compute_metrics(
        equity, strat_returns, applied_pos, asset_returns, periods_per_year, risk_free_rate
    )
    metrics.update(benchmark_metrics(data["Close"], periods_per_year))
    return BacktestResult(
        equity=equity,
        strat_returns=strat_returns,
        applied_pos=applied_pos,
        asset_returns=asset_returns,
        metrics=metrics,
        engine="vectorized",
        meta={"cash": cash, "commission": commission, "periods_per_year": periods_per_year},
    )


def _backtesting_py(
    strategy: StrategySpec,
    data: pd.DataFrame,
    cash: float,
    commission: float,
    periods_per_year: int,
    risk_free_rate: float,
) -> BacktestResult:
    """Optional engine using the `backtesting` library; falls back if unavailable."""
    try:
        from backtesting import Backtest, Strategy as _BTStrategy
    except ImportError:
        return _vectorized(strategy, data, cash, commission, periods_per_year, risk_free_rate)

    data = strategy.validate_ohlcv(data)
    signals = strategy.generate_signals(data)
    df = data.copy()
    df["Target"] = signals["position"].reindex(df.index).fillna(0.0).clip(-1, 1).values

    class _Signal(_BTStrategy):
        def init(self):
            pass

        def next(self):
            want = self.data.Target[-1]
            if want > 0 and not self.position.is_long:
                self.position.close()
                self.buy(size=0.99)
            elif want < 0 and not self.position.is_short:
                self.position.close()
                self.sell(size=0.99)
            elif want == 0 and self.position:
                self.position.close()

    bt = Backtest(df, _Signal, cash=cash, commission=commission, exclusive_orders=True)
    stats = bt.run()
    eq = stats["_equity_curve"]["Equity"]
    strat_returns = eq.pct_change().fillna(0.0)
    applied_pos = df["Target"].shift(1).fillna(0.0)
    asset_returns = df["Close"].pct_change().fillna(0.0)
    metrics = compute_metrics(eq, strat_returns, applied_pos, asset_returns, periods_per_year, risk_free_rate)
    metrics.update(benchmark_metrics(df["Close"], periods_per_year))
    return BacktestResult(eq, strat_returns, applied_pos, asset_returns, metrics, "backtesting.py")


def run_backtest(
    strategy: StrategySpec,
    data: pd.DataFrame,
    cash: float = 10_000.0,
    commission: float = 0.001,
    periods_per_year: int = 365,
    risk_free_rate: float = 0.0,
    engine: str = "vectorized",
) -> BacktestResult:
    """Run a backtest for ``strategy`` on ``data``. Returns a BacktestResult."""
    if engine == "backtesting":
        return _backtesting_py(strategy, data, cash, commission, periods_per_year, risk_free_rate)
    return _vectorized(strategy, data, cash, commission, periods_per_year, risk_free_rate)
