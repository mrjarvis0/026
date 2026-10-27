"""Live paper-trading engine (testnet only).

Turns an agent's strategy into a running (paper) trader: each closed bar it reads
the target position, reconciles against the account, and places only the delta
order. Dry-run by default; testnet only; real money is out of scope.
"""
from .engine import LiveTrader, Decision  # noqa: F401
from .broker import LiveBroker  # noqa: F401
