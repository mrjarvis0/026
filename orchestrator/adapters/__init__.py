"""Kernel-side bus adapters — thin bridges from the message bus to an agent's own
entry points (SP-4). Agents stay unaware of the bus; the wiring lives here.

Currently wired: A002 (News Intelligence). A001's adapter is intentionally not
built yet — see AGENTS.md §12 / registry `kernel_wired` flags.
"""
from __future__ import annotations

from .a002 import build_handler as build_a002_handler
from .a002 import register as register_a002
from .a015 import build_handler as build_a015_handler
from .a015 import register as register_a015

__all__ = [
    "register_a002", "build_a002_handler",
    "register_a015", "build_a015_handler",
]
