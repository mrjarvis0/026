"""Shared fixtures for the event-bus tests: a fake clock and golden event builders."""
import copy
from datetime import UTC, datetime, timedelta

MANIFESTS = {"A015": {"produces": [{"type": t, "schema_version": 1} for t in (
    "a015.listing.delisted", "a015.listing.new", "a015.market.status_changed", "a015.market.pair_changed")]}}


def sample_event(**overrides):
    event = {
        "event_id": "evt_3f9a21c0e4b1d5a7",
        "type": "a015.listing.delisted",
        "schema_version": 1,
        "source": "A015",
        "subject": "market:binance:XYZ/USDT",
        "event_time": None,
        "event_window": {"from": "2026-10-28T09:00:00+00:00", "to": "2026-10-28T09:15:02+00:00"},
        "observed_at": "2026-10-28T09:15:02+00:00",
        "known_at": None,
        "trace_id": "trc_3f9a21c0e4b1d5a7",
        "causation_id": None,
        "detector": {"id": "DELISTING", "maturity": "implemented", "ceiling": None},
        "confidence": None,
        "coverage": {"complete": True, "as_of": "2026-10-28T09:15:02+00:00", "lag_s": None,
                     "note": "spot only, 3705 markets"},
        "evidence": [{"source": "ccxt.fetch_markets:binance", "locator": "snapshot:3f9a21c0e4b1",
                      "retrieved_at": "2026-10-28T09:15:02+00:00"}],
        "untrusted": False,
        "data": {"exchange": "binance", "symbol": "XYZ/USDT", "base": "XYZ",
                 "stated_reason": "unspecified"},
    }
    event.update(copy.deepcopy(overrides))
    return event




def event_n(n: int, **overrides):
    """A distinct valid delisting event (stable id per n)."""
    return sample_event(event_id=f"evt_{n:016x}", trace_id=f"trc_{n:016x}",
                        subject=f"market:binance:T{n}/USDT",
                        data={"exchange": "binance", "symbol": f"T{n}/USDT", "base": f"T{n}",
                              "stated_reason": "unspecified"}, **overrides)


def listing_n(n: int, **overrides):
    """A distinct valid new-listing event, no detector (always passes the maturity gate)."""
    return sample_event(event_id=f"evt_{n + 0x1000:016x}", type="a015.listing.new", detector=None,
                        subject=f"market:binance:N{n}/USDT",
                        data={"exchange": "binance", "symbol": f"N{n}/USDT", "base": f"N{n}"}, **overrides)


class FakeClock:
    """Callable returning aware UTC datetimes; advance() moves time forward."""

    def __init__(self, start=datetime(2026, 10, 28, 9, 30, tzinfo=UTC)):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds: float):
        self.now += timedelta(seconds=seconds)
