"""Per-agent live state (idempotency + restart safety).

Stored at agents/$NNN-owner/live_state.json. Tracks the last bar we acted on so a
re-run within the same bar does nothing, and a daily trade counter for the cap.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

STATE_FILE = "live_state.json"

_DEFAULT: dict[str, Any] = {
    "last_bar_acted": None,   # ISO timestamp of the bar we last acted on
    "last_target": 0.0,       # last target position we set
    "last_order": None,       # summary of the last order placed
    "trades_day": None,       # ISO date of the trades_today counter
    "trades_today": 0,
}


def load_state(agent_dir: Path) -> dict[str, Any]:
    path = agent_dir / STATE_FILE
    if not path.exists():
        return dict(_DEFAULT)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULT)
    merged = dict(_DEFAULT)
    merged.update(data)
    return merged


def save_state(agent_dir: Path, state: dict[str, Any]) -> None:
    path = agent_dir / STATE_FILE
    path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def trades_today(state: dict[str, Any]) -> int:
    """Today's order count (resets automatically on a new UTC date)."""
    today = date.today().isoformat()
    if state.get("trades_day") != today:
        return 0
    return int(state.get("trades_today", 0))


def record_trade(state: dict[str, Any], order_summary: str) -> None:
    today = date.today().isoformat()
    if state.get("trades_day") != today:
        state["trades_day"] = today
        state["trades_today"] = 0
    state["trades_today"] = int(state.get("trades_today", 0)) + 1
    state["last_order"] = order_summary
