"""Shared round-trip fee math for the paper and real engines (F-track F2).

Both legs bear the fee, so recorded PnL is net-of-fee in either mode::

    proceeds = qty * exit_price  * (1 - fee)
    cost     = qty * entry_price * (1 + fee)
    pnl      = proceeds - cost

Paper pays PAPER_FEE_PCT; real pays REAL_FEE_PCT (same default — set it to your
VIP/maker tier, see .env.example). One function, so the two engines can never
drift apart again.
"""


def entry_cost(quantity: float, price: float, fee_pct: float) -> float:
    """Cash debited to open: notional plus the entry-leg fee."""
    return quantity * price * (1 + fee_pct)


def exit_proceeds(quantity: float, price: float, fee_pct: float) -> float:
    """Cash credited on close: notional minus the exit-leg fee."""
    return quantity * price * (1 - fee_pct)


def round_trip_pnl(entry_price: float, exit_price: float,
                   quantity: float, fee_pct: float) -> tuple[float, float]:
    """Net (pnl, pnl_pct) for a round trip. pnl_pct is measured on the
    fee-loaded cost basis, matching what the wallet actually spent."""
    cost = entry_cost(quantity, entry_price, fee_pct)
    proceeds = exit_proceeds(quantity, exit_price, fee_pct)
    pnl = proceeds - cost
    pnl_pct = (pnl / cost * 100.0) if cost else 0.0
    return pnl, pnl_pct
