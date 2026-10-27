"""
A002 event extraction tests (offline). Run directly:
    python agents/A002_News_Intelligence/tests/test_events.py
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from agents.A002_News_Intelligence.intelligence.events import extract_events

PASS = 0
FAIL = 0
NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)  # a Monday


def check(label: str, ok: bool) -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [OK] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}")


def only(title, content="", **kw):
    return extract_events(title, content, now=NOW, **kw)


def run() -> None:
    print("events:")

    # ISO date + time
    e = only("Protocol X mainnet will go live on 2026-06-10 at 14:00 UTC")
    check("iso date+time found", len(e) == 1)
    check("iso resolves correctly", e and e[0].when == datetime(2026, 6, 10, 14, 0, tzinfo=UTC))

    # Month-name date
    e = only("The token unlock is scheduled for June 12, 2026")
    check("month-name date found", len(e) == 1 and e[0].when.day == 12)

    # Weekday + time -> next occurrence (NOW is Monday; Wednesday = +2 days)
    e = only("The FOMC meeting is scheduled for Wednesday at 2pm")
    check("weekday resolves to coming wednesday", e and e[0].when.day == 3 and e[0].when.hour == 14)

    # No scheduling keyword -> ignored even with a date
    e = only("Bitcoin is up 40% since January 2024")
    check("bare date without intent ignored", e == [])

    # Past date -> ignored
    e = only("The upgrade launched on 2026-05-01 at 10:00 UTC")
    check("past event ignored", e == [])

    # Beyond horizon -> ignored (default 14 days)
    e = only("Mainnet launch scheduled for 2026-09-01")
    check("beyond-horizon event ignored", e == [])

    # Carries symbols + source through
    e = only("ETH staking unlock begins 2026-06-05 at 09:00 UTC", symbols=["ETH"], source="rss_x")
    check("symbols carried", e and e[0].symbols == ["ETH"])
    check("source carried", e and e[0].source == "rss_x")

    # Vague phrasing -> nothing (known ceiling, but must not crash)
    e = only("The team says a launch is coming sometime next quarter")
    check("vague phrasing yields nothing", e == [])


if __name__ == "__main__":
    run()
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)
