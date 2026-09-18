"""Tests for the merged T01 upgrades: fees + expectancy, ATR stops/sizing,
trailing stops, VWAP confluence, ATR/VWAP indicators, and the Kraken fallback.

Run:  python -m pytest agents/T01_Smart_Binance_Intelligence/tests/ -q
(from the T01 agent root, with backend on the path)
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

# T01 agent root on the path so `import backend...` works from anywhere.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import config
from backend.analysis import indicators, risk, signals
from backend.data import database as db
from backend.trading import performance
from backend.trading.paper_engine import PaperEngine


# ---------------- fixtures ----------------

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point the DB at a throwaway file and start from a clean schema."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t01_test.db")
    db.init_db()
    return db


def _synth_ohlcv(n=120, start=100.0, step=0.5):
    """A gently rising OHLCV series with enough bars to warm every indicator."""
    rows = []
    ts = 1_700_000_000_000
    price = start
    for i in range(n):
        o = price
        c = price + step
        h = c + 0.3
        low = o - 0.3
        rows.append([ts + i * 300_000, o, h, low, c, 10.0 + i])
        price = c
    return rows


# ---------------- indicators ----------------

def test_compute_all_has_atr_and_vwap():
    df = indicators.compute_all(_synth_ohlcv())
    assert "atr" in df.columns and "vwap" in df.columns
    # last ATR/VWAP are real numbers once warmed up
    assert df["atr"].iloc[-1] > 0
    assert df["vwap"].iloc[-1] > 0


def test_atr_is_nonnegative():
    df = indicators.compute_all(_synth_ohlcv())
    assert (df["atr"].dropna() >= 0).all()


# ---------------- risk: ATR stops & sizing ----------------

def test_fixed_fallback_matches_legacy(monkeypatch):
    """atr=0 must reproduce the old fixed-% stop/target exactly."""
    entry = 100.0
    sl = risk.stop_loss_price(entry, "buy", atr=0.0)
    tp = risk.take_profit_price(entry, "buy", atr=0.0)
    assert sl == round(entry * (1 - config.STOP_LOSS_PCT), 8)
    assert tp == round(entry * (1 + config.TAKE_PROFIT_PCT), 8)


def test_atr_stop_uses_multiplier(monkeypatch):
    monkeypatch.setattr(config, "USE_ATR_STOPS", True)
    entry, atr = 100.0, 4.0
    sl = risk.stop_loss_price(entry, "buy", atr=atr)
    tp = risk.take_profit_price(entry, "buy", atr=atr)
    assert sl == round(entry - atr * config.ATR_STOP_MULT, 8)
    assert tp == round(entry + atr * config.ATR_TP_MULT, 8)


def test_atr_disabled_ignores_atr(monkeypatch):
    monkeypatch.setattr(config, "USE_ATR_STOPS", False)
    entry, atr = 100.0, 4.0
    sl = risk.stop_loss_price(entry, "buy", atr=atr)
    assert sl == round(entry * (1 - config.STOP_LOSS_PCT), 8)


def test_wider_atr_shrinks_position(monkeypatch):
    monkeypatch.setattr(config, "USE_ATR_STOPS", True)
    small = risk.position_size(1000.0, 100.0, mode="paper", atr=1.0)
    big = risk.position_size(1000.0, 100.0, mode="paper", atr=8.0)
    assert big < small   # more volatility -> smaller size for the same $ risk


# ---------------- trailing stop ----------------

def test_trailing_ratchets_up_in_profit(monkeypatch):
    monkeypatch.setattr(config, "TRAIL_ENABLED", True)
    monkeypatch.setattr(config, "TRAIL_PCT", 0.02)
    # entry 100, price ran to 110 -> trail should sit at 110*0.98 = 107.8
    new = risk.maybe_trail_stop(current_stop=98.0, price=110.0, entry=100.0)
    assert new == pytest.approx(107.8)


def test_trailing_never_loosens(monkeypatch):
    monkeypatch.setattr(config, "TRAIL_ENABLED", True)
    monkeypatch.setattr(config, "TRAIL_PCT", 0.02)
    # existing stop already higher than the trail candidate -> keep it (None)
    assert risk.maybe_trail_stop(current_stop=109.0, price=110.0, entry=100.0) is None


def test_trailing_inactive_below_entry(monkeypatch):
    monkeypatch.setattr(config, "TRAIL_ENABLED", True)
    assert risk.maybe_trail_stop(current_stop=98.0, price=99.0, entry=100.0) is None


def test_trailing_respects_disable(monkeypatch):
    monkeypatch.setattr(config, "TRAIL_ENABLED", False)
    assert risk.maybe_trail_stop(current_stop=98.0, price=110.0, entry=100.0) is None


# ---------------- VWAP confluence in signals ----------------

def test_vwap_factor_present():
    above = signals._evaluate_vwap(price=105.0, vwap_v=100.0)
    below = signals._evaluate_vwap(price=95.0, vwap_v=100.0)
    assert above == [("above_vwap", 0.7)]
    assert below == [("below_vwap", -0.7)]


def test_signal_includes_vwap_indicator():
    df = indicators.compute_all(_synth_ohlcv())
    sig = signals.generate_signal(df)
    assert "vwap" in sig.details["indicators"]


# ---------------- paper fees ----------------

def test_paper_fees_reduce_pnl(temp_db, monkeypatch):
    monkeypatch.setattr(config, "PAPER_FEE_PCT", 0.001)
    eng = PaperEngine(start_balance=10_000.0)
    trade = eng.open_trade("BTC/USDT", 100.0, "test")
    assert trade is not None
    qty = trade["quantity"]
    # Close at the SAME price: with zero price move, a round-trip fee makes PnL
    # strictly negative (you pay fees on both legs).
    res = eng.close_trade(trade, 100.0, "test_close")
    assert res["pnl"] < 0
    # magnitude ~ entry_fee + exit_fee on the notional
    expected = -(qty * 100.0) * config.PAPER_FEE_PCT * 2
    assert res["pnl"] == pytest.approx(expected, rel=1e-3)


def test_paper_open_debits_fee(temp_db, monkeypatch):
    monkeypatch.setattr(config, "PAPER_FEE_PCT", 0.001)
    eng = PaperEngine(start_balance=10_000.0)
    before = eng.balance
    trade = eng.open_trade("ETH/USDT", 50.0, "test")
    spent = before - eng.balance
    # spent must equal notional * (1 + fee), not bare notional
    assert spent == pytest.approx(trade["quantity"] * 50.0 * (1 + config.PAPER_FEE_PCT))


# ---------------- expectancy ----------------

def test_expectancy_math(temp_db):
    # two +10 wins and one -5 loss -> win_rate 2/3, avg_win 10, avg_loss -5
    for pnl in (10.0, 10.0, -5.0):
        tid = db.insert_trade({
            "mode": "paper", "symbol": "BTC/USDT", "side": "buy",
            "entry_price": 100.0, "quantity": 1.0, "opened_at": "t",
        })
        db.close_trade(tid, 100.0, pnl, pnl, "test")
    m = performance.compute_metrics("paper")
    expected = (10.0 * (2 / 3)) - (5.0 * (1 / 3))
    assert m["expectancy"] == pytest.approx(round(expected, 4))


def test_empty_metrics_have_expectancy(temp_db):
    m = performance.compute_metrics("paper")
    assert m["total_trades"] == 0 and m["expectancy"] == 0.0


# ---------------- collector geo-block detection ----------------

def test_geo_block_detection():
    from backend.data import collector
    assert collector._is_geo_blocked(Exception("binance {'code': 0, 'msg': 'Service unavailable 451'}"))
    assert not collector._is_geo_blocked(Exception("some other network hiccup"))
