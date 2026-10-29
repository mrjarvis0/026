"""Paper / demo trading adapters — testnet & practice accounts only.

Safety model (Constitution R-B.4, R-B.9):
- **No order is ever sent automatically.** Callers build a PaperOrder (a
  description) and must pass the explicit human-confirm token to submit it.
- These adapters target **testnet / practice** endpoints only. They never touch a
  real-money account; real trading is out of scope for this hub.
"""
from __future__ import annotations

from dataclasses import dataclass

#: The caller must pass this exact token to actually transmit an order. Requiring a
#: literal, non-default value makes "send" an explicit human act, not a default path.
HUMAN_CONFIRM_PHRASE = "I-CONFIRM-PAPER-ORDER"


@dataclass
class PaperOrder:
    market: str            # crypto | forex | stocks
    symbol: str
    side: str              # buy | sell
    qty: float
    order_type: str = "market"
    price: float | None = None
    note: str = ""

    def describe(self) -> str:
        px = f" @ {self.price}" if self.price is not None else " @ market"
        return f"[{self.market}] {self.side.upper()} {self.qty} {self.symbol}{px} ({self.order_type})"


class OrderRefused(RuntimeError):
    """Raised when a submit is attempted without the human-confirm token."""


def require_confirmation(confirm_token: str | None) -> None:
    """Gate every real transmission behind the explicit human token."""
    if confirm_token != HUMAN_CONFIRM_PHRASE:
        raise OrderRefused(
            "Refusing to send order: human confirmation required. "
            f"Pass confirm_token='{HUMAN_CONFIRM_PHRASE}' to transmit to the testnet/practice account."
        )
