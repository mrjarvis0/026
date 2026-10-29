"""Kernel-side bus adapters — thin bridges from the message bus to an agent's own entry
points. Agents stay unaware of the bus; the wiring lives here, in the composition root
(the only layer allowed to import ``agents.*``). Payload key: ``intent`` (A001/A002 also
honour the legacy ``op``).
"""
from __future__ import annotations

from . import a002, a015
from .a001 import a001_handler

__all__ = ["a001_handler", "a002", "a015"]
