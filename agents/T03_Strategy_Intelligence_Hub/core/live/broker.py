"""Unified live-broker wrapper over the paper adapters (testnet only).

Dispatches by market. Crypto uses core/paper/binance_testnet. Forex/stocks are
stubs until their practice adapters are wired for live reconciliation.
"""
from __future__ import annotations

from typing import Any

from ..paper import PaperOrder


class LiveBroker:
    """Thin façade so the engine doesn't care which venue it is talking to."""

    def __init__(self, market: str) -> None:
        self.market = market
        self._client: Any = None
        if market == "crypto":
            from ..paper import binance_testnet as mod
        elif market == "forex":
            mod = None  # oanda_practice lacks live reconcile helpers yet
        elif market == "stocks":
            mod = None  # alpaca_paper lacks live reconcile helpers yet
        else:
            raise ValueError(f"Unknown market '{market}'")
        self._mod = mod

    @property
    def connected(self) -> bool:
        return self._client is not None

    def connect(self) -> None:
        """Connect to the testnet account. Raises if the venue isn't wired or keys missing."""
        if self._mod is None:
            raise NotImplementedError(
                f"Live reconciliation for market '{self.market}' is not wired yet "
                f"(only crypto/Binance Testnet). Use a crypto agent."
            )
        self._client = self._mod.connect()

    # -- reads --
    def price(self, symbol: str) -> float:
        return self._mod.get_price(self._client, symbol)

    def equity(self, symbol: str, price: float | None = None) -> float:
        return self._mod.get_equity(self._client, symbol, price)

    def position_units(self, symbol: str) -> float:
        return self._mod.get_position_units(self._client, symbol)

    def round_qty(self, symbol: str, qty: float) -> float:
        return self._mod.round_qty(self._client, symbol, qty)

    # -- write (gated) --
    def place_market(self, symbol: str, side: str, qty: float, confirm_token: str | None) -> dict:
        order = PaperOrder(market=self.market, symbol=symbol, side=side, qty=qty,
                           order_type="market", note="live-engine delta")
        return self._mod.submit_order(self._client, order, confirm_token=confirm_token)
