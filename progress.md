# Phase 1: Research & Plan
User wants professional trader firm-style improvements to find flaws and add new institutional-grade features (e.g. VWAP, dynamic risk sizing, trailing stops). The memory explicitly requests taking an ownership persona to proactively add advanced algorithmic features.
I will analyze T01_Smart_Binance_Intelligence.

Current Flaws:
1. `risk.py` uses a static risk percentage. Institutional firms use volatility-adjusted position sizing (e.g., using ATR).
2. `indicators.py` lacks institutional indicators like VWAP (Volume Weighted Average Price) and ATR (Average True Range) which are essential for true dynamic risk.
3. The stop loss in `paper_engine.py` might be static rather than a trailing stop.

Plan:
1. Add ATR and VWAP to `indicators.py`.
2. Update `risk.py` to use ATR for dynamic stop-loss distance calculation instead of a static percentage.
3. Update tests.
