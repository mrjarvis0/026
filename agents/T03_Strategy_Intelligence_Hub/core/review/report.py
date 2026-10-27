"""Generate an agent's performance review.

Produces `results/backtest/metrics.json`, an equity-curve PNG, and `results/REVIEW.md`
comparing the strategy to buy-&-hold. The verdict is deliberately conservative:
beating buy-&-hold on risk-adjusted terms, not just raw return, is the bar.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from ..backtest.runner import BacktestResult


def save_metrics(out_dir: Path, metrics: dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "metrics.json"
    path.write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")
    return path


def plot_equity(result: BacktestResult, out_path: Path) -> Path | None:
    """Save a strategy-vs-buy&hold equity curve. Returns None if matplotlib absent."""
    try:
        import matplotlib
        matplotlib.use("Agg")  # headless
        import matplotlib.pyplot as plt
    except ImportError:  # pragma: no cover
        return None

    frame = result.equity_frame()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(frame.index, frame["strategy"], label="Strategy", linewidth=1.6)
    ax.plot(frame.index, frame["buy_and_hold"], label="Buy & Hold", linewidth=1.2, alpha=0.7)
    ax.set_title("Equity curve — strategy vs buy & hold")
    ax.set_ylabel("Portfolio value")
    ax.legend()
    ax.grid(True, alpha=0.3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def _pct(x: Any) -> str:
    try:
        return f"{float(x) * 100:.2f}%"
    except (TypeError, ValueError):
        return str(x)


def _num(x: Any) -> str:
    try:
        return f"{float(x):.3f}"
    except (TypeError, ValueError):
        return str(x)


def _verdict(m: dict[str, Any]) -> str:
    sharpe = m.get("sharpe")
    bh_sharpe = m.get("bh_sharpe")
    ret = m.get("total_return")
    bh_ret = m.get("bh_total_return")
    try:
        beats_risk = sharpe is not None and bh_sharpe is not None and float(sharpe) > float(bh_sharpe)
        beats_ret = ret is not None and bh_ret is not None and float(ret) > float(bh_ret)
    except (TypeError, ValueError):
        return "⚠️ Inconclusive — metrics unavailable."
    if beats_risk and beats_ret:
        return "✅ Beats buy-&-hold on both total return and risk-adjusted (Sharpe)."
    if beats_risk:
        return "🟡 Beats buy-&-hold on risk-adjusted return (Sharpe) but not raw return."
    if beats_ret:
        return "🟡 Higher raw return than buy-&-hold, but weaker risk-adjusted — check drawdown."
    return "❌ Does not beat buy-&-hold here. Needs rework or a different regime/market."


def generate_review(
    agent_dir: Path,
    result: BacktestResult,
    config: dict[str, Any],
    training: dict[str, Any] | None = None,
) -> Path:
    """Write metrics.json, equity_curve.png, and REVIEW.md. Returns REVIEW.md path."""
    results_dir = agent_dir / "results"
    bt_dir = results_dir / "backtest"
    save_metrics(bt_dir, result.metrics)
    result.save(bt_dir)
    plot_equity(result, bt_dir / "equity_curve.png")

    m = result.metrics
    name = agent_dir.name
    symbols = config.get("symbols", config.get("symbol", "?"))
    market = config.get("market", "?")
    timeframe = config.get("timeframe", "?")

    lines: list[str] = [
        f"# Review — `{name}`",
        "",
        f"- **Generated:** {date.today().isoformat()}",
        f"- **Market / symbols:** {market} / {symbols}",
        f"- **Timeframe:** {timeframe}",
        f"- **Backtest engine:** {result.engine}",
        f"- **Window:** {m.get('years', '?')} years ({m.get('bars', '?')} bars)",
        "",
        f"## Verdict\n\n{_verdict(m)}",
        "",
        "## Headline metrics",
        "",
        "| Metric | Strategy | Buy & Hold |",
        "|---|---|---|",
        f"| Total return | {_pct(m.get('total_return'))} | {_pct(m.get('bh_total_return'))} |",
        f"| CAGR | {_pct(m.get('cagr'))} | {_pct(m.get('bh_cagr'))} |",
        f"| Sharpe | {_num(m.get('sharpe'))} | {_num(m.get('bh_sharpe'))} |",
        f"| Sortino | {_num(m.get('sortino'))} | — |",
        f"| Calmar | {_num(m.get('calmar'))} | — |",
        f"| Max drawdown | {_pct(m.get('max_drawdown'))} | {_pct(m.get('bh_max_drawdown'))} |",
        f"| Ann. volatility | {_pct(m.get('ann_volatility'))} | — |",
        f"| Exposure | {_pct(m.get('exposure'))} | 100% |",
        "",
        "## Trade quality",
        "",
        f"- **Trades:** {m.get('num_trades')}",
        f"- **Win rate:** {_pct(m.get('win_rate'))}",
        f"- **Profit factor:** {_num(m.get('profit_factor'))}",
        f"- **Avg trade:** {_pct(m.get('avg_trade'))}",
        "",
        "![Equity curve](backtest/equity_curve.png)",
        "",
    ]

    if training:
        lines += [
            "## Walk-forward (out-of-sample) validation",
            "",
            f"- **Folds:** {training.get('n_folds')}",
            f"- **OOS mean {training.get('metric', 'metric')}:** {_num(training.get('oos_mean_metric'))}",
            f"- **Recommended params:** `{training.get('recommended_params')}`",
            "",
            "> Out-of-sample is the number that matters; strong in-sample with weak OOS = overfit.",
            "",
        ]

    lines += [
        "## Notes & caveats",
        "",
        "- Historical simulation only. **Not financial advice**; past performance ≠ future results.",
        "- Costs modeled: commission only (see metrics meta). Slippage, funding, and liquidity are not fully modeled.",
        "- Re-run on out-of-sample / a second symbol before trusting. Paper-trade before any real capital (human-gated).",
        "",
    ]

    review_path = results_dir / "REVIEW.md"
    review_path.write_text("\n".join(lines), encoding="utf-8")
    return review_path
