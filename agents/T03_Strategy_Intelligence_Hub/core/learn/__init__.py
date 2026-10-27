"""Learning / mistake-memory (Reflexion pattern).

Watch trades → on a loss, diagnose *why* → store a categorized lesson in a mistakes
memory → warn (or block) before repeating the same losing pattern. Grounded in the
Constitution's R-D.4 (self-correction loop) and mirrors the sibling `StallBreaker`.

Pieces:
- trades.py  : reconstruct trades (entry/exit + market context) from a position series
- reflect.py : diagnose a losing trade into a Lesson (rule-based, no fabrication)
- memory.py  : persist lessons, count repeats, render MISTAKES.md
- guard.py   : check a proposed trade against known mistakes -> warnings
"""
from .trades import TradeRecord, extract_trades, latest_context  # noqa: F401
from .reflect import Lesson, diagnose  # noqa: F401
from .memory import MistakeMemory  # noqa: F401
from .guard import check_trade  # noqa: F401
