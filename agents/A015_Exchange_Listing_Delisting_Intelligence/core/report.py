"""Canonical deviation-report scaffold (A001/A002 style) shared by every detector.

A report is a fact + evidence, never a buy/sell signal. `base_report` fills the
fields every detector shares; each detector adds its own specifics.
"""
from __future__ import annotations

from datetime import datetime, timezone

from . import config_loader as cfg

INSUFFICIENT = "No historical evidence for this exchange yet (confidence: insufficient sample)"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def base_report(event_type: str, exchange: str, symbol: str | None = None) -> dict:
    return {
        "event_type": event_type,
        "exchange": exchange,
        "symbol": symbol,
        "detected_at": now_iso(),
        "detected_via": "structured-diff",
        "phase": cfg.phase_of(exchange),
        "evidence_backed": cfg.is_evidence_backed(exchange),
    }
