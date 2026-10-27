"""Performance metrics computed from an equity curve + position series.

These are the numbers the Constitution's success criteria are judged on
($trategy-master.agent.md §5): return, risk-adjusted return, drawdown, trade
quality, and a buy-&-hold benchmark.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _max_drawdown(equity: pd.Series) -> float:
    """Largest peak-to-trough decline as a negative fraction (e.g. -0.35)."""
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    return float(drawdown.min())


def _extract_trades(applied_pos: pd.Series, asset_returns: pd.Series) -> list[float]:
    """Per-trade returns from contiguous constant-nonzero-position segments."""
    seg_id = (applied_pos != applied_pos.shift()).cumsum()
    trades: list[float] = []
    for _, idx in applied_pos.groupby(seg_id).groups.items():
        seg_pos = applied_pos.loc[idx]
        direction = seg_pos.iloc[0]
        if direction == 0:
            continue
        seg_ret = asset_returns.loc[idx]
        gross = float((1.0 + direction * seg_ret).prod() - 1.0)
        trades.append(gross)
    return trades


def compute_metrics(
    equity: pd.Series,
    strat_returns: pd.Series,
    applied_pos: pd.Series,
    asset_returns: pd.Series,
    periods_per_year: int = 365,
    risk_free_rate: float = 0.0,
) -> dict[str, float]:
    """Return a dict of headline metrics for a single backtest run."""
    equity = equity.dropna()
    strat_returns = strat_returns.reindex(equity.index).fillna(0.0)
    n = len(equity)
    if n < 2:
        return {"error": float("nan"), "bars": float(n)}

    n_years = n / periods_per_year
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    cagr = float((equity.iloc[-1] / equity.iloc[0]) ** (1.0 / n_years) - 1.0) if n_years > 0 else float("nan")

    mean_r = float(strat_returns.mean())
    std_r = float(strat_returns.std(ddof=1))
    ann_return = mean_r * periods_per_year
    ann_vol = std_r * np.sqrt(periods_per_year)
    sharpe = (ann_return - risk_free_rate) / ann_vol if ann_vol > 0 else float("nan")

    downside = strat_returns[strat_returns < 0]
    dd_std = float(downside.std(ddof=1)) * np.sqrt(periods_per_year) if len(downside) > 1 else np.nan
    sortino = (ann_return - risk_free_rate) / dd_std if dd_std and dd_std > 0 else float("nan")

    max_dd = _max_drawdown(equity)
    calmar = (cagr / abs(max_dd)) if max_dd < 0 else float("nan")

    exposure = float((applied_pos != 0).mean())

    trades = _extract_trades(applied_pos, asset_returns)
    n_trades = len(trades)
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]
    win_rate = (len(wins) / n_trades) if n_trades else float("nan")
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (float("inf") if gross_win > 0 else float("nan"))
    avg_trade = float(np.mean(trades)) if trades else float("nan")

    return {
        "total_return": round(total_return, 6),
        "cagr": round(cagr, 6),
        "ann_return": round(ann_return, 6),
        "ann_volatility": round(ann_vol, 6),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "calmar": round(calmar, 4),
        "max_drawdown": round(max_dd, 6),
        "exposure": round(exposure, 4),
        "num_trades": n_trades,
        "win_rate": round(win_rate, 4) if win_rate == win_rate else win_rate,
        "profit_factor": round(profit_factor, 4) if np.isfinite(profit_factor) else profit_factor,
        "avg_trade": round(avg_trade, 6) if avg_trade == avg_trade else avg_trade,
        "bars": n,
        "years": round(n_years, 3),
    }


def benchmark_metrics(close: pd.Series, periods_per_year: int = 365) -> dict[str, float]:
    """Buy-&-hold metrics for the same asset/window (the comparison baseline)."""
    close = close.dropna()
    bh_returns = close.pct_change().fillna(0.0)
    equity = (1.0 + bh_returns).cumprod()
    pos = pd.Series(1.0, index=close.index)
    m = compute_metrics(equity, bh_returns, pos, bh_returns, periods_per_year)
    return {f"bh_{k}": v for k, v in m.items() if k in {"total_return", "cagr", "sharpe", "max_drawdown"}}
