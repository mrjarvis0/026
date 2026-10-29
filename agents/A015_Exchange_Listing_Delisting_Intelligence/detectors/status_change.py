"""SUPPORT_CHANGE / MAINTENANCE_HALT — a symbol flips to HALT/BREAK.

Only fires for exchanges whose CCXT impl exposes fetchStatus (README §4.2) — read
from config (`has_fetch_status`), not a hard-coded list. No price-impact annotation:
this is a fleet-internal risk/ops signal (e.g. tells A013 to skip that pair now).
"""
from __future__ import annotations

from ..core import config_loader as cfg
from ..core.report import base_report

_HALT_BREAK = {"halt", "break"}


def _status_of(market: dict) -> str | None:
    if not isinstance(market, dict):
        return None
    if market.get("status") is not None:
        return market["status"]
    info = market.get("info") or {}
    return info.get("status") or info.get("tradingStatus")


def detect_status_change(changes: list[dict]) -> list[dict]:
    reports = []
    for change in changes:
        if change.get("change_type") != "changed":
            continue
        exchange_id = change.get("exchange")
        if not exchange_id or not cfg.has_fetch_status(exchange_id):
            continue
        old_status = _status_of(change.get("old_value") or {})
        new_status = _status_of(change.get("new_value") or {})
        if not new_status or str(new_status).lower() not in _HALT_BREAK:
            continue
        if old_status is not None and str(old_status).lower() == str(new_status).lower():
            continue   # already in that state: another field changed, this is not a status transition
        report = base_report("STATUS_CHANGE", exchange_id, change.get("symbol"))
        report.update({
            "status_from": old_status,
            "status_to": new_status,
            "historical_context": "No price-impact annotation - fleet-internal risk/ops signal",
        })
        reports.append(report)
    return reports
