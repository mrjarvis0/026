"""
CIE-OS
A001 Blockchain Intelligence Agent

Module:
    skills.wallet_lookup.balances

Purpose:
    Adapt the per-chain sensor registry to the simple
    ``native_balance(chain, address)`` contract a skill wants, so a skill needs
    to know nothing about chain dispatch or transports.

Notes:
    A chain with no sensor (non-EVM, for now) yields ``None`` rather than raising,
    so the caller degrades -- reports no balance -- exactly as it would with no
    provider wired at all. Construction performs no network I/O; the balance read
    does, which is why it is the caller's choice to wire this in.
"""
from __future__ import annotations

from typing import Any

from core.exceptions import SensorError
from sensors.registry import SensorRegistry


class SensorBalances:
    """A native-balance provider backed by the shared sensor registry."""

    def __init__(self, registry: SensorRegistry | None = None) -> None:
        self._registry = registry if registry is not None else SensorRegistry()

    def native_balance(self, chain: str, address: str) -> Any:
        try:
            sensor = self._registry.get(chain)
        except (SensorError, KeyError, ValueError):
            return None
        return sensor.balance(address)
