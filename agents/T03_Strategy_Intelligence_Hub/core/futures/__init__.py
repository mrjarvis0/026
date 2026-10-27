"""Futures scalper components (SCALPER.md components #3–#7).

MTF analysis → next-candle probability → signal fusion → scalper execution loop.

Pieces:
- mtf.py      : multi-timeframe OHLCV fetch + per-TF trend/momentum/ADX, alignment score
- predict.py  : calibrated next-candle probability model (features → P(up))
- fuse.py     : fuse scanner consensus + MTF alignment + P(up) + optional sentiment
- scalper.py  : 24/7 futures scalper execution loop (dry-run by default)
"""
from .mtf import MTFAnalyzer, MTFSignal          # noqa: F401
from .predict import CandlePredictor              # noqa: F401
from .fuse import SignalFuser, FusedSignal        # noqa: F401
