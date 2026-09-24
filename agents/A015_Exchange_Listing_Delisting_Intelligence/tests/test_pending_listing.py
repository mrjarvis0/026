"""Tests for the ANNOUNCED_LISTING (pending) detector + title token extraction.
Deterministic — no network (announcements are injected)."""
from datetime import datetime, timezone

from agents.A015_Exchange_Listing_Delisting_Intelligence.detectors.pending_listing import (
    detect_pending_listings,
)
from agents.A015_Exchange_Listing_Delisting_Intelligence.tools.text_feeds.announcements import (
    extract_tokens,
)

_NOW = datetime(2026, 9, 21, tzinfo=timezone.utc)


def _ann(exchange, tokens, announced_at=None, title="t", url="u"):
    return {"exchange": exchange, "tokens": tokens, "announced_at": announced_at,
            "title": title, "url": url}


def test_pending_flags_announced_not_yet_listed_with_age():
    anns = [_ann("okx", ["FOO"], announced_at="2026-09-10T00:00:00+00:00")]
    [r] = detect_pending_listings(anns, {"okx": {"BTC", "ETH"}}, now=_NOW, stale_days=3)
    assert r["event_type"] == "ANNOUNCED_LISTING" and r["token"] == "FOO"
    assert r["still_pending"] is True
    assert r["days_since_announcement"] == 11.0 and r["is_stale"] is True


def test_recent_announcement_is_not_stale():
    anns = [_ann("okx", ["BAR"], announced_at="2026-09-20T00:00:00+00:00")]
    [r] = detect_pending_listings(anns, {"okx": set()}, now=_NOW, stale_days=3)
    assert r["days_since_announcement"] == 1.0 and r["is_stale"] is False


def test_already_listed_token_is_not_pending():
    anns = [_ann("okx", ["BTC"])]
    assert detect_pending_listings(anns, {"okx": {"BTC"}}, now=_NOW) == []


def test_pending_dedups_same_token():
    anns = [_ann("okx", ["FOO"], title="a"), _ann("okx", ["FOO"], title="b")]
    assert len(detect_pending_listings(anns, {"okx": set()}, now=_NOW)) == 1


def test_missing_announce_date_gives_none_age_not_stale():
    [r] = detect_pending_listings([_ann("okx", ["ZZZ"])], {"okx": set()}, now=_NOW)
    assert r["days_since_announcement"] is None and r["is_stale"] is False


def test_extract_tokens_parenthesised_and_bare():
    assert "FOO" in extract_tokens("Binance Will List Foobar (FOO)")
    assert set(extract_tokens("OKX to list PONSUSD, RAYUSD X-Perps")) >= {"PONS", "RAY"}
    assert extract_tokens("OKX to list perpetual futures for AKE crypto") == ["AKE"]
    assert "USDC" not in extract_tokens("OKX to list USDC trading pairs for xAAPL")


def test_extract_tokens_ignores_non_listing_service_titles():
    # "Will Add X on Earn / VIP Loan / Margin" is not a trading listing -> no ticker guessed
    # (this is the fix for the "VIP" false positive seen on live Binance data)
    assert extract_tokens("Binance Will Add Foo on Earn, Buy Crypto, VIP Loan & Margin") == []
    assert extract_tokens("Binance Will Add Something on Simple Earn Flexible") == []
