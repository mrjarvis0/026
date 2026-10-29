"""Phase 0 wiring fixes — each test names the defect it guards.

- real enable/disable must reach the bot's own RealEngine (it cached the flag at start-up).
- the T03 soft veto must run in the live loop (decide() had no caller), only ever blocks an
  ENTRY (never an exit), and consults T03 for the symbol T01 is actually trading.

Run:  python -m pytest agents/T01_Smart_Binance_Intelligence/tests/test_t01_wiring.py -q
"""
import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import config
from backend.analysis import signals
from backend.bot import TradingBot
from backend.data import database as db
from backend.strategy import engine
from backend.trading import performance
from backend.trading.real_engine import RealEngine


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t01_wiring.db")
    db.init_db()
    return db


@pytest.fixture
def real_unlocked(temp_db, monkeypatch):
    """Everything except the operator's enable flag is satisfied."""
    monkeypatch.setattr(performance, "is_real_trading_unlocked", lambda: True)
    monkeypatch.setattr(config, "BINANCE_API_KEY", "k")
    monkeypatch.setattr(config, "BINANCE_API_SECRET", "s")
    db.set_state("real_start_equity", "100")  # skip the balance fetch in enable()


# ---------------- real enable / disable ----------------

def test_disable_from_another_engine_stops_the_running_one(real_unlocked):
    # regression: the API disabled a throwaway RealEngine(); the bot's cached flag stayed True
    bot_engine = RealEngine()
    RealEngine().enable()
    assert bot_engine.ready()[0]
    RealEngine().disable()
    assert not bot_engine.enabled
    assert not bot_engine.ready()[0]


def test_enable_from_another_engine_reaches_the_running_one(real_unlocked):
    # same root cause, other direction: enabling never reached a running bot until restart
    bot_engine = RealEngine()
    assert not bot_engine.ready()[0]
    RealEngine().enable()
    assert bot_engine.ready()[0]


def test_enable_still_refused_while_gate_locked(temp_db, monkeypatch):
    monkeypatch.setattr(performance, "is_real_trading_unlocked", lambda: False)
    monkeypatch.setattr(config, "BINANCE_API_KEY", "k")
    monkeypatch.setattr(config, "BINANCE_API_SECRET", "s")
    from backend.trading.real_engine import RealTradingLocked
    with pytest.raises(RealTradingLocked):
        RealEngine().enable()
    assert not RealEngine().enabled


# ---------------- T03 soft veto ----------------

def _sig(action):
    return signals.Signal(action=action, confidence=0.8, reason="r", price=100.0, details={})


@pytest.fixture
def t03(monkeypatch):
    """Control T03's answer and record which symbol it was asked about."""
    asked = {}

    def fake(symbol=None):
        asked["symbol"] = symbol
        return asked.get("answer", (0, 0.0))

    monkeypatch.setattr(config, "T03_ENABLED", True)
    monkeypatch.setattr(engine, "_t03_consensus", fake)
    return asked


def test_opposing_t03_consensus_vetoes_a_buy(t03):
    t03["answer"] = (-1, 0.9)
    out = engine.apply_t03_veto(_sig("buy"), "BTC/USDT")
    assert out.action == "hold" and out.details["t03_veto"] is True


def test_t03_never_vetoes_an_exit(t03):
    # a veto must not trap the bot in a position it wants out of
    t03["answer"] = (1, 0.95)
    assert engine.apply_t03_veto(_sig("sell"), "BTC/USDT").action == "sell"


def test_weak_or_agreeing_t03_leaves_buy_alone(t03):
    t03["answer"] = (-1, 0.5)
    assert engine.apply_t03_veto(_sig("buy"), "BTC/USDT").action == "buy"
    t03["answer"] = (1, 0.9)
    assert engine.apply_t03_veto(_sig("buy"), "BTC/USDT").action == "buy"


def test_veto_asks_t03_about_the_traded_symbol(t03):
    # regression: T03 was always asked about the configured BTC/USDT, whatever T01 traded
    engine.apply_t03_veto(_sig("buy"), "ETH/USDT")
    assert t03["symbol"] == "ETH/USDT"


def test_t03_disabled_means_no_veto(t03, monkeypatch):
    monkeypatch.setattr(config, "T03_ENABLED", False)
    t03["answer"] = (-1, 0.99)
    assert engine.apply_t03_veto(_sig("buy"), "BTC/USDT").action == "buy"


def test_live_loop_decision_applies_the_veto(temp_db, t03, monkeypatch):
    # regression: decide() carried the veto but nothing called it; the bot's own
    # decision step must go through the overlay
    monkeypatch.setattr(signals, "generate_signal", lambda df, params=None: _sig("buy"))
    t03["answer"] = (-1, 0.9)
    bot = TradingBot()
    bot.symbol = "SOL/USDT"
    out = asyncio.run(bot._decide(None, {}))
    assert out.action == "hold" and out.details["t03_veto"] is True
    assert t03["symbol"] == "SOL/USDT"


def test_live_loop_decision_does_not_wait_forever_on_t03(temp_db, monkeypatch):
    import time
    monkeypatch.setattr(config, "T03_ENABLED", True)
    monkeypatch.setattr(signals, "generate_signal", lambda df, params=None: _sig("buy"))
    monkeypatch.setattr(engine, "_t03_consensus", lambda symbol=None: time.sleep(2) or (-1, 0.9))
    monkeypatch.setattr("backend.bot.T03_TIMEOUT_S", 0.05)
    out = asyncio.run(TradingBot()._decide(None, {}))
    assert out.action == "buy"  # T03 too slow -> no veto, never a stalled cycle
