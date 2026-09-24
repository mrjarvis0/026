"""ANNOUNCED_LISTING (pending) — a coin whose listing was *announced* but which is
NOT yet trading on the exchange (README §4.3, earliest-detection layer).

This is the "notification aa gaya, kaafi din ho gaye, par abhi tak list nahi hua"
signal: for every announced token not present in the exchange's current spot markets,
emit a pending report with `days_since_announcement` and an `is_stale` flag. Once the
token actually appears in `fetch_markets()`, the normal NEW_LISTING detector takes over,
so a listed token is never reported as pending.

Source parsing is heuristic (README §Sources), so confidence stays modest — this is a
fact ("announced, not yet on spot") plus context, never a buy/sell signal.
"""
from __future__ import annotations

from datetime import datetime, timezone

_CONTEXT = ("Announced but not yet listed. The historical listing pump typically lands "
            "around the announcement (README §3.1), not the technical listing moment. "
            "Not a buy/sell signal; token parsed heuristically from the announcement title.")


def _days_since(announced_at: str | None, now: datetime) -> float | None:
    if not announced_at:
        return None
    try:
        dt = datetime.fromisoformat(announced_at)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return round((now - dt).total_seconds() / 86400, 1)


def detect_pending_listings(announcements: list[dict],
                            listed_bases_by_exchange: dict[str, set],
                            now: datetime | None = None,
                            stale_days: float = 3.0) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    seen: set[tuple[str, str]] = set()
    reports: list[dict] = []
    for ann in announcements:
        exchange = ann.get("exchange")
        if not exchange:
            continue
        listed = listed_bases_by_exchange.get(exchange) or set()
        days = _days_since(ann.get("announced_at"), now)
        for token in ann.get("tokens", []):
            if token in listed:        # already trading -> NEW_LISTING territory, not pending
                continue
            key = (exchange, token)
            if key in seen:
                continue
            seen.add(key)
            reports.append({
                "event_type": "ANNOUNCED_LISTING",
                "exchange": exchange,
                "token": token,
                "still_pending": True,
                "announced_at": ann.get("announced_at"),
                "days_since_announcement": days,
                "is_stale": days is not None and days >= stale_days,
                "title": ann.get("title"),
                "url": ann.get("url"),
                "detected_via": "announcement-text",
                "historical_context": _CONTEXT,
            })
    return reports
