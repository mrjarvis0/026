"""A015 tests — config-driven gating, evidence discipline, snapshot-aware pair-change,
and the read-only (never buy/sell) invariant. Run: pytest agents/A015_*/tests -q
"""
from agents.A015_Exchange_Listing_Delisting_Intelligence.core import config_loader as cfg
from agents.A015_Exchange_Listing_Delisting_Intelligence.detectors import (
    detect_delisting,
    detect_new_listing,
    detect_pair_change,
    detect_status_change,
    run_all,
)
from agents.A015_Exchange_Listing_Delisting_Intelligence.tools.diff_engine import diff_snapshots


def _change(exchange, symbol, change_type, old=None, new=None):
    return {"exchange": exchange, "symbol": symbol, "change_type": change_type,
            "old_value": old, "new_value": new, "detected_at": "2026-09-21T00:00:00Z"}


# --- config loader (upgrade: config-driven, not hard-coded) ---
def test_evidence_backed_is_exactly_the_three_studied_exchanges():
    backed = {e for e in cfg.exchanges() if cfg.is_evidence_backed(e)}
    assert backed == {"binance", "bybit", "coinbase"}


def test_fetch_status_read_from_config():
    assert cfg.has_fetch_status("binance") is True
    assert cfg.has_fetch_status("kraken") is True
    assert cfg.has_fetch_status("coinbase") is False   # no fetchStatus (README §4.2)


# --- diff engine ---
def test_diff_engine_add_and_change():
    old = {"A/USDT": {"active": True}, "B/USDT": {"active": True}}
    new = {"A/USDT": {"active": True}, "B/USDT": {"active": False}, "C/USDT": {"active": True}}
    kinds = {c.change_type for c in diff_snapshots(old, new)}
    assert kinds == {"changed", "added"}


# --- NEW_LISTING evidence gating ---
def test_new_listing_binance_is_evidence_backed():
    [r] = detect_new_listing([_change("binance", "FOO/USDT", "added")])
    assert r["event_type"] == "NEW_LISTING" and r["evidence_backed"] is True
    assert r["median_day_1_effect_pct"] == 41


def test_new_listing_other_exchange_insufficient_sample():
    [r] = detect_new_listing([_change("kraken", "FOO/USDT", "added")])
    assert r["evidence_backed"] is False and r["median_day_1_effect_pct"] is None
    assert "insufficient sample" in r["historical_context"]


# --- DELISTING ---
def test_delisting_reason_gated_annotation():
    [r] = detect_delisting([_change("binance", "OLD/USDT", "removed")], stated_reason="low-liquidity")
    assert r["event_type"] == "DELISTING" and r["median_crash_pct"] == -25
    [other] = detect_delisting([_change("kraken", "OLD/USDT", "removed")])
    assert other["median_crash_pct"] is None


# --- STATUS_CHANGE (config-gated by has_fetch_status) ---
def test_status_change_fires_only_for_fetch_status_exchanges():
    halt = _change("binance", "X/USDT", "changed", old={"status": "TRADING"}, new={"status": "HALT"})
    assert len(detect_status_change([halt])) == 1
    halt_cb = _change("coinbase", "X/USDT", "changed", old={"status": "TRADING"}, new={"status": "HALT"})
    assert detect_status_change([halt_cb]) == []   # coinbase has no fetchStatus


# --- PAIR_CHANGE (snapshot-aware; the real upgrade) ---
def test_pair_change_returns_empty_without_snapshots():
    assert detect_pair_change([_change("binance", "ETH/BTC", "added")]) == []


def test_pair_change_added_pair_for_existing_base():
    old, new = {"ETH/USDT": {}}, {"ETH/USDT": {}, "ETH/BTC": {}}
    [r] = detect_pair_change([_change("binance", "ETH/BTC", "added")], old, new)
    assert r["event_type"] == "PAIR_CHANGE" and r["pair_added"] is True and r["base_asset"] == "ETH"


def test_pair_change_new_base_is_not_a_pair_change():
    old, new = {"ETH/USDT": {}}, {"ETH/USDT": {}, "PEPE/USDT": {}}
    assert detect_pair_change([_change("binance", "PEPE/USDT", "added")], old, new) == []


def test_pair_change_removed_pair_base_still_listed():
    old, new = {"ETH/USDT": {}, "ETH/BTC": {}}, {"ETH/USDT": {}}
    [r] = detect_pair_change([_change("binance", "ETH/BTC", "removed")], old, new)
    assert r["pair_removed"] is True


def test_pair_change_removed_last_pair_is_delisting():
    old, new = {"ETH/USDT": {}, "BTC/USDT": {}}, {"BTC/USDT": {}}
    assert detect_pair_change([_change("binance", "ETH/USDT", "removed")], old, new) == []


# --- pipeline + invariant ---
def test_run_all_four_detectors():
    assert set(run_all([], {}, {})) == {"NEW_LISTING", "DELISTING", "STATUS_CHANGE", "PAIR_CHANGE"}


def test_reports_never_say_buy_or_sell():
    [r] = detect_new_listing([_change("binance", "FOO/USDT", "added")])
    text = str(r).lower()
    assert "buy" not in text and "sell" not in text


# --- mutual exclusion when snapshots are supplied (no double-counting) ---
def test_new_listing_skips_existing_base_pair_add_with_snapshot():
    old = {"ETH/USDT": {}}
    # ETH/BTC is a pair add for existing base ETH -> NOT a new listing
    assert detect_new_listing([_change("binance", "ETH/BTC", "added")], old_snapshot=old) == []
    # a genuinely new base is still a listing
    [r] = detect_new_listing([_change("binance", "PEPE/USDT", "added")], old_snapshot=old)
    assert r["event_type"] == "NEW_LISTING"


def test_delisting_skips_pair_removal_when_base_still_listed():
    new = {"ETH/USDT": {}}
    # ETH/BTC removed but ETH still trades -> NOT a delisting
    assert detect_delisting([_change("binance", "ETH/BTC", "removed")], new_snapshot=new) == []


def test_run_all_does_not_double_count_a_pair_add():
    old = {"ETH/USDT": {}}
    new = {"ETH/USDT": {}, "ETH/BTC": {}}
    out = run_all([_change("binance", "ETH/BTC", "added")], old, new)
    assert out["NEW_LISTING"] == []          # not a new listing...
    assert len(out["PAIR_CHANGE"]) == 1      # ...only a pair change
