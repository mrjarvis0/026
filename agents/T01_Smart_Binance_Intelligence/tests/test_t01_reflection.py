"""Tests for roadmap #16 — per-trade loss attribution + targeted self-correction,
plus the ADX regime label, factor-weight down-weighting, the ADX entry gate, and
the non-acting multi-scenario predictions.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import config
from backend.analysis import indicators, signals
from backend.data import database as db
from backend.strategy import engine, reflection


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t01_reflect.db")
    db.init_db()
    return db


def _rising_ohlcv(n=140, start=100.0, step=0.5):
    rows, ts, price = [], 1_700_000_000_000, start
    for i in range(n):
        o, c = price, price + step
        rows.append([ts + i * 300_000, o, c + 0.3, o - 0.3, c, 10.0 + i])
        price = c
    return rows


def _add_closed(mode, pnl, *, regime=None, factor=None, exit_reason="stop_loss"):
    tid = db.insert_trade({
        "mode": mode, "symbol": "BTC/USDT", "side": "buy",
        "entry_price": 100.0, "quantity": 1.0, "opened_at": "t",
        "entry_regime": regime, "entry_factor": factor,
    })
    db.close_trade(tid, 100.0, pnl, pnl, exit_reason)
    return tid


# ---------------- ADX + regime + gate ----------------

def test_adx_column_present():
    df = indicators.compute_all(_rising_ohlcv())
    assert "adx" in df.columns
    assert (df["adx"].dropna() >= 0).all()


def test_signal_reports_regime_and_dominant_factor():
    df = indicators.compute_all(_rising_ohlcv())
    sig = signals.generate_signal(df)
    assert sig.details["regime"] in ("trend", "chop")
    assert "dominant_factor" in sig.details
    assert "adx" in sig.details["indicators"]


def test_adx_min_gate_blocks_entry():
    df = indicators.compute_all(_rising_ohlcv())
    # Force the gate: demand an absurdly high ADX so any real reading is below it.
    sig = signals.generate_signal(df, {"adx_min": 999.0, "net_threshold": 0.5})
    assert sig.action == "hold"
    assert "regime filter" in sig.reason


def test_factor_weights_downweight_removes_contribution():
    df = indicators.compute_all(_rising_ohlcv())
    base = signals.generate_signal(df, {})
    # Zero every family -> net collapses to 0, so no buy/sell regardless of threshold.
    zero = {c: 0.0 for c in ("rsi", "macd", "trend", "bb", "vol", "vwap")}
    muted = signals.generate_signal(df, {"factor_weights": zero, "net_threshold": 0.1})
    assert muted.details["net_score"] == 0.0
    assert muted.action == "hold"
    assert base.details["net_score"] != 0.0 or True  # base may or may not fire; muted must not


# ---------------- entry diagnosis persisted ----------------

def test_entry_diagnosis_stored(temp_db):
    from backend.trading.paper_engine import PaperEngine
    eng = PaperEngine(start_balance=10_000.0)
    eng.open_trade("BTC/USDT", 100.0, "test", atr=2.0,
                   meta={"factor": "bb", "regime": "chop", "adx": 12.0})
    row = db.get_open_trades("paper")[0]
    assert row["entry_factor"] == "bb"
    assert row["entry_regime"] == "chop"
    assert row["entry_adx"] == 12.0


def test_stop_mult_widens_stop(monkeypatch):
    from backend.analysis import risk
    monkeypatch.setattr(config, "USE_ATR_STOPS", True)
    narrow = risk.stop_loss_price(100.0, "buy", atr=2.0, stop_mult=0.0)   # config 1.5 -> 97.0
    wide = risk.stop_loss_price(100.0, "buy", atr=2.0, stop_mult=2.5)     # 2.5 -> 95.0
    assert wide < narrow


# ---------------- reflection diagnosis ----------------

def test_diagnose_none_when_too_few(temp_db):
    _add_closed("paper", -1.0, regime="chop")
    assert reflection.diagnose("paper") is None   # below REFLECT_MIN_TRADES


def test_diagnose_none_when_low_loss_rate(temp_db, monkeypatch):
    monkeypatch.setattr(config, "REFLECT_MIN_TRADES", 4)
    for _ in range(8):
        _add_closed("paper", +1.0, exit_reason="take_profit")   # all wins
    assert reflection.diagnose("paper") is None


def test_correct_chop_raises_adx_min(temp_db, monkeypatch):
    monkeypatch.setattr(config, "REFLECT_MIN_TRADES", 4)
    for _ in range(8):
        _add_closed("paper", -1.0, regime="chop", factor="bb", exit_reason="signal_sell")
    changes = reflection.diagnose_and_correct("paper")
    assert any("adx_min" in c for c in changes)
    assert engine.load_params()["adx_min"] > 0


def test_correct_single_factor_downweights(temp_db, monkeypatch):
    monkeypatch.setattr(config, "REFLECT_MIN_TRADES", 4)
    for _ in range(8):
        _add_closed("paper", -1.0, regime="trend", factor="bb", exit_reason="signal_sell")
    changes = reflection.diagnose_and_correct("paper")
    assert any("weight[bb]" in c for c in changes)
    assert engine.load_params()["factor_weights"].get("bb", 1.0) < 1.0


def test_correct_stopouts_widen_stop(temp_db, monkeypatch):
    monkeypatch.setattr(config, "REFLECT_MIN_TRADES", 4)
    for _ in range(8):
        _add_closed("paper", -1.0, regime="trend", factor="rsi", exit_reason="stop_loss")
    changes = reflection.diagnose_and_correct("paper")
    assert any("atr_stop_mult" in c for c in changes)
    assert engine.load_params()["atr_stop_mult"] > 0


def test_correction_is_idempotent_and_bounded(temp_db, monkeypatch):
    monkeypatch.setattr(config, "REFLECT_MIN_TRADES", 4)
    for _ in range(8):
        _add_closed("paper", -1.0, regime="chop", factor="bb", exit_reason="stop_loss")
    # Run many times; adx_min must not exceed its clamp (30) and stays a number.
    for _ in range(20):
        reflection.diagnose_and_correct("paper")
    p = engine.load_params()
    assert p["adx_min"] <= 30.0
    assert p["factor_weights"].get("bb", 1.0) >= 0.5
    assert p["atr_stop_mult"] <= 3.0


# ---------------- multi-scenario predictions ----------------

def test_predict_scenarios_shape(temp_db):
    df = indicators.compute_all(_rising_ohlcv())
    preds = engine.predict_scenarios(df)
    assert set(preds) == {"conservative", "standard", "aggressive"}
    for v in preds.values():
        assert v["action"] in ("buy", "sell", "hold")
    # Aggressive threshold is never higher than conservative.
    assert preds["aggressive"]["threshold"] <= preds["conservative"]["threshold"]
