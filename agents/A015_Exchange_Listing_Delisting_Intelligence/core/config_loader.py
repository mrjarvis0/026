"""Config access for A015 — loaded once and cached (was: re-read per detector call).

All per-exchange facts (phase, evidence-backing, fetchStatus support) come from
`config/exchanges.yaml`, never hard-coded in a detector — so adding/adjusting an
exchange is a config edit, not a code edit.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


@lru_cache(maxsize=1)
def exchanges() -> dict:
    with open(_CONFIG_DIR / "exchanges.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@lru_cache(maxsize=1)
def detectors_cfg() -> dict:
    with open(_CONFIG_DIR / "detectors.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _entry(exchange_id: str) -> dict:
    return (exchanges().get(exchange_id) or {})


def phase_of(exchange_id: str) -> int:
    """Rollout phase (1/2/3); unknown exchanges default to 3 (lowest priority)."""
    return int(_entry(exchange_id).get("phase", 3))


def is_evidence_backed(exchange_id: str) -> bool:
    """True only where a quantified historical listing/delisting effect exists
    (Binance/Bybit/Coinbase per README §3.4) — config-driven, not phase-coupled."""
    return bool(_entry(exchange_id).get("evidence_backed", False))


def has_fetch_status(exchange_id: str) -> bool:
    """True where the exchange's CCXT impl exposes fetchStatus (README §4.2) —
    read from config, not a hard-coded set."""
    return bool(_entry(exchange_id).get("has_fetch_status", False))
