"""Compute performance metrics and evaluate the real-trading accuracy gate."""
import math

from backend import config
from backend.data import database as db


def compute_metrics(mode: str = "paper") -> dict:
    closed = db.get_closed_trades(mode=mode, limit=10000)
    # 'reset' rows are synthetic breakeven closes created when the paper wallet
    # is reset (PaperEngine.reset). They are not real trades: counting them
    # would inflate total_trades toward the real-trading gate and drag accuracy
    # down with fake pnl=0 "losses". Exclude them from every metric.
    closed = [t for t in closed if t.get("exit_reason") != "reset"]
    total = len(closed)

    if total == 0:
        return {
            "mode": mode,
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "accuracy": 0.0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "avg_pnl": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "expectancy": 0.0,
            "profit_factor": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "roi_pct": 0.0,
            "unlocked": False,
            "unlock_threshold": config.ACCURACY_UNLOCK_THRESHOLD,
            "min_trades": config.ACCURACY_MIN_TRADES,
        }

    pnls = [t["pnl"] or 0.0 for t in closed]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total_pnl = sum(pnls)
    accuracy = len(wins) / total * 100.0
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    # Expectancy: average $ PnL you can expect per trade given the current
    # win-rate and average win/loss sizes. Positive = a statistical edge.
    win_rate = len(wins) / total
    expectancy = (avg_win * win_rate) - (abs(avg_loss) * (1.0 - win_rate))

    # Sharpe ratio on per-trade returns
    mean = total_pnl / total
    if total > 1:
        variance = sum((p - mean) ** 2 for p in pnls) / (total - 1)
        std = math.sqrt(variance)
        sharpe = (mean / std) * math.sqrt(total) if std > 0 else 0.0
    else:
        sharpe = 0.0

    # Max drawdown over cumulative pnl curve
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in reversed(pnls):   # closed is DESC; iterate chronologically
        cumulative += p
        peak = max(peak, cumulative)
        max_dd = max(max_dd, peak - cumulative)

    # ROI is measured against the capital that mode actually started with:
    # paper's fixed starting balance, or the real equity snapshotted at enable.
    if mode == "real":
        roi_base = float(db.get_state("real_start_equity") or config.PAPER_START_BALANCE)
    else:
        roi_base = config.PAPER_START_BALANCE
    roi_pct = total_pnl / roi_base * 100.0 if roi_base else 0.0

    unlocked = (accuracy >= config.ACCURACY_UNLOCK_THRESHOLD
                and total >= config.ACCURACY_MIN_TRADES)

    return {
        "mode": mode,
        "total_trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "accuracy": round(accuracy, 2),
        "win_rate": round(accuracy, 2),
        "total_pnl": round(total_pnl, 2),
        "avg_pnl": round(mean, 4),
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "expectancy": round(expectancy, 4),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else 999.0,
        "sharpe": round(sharpe, 2),
        "max_drawdown": round(max_dd, 2),
        "roi_pct": round(roi_pct, 2),
        "unlocked": unlocked,
        "unlock_threshold": config.ACCURACY_UNLOCK_THRESHOLD,
        "min_trades": config.ACCURACY_MIN_TRADES,
    }


def is_real_trading_unlocked() -> bool:
    """Real trading is gated: accuracy >= threshold over min sample of paper trades."""
    return compute_metrics("paper")["unlocked"]
