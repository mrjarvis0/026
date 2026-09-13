"""
CIE-OS
A01 Blockchain Intelligence Agent

Module:
    normalization._hex

Purpose:
    Small shared helper for reading a JSON-RPC integer field that may arrive as
    an ``int``, a decimal string, a ``0x``-prefixed hex string, or missing --
    the shape ``blockNumber``, ``logIndex`` and the like are quoted in.

    Extracted so ``normalization.logs`` and ``normalization.approvals`` share
    one parser; a fix or hardening here now lands in both call sites.
"""

from __future__ import annotations

from typing import Any


def height_of(value: Any) -> int | None:
    """
    Read a non-negative integer field from a JSON-RPC payload.

    Accepts ``int`` (rejecting ``bool``, which subclasses it), decimal strings,
    and ``0x``-prefixed hex. Returns ``None`` for anything unreadable or a
    negative int -- a caller counts that as "field absent" rather than raising.
    """
    if isinstance(value, int) and not isinstance(value, bool):
        return value if value >= 0 else None
    if isinstance(value, str) and value.strip():
        text = value.strip()
        try:
            return int(text, 16) if text.lower().startswith("0x") else int(text, 10)
        except ValueError:
            return None
    return None


__all__ = ["height_of"]
