"""Parameter optimization with honest out-of-sample (walk-forward) validation.

In-sample-only tuning is how strategies lie. Walk-forward picks parameters on a
training window, then scores them on the *next, unseen* window, and repeats. The
out-of-sample aggregate is what the review trusts (Constitution R-D.7).
"""
from __future__ import annotations

import itertools
from typing import Any, Callable

import pandas as pd

from ..backtest.runner import run_backtest
from ..strategy_base import StrategySpec

StrategyFactory = Callable[..., StrategySpec]


def _param_combinations(grid: dict[str, list]) -> list[dict[str, Any]]:
    if not grid:
        return [{}]
    keys = list(grid.keys())
    return [dict(zip(keys, combo)) for combo in itertools.product(*(grid[k] for k in keys))]


def _score(result_metric: float | None) -> float:
    return float(result_metric) if result_metric is not None and result_metric == result_metric else float("-inf")


def grid_search(
    strategy_cls: StrategyFactory,
    data: pd.DataFrame,
    param_grid: dict[str, list],
    *,
    metric: str = "sharpe",
    cash: float = 10_000.0,
    commission: float = 0.001,
    periods_per_year: int = 365,
) -> dict[str, Any]:
    """Exhaustive search; returns the params maximizing ``metric`` in-sample."""
    best: dict[str, Any] = {"params": {}, "score": float("-inf"), "metrics": {}}
    trials: list[dict[str, Any]] = []
    for params in _param_combinations(param_grid):
        strat = strategy_cls(**params)
        res = run_backtest(strat, data, cash, commission, periods_per_year)
        score = _score(res.metrics.get(metric))
        trials.append({"params": params, "score": score, metric: res.metrics.get(metric)})
        if score > best["score"]:
            best = {"params": params, "score": score, "metrics": res.metrics}
    best["trials"] = trials
    return best


def walk_forward(
    strategy_cls: StrategyFactory,
    data: pd.DataFrame,
    param_grid: dict[str, list],
    *,
    n_splits: int = 4,
    metric: str = "sharpe",
    cash: float = 10_000.0,
    commission: float = 0.001,
    periods_per_year: int = 365,
) -> dict[str, Any]:
    """Anchored walk-forward: expand the train window, test on the next fold.

    Returns per-fold chosen params + out-of-sample metrics, plus an aggregate and
    the params most frequently selected (a robustness signal).
    """
    data = data.sort_index()
    n = len(data)
    if n < (n_splits + 1) * 30:
        n_splits = max(2, n // 60)  # need enough bars per fold
    fold_size = n // (n_splits + 1)
    folds: list[dict[str, Any]] = []

    for i in range(1, n_splits + 1):
        train = data.iloc[: i * fold_size]
        test = data.iloc[i * fold_size : (i + 1) * fold_size]
        if len(test) < 20:
            break
        chosen = grid_search(
            strategy_cls, train, param_grid,
            metric=metric, cash=cash, commission=commission, periods_per_year=periods_per_year,
        )
        oos = run_backtest(strategy_cls(**chosen["params"]), test, cash, commission, periods_per_year)
        folds.append({
            "fold": i,
            "train_bars": len(train),
            "test_bars": len(test),
            "chosen_params": chosen["params"],
            "in_sample_score": chosen["score"],
            "oos_metrics": oos.metrics,
        })

    oos_scores = [f["oos_metrics"].get(metric) for f in folds if f["oos_metrics"].get(metric) == f["oos_metrics"].get(metric)]
    agg = (sum(oos_scores) / len(oos_scores)) if oos_scores else float("nan")

    # most robust params = the combination chosen in the most folds
    from collections import Counter
    counts = Counter(tuple(sorted(f["chosen_params"].items())) for f in folds)
    best_combo = dict(counts.most_common(1)[0][0]) if counts else {}

    return {
        "metric": metric,
        "n_folds": len(folds),
        "folds": folds,
        "oos_mean_metric": agg,
        "recommended_params": best_combo,
    }
