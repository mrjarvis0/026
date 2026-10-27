"""
CIE-OS
A002 News Intelligence Agent

Module:
    intelligence.events

Purpose:
    Best-effort extraction of scheduled future events from news text — a meeting,
    launch, unlock or release that names an explicit time ("mainnet goes live
    Oct 1 at 14:00 UTC", "the FOMC meeting on Wednesday at 2pm ET").

    This is a HEURISTIC with a known ceiling. It only fires when BOTH hold:
      1. an explicit date and/or time parses to a FUTURE instant inside a bounded
         window (default 14 days), and
      2. a scheduling keyword sits near it (will / scheduled / launch / meeting /
         unlock / begins / goes live / expected ...).
    It deliberately misses vague phrasing ("sometime next quarter") and can
    misfire; consumers must treat the result as a watch list, never as truth.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from dateutil import parser as dateparser
from pydantic import BaseModel

# Scheduling intent: without one of these near the time, a date is just prose
# ("up 30% since March 2024"), not an upcoming event.
_SCHEDULE_RE = re.compile(
    r"\b(will|scheduled|schedule|upcoming|launch(?:es|ing)?|go(?:es|ing)? live|"
    r"mainnet|testnet|unlock|vesting|release[sd]?|begins?|starts?|kicks? off|"
    r"meeting|summit|hearing|vote|decision|announce[sd]?|expected|slated|"
    r"set to|due|deadline|listing|airdrop|halving|fork|upgrade)\b",
    re.IGNORECASE,
)

# Explicit absolute forms. Each capture is handed to dateutil for normalization.
_MONTHS = (
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
)
_DATE_RES = (
    re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?\b"),          # ISO 2026-10-01[ 14:00]
    re.compile(rf"\b(?:{_MONTHS})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b", re.I),  # October 1[, 2026]
    re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTHS})(?:,?\s+\d{{4}})?\b", re.I),      # 1 October[, 2026]
)
_TIME_RE = re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b|\b\d{1,2}:\d{2}\b", re.I)
_WEEKDAY_RE = re.compile(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)
_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


class ScheduledEvent(BaseModel):
    when: datetime           # resolved to UTC
    matched: str             # the phrase that produced it (audit trail)
    claim: str               # the sentence it came from
    source: str = ""
    symbols: list[str] = []


def _combine(date_str: str | None, time_str: str | None, now: datetime) -> datetime | None:
    """Resolve a date phrase and/or a time phrase to a single UTC instant."""
    try:
        if date_str:
            base = dateparser.parse(date_str, default=now.replace(hour=0, minute=0, second=0, microsecond=0))
            if time_str:
                t = dateparser.parse(time_str, default=base)
                base = base.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        elif time_str:
            # Time only -> today at that time (may roll to tomorrow below if past).
            t = dateparser.parse(time_str, default=now)
            base = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        else:
            return None
    except (ValueError, OverflowError):
        return None
    if base.tzinfo is None:
        base = base.replace(tzinfo=UTC)
    return base.astimezone(UTC)


def _weekday_to_dt(text: str, time_str: str | None, now: datetime) -> datetime | None:
    """Resolve 'Wednesday [at 2pm]' to the next occurrence."""
    m = _WEEKDAY_RE.search(text)
    if not m:
        return None
    target = _WEEKDAYS.index(m.group(1).lower())
    ahead = (target - now.weekday()) % 7
    day = now + timedelta(days=ahead or 7)  # never "today"; a named weekday means the coming one
    base = _combine(day.strftime("%Y-%m-%d"), time_str, now)
    return base


def extract_events(
    title: str,
    content: str,
    symbols: list[str] | None = None,
    source: str = "",
    now: datetime | None = None,
    horizon_days: int = 14,
) -> list[ScheduledEvent]:
    """Return future scheduled events found in one news item (may be empty)."""
    now = now or datetime.now(UTC)
    limit = now + timedelta(days=horizon_days)
    out: list[ScheduledEvent] = []
    seen: set[datetime] = set()

    for sentence in re.split(r"(?<=[.!?])\s+", f"{title}. {content}"):
        if not _SCHEDULE_RE.search(sentence):
            continue
        time_m = _TIME_RE.search(sentence)
        time_str = time_m.group(0) if time_m else None

        candidates: list[tuple[str, datetime | None]] = []
        for rex in _DATE_RES:
            dm = rex.search(sentence)
            if dm:
                candidates.append((dm.group(0), _combine(dm.group(0), time_str, now)))
        if not candidates:
            wd = _weekday_to_dt(sentence, time_str, now)
            if wd:
                candidates.append((_WEEKDAY_RE.search(sentence).group(0), wd))

        for matched, when in candidates:
            if when is None or when in seen or not (now < when <= limit):
                continue
            seen.add(when)
            out.append(
                ScheduledEvent(
                    when=when,
                    matched=f"{matched}{' ' + time_str if time_str else ''}",
                    claim=sentence.strip()[:250],
                    source=source,
                    symbols=symbols or [],
                )
            )
    return out


__all__ = ["ScheduledEvent", "extract_events"]
