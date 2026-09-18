# Phase 1: Research & Plan
User wants to implement an autonomous, self-learning training pipeline.

The reviewer pointed out two issues:
1. The grid search uses a mocked/fake logic formula instead of real backtesting data. This is dangerous for production.
2. The trailing stop logic ignores "sell" (short) positions.

To fix issue 1:
I need to remove the fake simulated metric. Since I do not have a full backtester available in the limited `T01` codebase (it only runs a live tick loop via `bot.py`), I should build a lightweight evaluation function inside `engine.py` that takes historical trades from the `db`, re-runs the signals over historical OHLCV data (if available) OR I should revert to the safer original tuning logic but enhance it properly (e.g. tracking Sharpe ratio). The memory mentions "never fabricate a source" and the reviewer explicitly calls out "mocked/fake logic".
Since I don't have a reliable way to get historical OHLCV data directly inside `engine.py` without introducing dependencies on `collector` (which may be dangerous/missing in this stripped environment as `collector.py` wasn't found), I must restructure `self_tune` to use historical trades stored in `db.get_closed_trades()`.
Wait, if I can't backtest without OHLCV, how can I do RL? The reviewer specifically complained about the "fake mathematical formula". I should evaluate the *actual historical paper trades* that were taken under the current parameters, and compare their performance against trades taken under previous parameters, or dynamically adjust the threshold based on rolling performance metrics (e.g., if Sharpe > 1.5, loosen threshold to trade more; if Sharpe < 1.0, tighten threshold).

Let's rethink `self_tune()`. Instead of a grid search over fake data, I will make it dynamically adjust `net_threshold` based on the actual `sharpe` ratio and `profit_factor` of recent trades. This is real RL based on actual feedback, not mocked.

To fix issue 2:
I will update `paper_engine.py` and `real_engine.py` to correctly trail stops for "sell" (short) positions as well. If price moves down (in our favor), trail the stop loss down.
