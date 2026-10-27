"""Tests for the F-track foundation fixes (F1–F4).

- F1: .env.example documents every knob config.py reads.
- F2: paper and real engines share one fee formula (backend/trading/fees.py).
- F3: every strategy-param change is journaled in param_history.
- F4: heartbeat + stale-feed auto-pause (+ /api/health reads it).

Run:  python -m pytest agents/T01_Smart_Binance_Intelligence/tests/ -q
"""
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# T01 agent root on the path so `import backend...` works from anywhere.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import config
from backend.data import database as db
from backend.strategy import engine, reflection
from backend.trading import fees


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point the DB at a throwaway file and start from a clean schema."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t01_foundation.db")
    db.init_db()
    return db


# ---------------- F1: .env.example == config.py knobs ----------------

def _config_keys() -> set[str]:
    src = (ROOT / "backend" / "config.py").read_text()
    return set(re.findall(r'os\.getenv\(\s*"([A-Z][A-Z0-9_]*)"', src))


def _example_keys() -> set[str]:
    keys = set()
    for line in (ROOT / ".env.example").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            keys.add(line.split("=", 1)[0].strip())
    return keys


def test_env_example_covers_every_config_knob():
    missing = _config_keys() - _example_keys()
    assert not missing, f".env.example is missing knobs: {sorted(missing)}"


def test_real_fee_knob_exists():
    assert hasattr(config, "REAL_FEE_PCT")
    assert config.REAL_FEE_PCT >= 0


# ---------------- F2: one fee formula for both engines ----------------

def test_fee_helpers_agree():
    pnl, pct = fees.round_trip_pnl(100.0, 110.0, 2.0, 0.001)
    assert pnl == pytest.approx(2.0 * 110.0 * 0.999 - 2.0 * 100.0 * 1.001)
    assert pct == pytest.approx(pnl / (2.0 * 100.0 * 1.001) * 100.0)
    # flat trade loses exactly the round-trip fee
    flat, _ = fees.round_trip_pnl(100.0, 100.0, 1.0, 0.001)
    assert flat == pytest.approx(-100.0 * 0.001 * 2, rel=1e-9)


def test_paper_close_records_net_pnl(temp_db):
    """Paper close must equal the shared fee formula (not hand-rolled math)."""
    from backend.trading.paper_engine import PaperEngine
    eng = PaperEngine(start_balance=10_000.0)
    trade = eng.open_trade("BTC/USDT", 100.0, "f2-test")
    assert trade is not None
    paper = eng.close_trade(trade, 110.0, "f2-test")
    expected, _ = fees.round_trip_pnl(100.0, 110.0, trade["quantity"],
                                      config.PAPER_FEE_PCT)
    assert paper["pnl"] == pytest.approx(round(expected, 4))
    # fees make the fee-free number strictly worse — proves fee is IN the math
    assert paper["pnl"] < (110.0 - 100.0) * trade["quantity"]


def test_real_close_uses_fee_formula(temp_db, monkeypatch):
    """RealEngine.close_trade must net fees (not old gross (fill-entry)*qty)."""
    from backend.trading import real_engine
    from backend.trading.real_engine import RealEngine

    class FakeEx:
        def create_order(self, *a, **k):
            return {"average": 110.0, "filled": 1.0}

    monkeypatch.setattr(real_engine.collector, "get_exchange", lambda: FakeEx())
    monkeypatch.setattr(RealEngine, "_guard", lambda self: None)
    monkeypatch.setattr(config, "REAL_FEE_PCT", 0.001)
    pos = {"id": db.insert_trade({"mode": "real", "symbol": "BTC/USDT",
                                  "side": "buy", "entry_price": 100.0,
                                  "quantity": 1.0, "opened_at": "t"}),
           "symbol": "BTC/USDT", "quantity": 1.0, "entry_price": 100.0}
    res = RealEngine().close_trade(pos, 110.0, "f2-test")
    expected, _ = fees.round_trip_pnl(100.0, 110.0, 1.0, 0.001)
    assert res["pnl"] == pytest.approx(round(expected, 4))
    assert res["pnl"] == pytest.approx(110.0 * 0.999 - 100.0 * 1.001)


# ---------------- F3: param_history audit trail ----------------

def _add_closed(mode, pnl, *, regime=None, factor=None, exit_reason="stop_loss"):
    tid = db.insert_trade({
        "mode": mode, "symbol": "BTC/USDT", "side": "buy",
        "entry_price": 100.0, "quantity": 1.0, "opened_at": "t",
        "entry_regime": regime, "entry_factor": factor,
    })
    db.close_trade(tid, 100.0, pnl, pnl, exit_reason)
    return tid


def test_self_tune_journals_change(temp_db):
    for _ in range(12):   # weak accuracy (<50%) forces the threshold up
        _add_closed("paper", -1.0, regime="trend", factor="rsi",
                    exit_reason="signal_sell")
    before = engine.load_params()
    engine.self_tune()
    assert engine.load_params()["net_threshold"] > before["net_threshold"]
    hist = db.get_param_history()
    assert len(hist) >= 1
    assert hist[0]["source"] == "self_tune"
    assert "accuracy" in hist[0]["reason"]
    snap = json.loads(hist[0]["params"])
    assert snap["net_threshold"] == engine.load_params()["net_threshold"]


def test_reflection_journals_change(temp_db, monkeypatch):
    monkeypatch.setattr(config, "REFLECT_MIN_TRADES", 4)
    for _ in range(8):
        _add_closed("paper", -1.0, regime="chop", factor="bb",
                    exit_reason="signal_sell")
    changes = reflection.diagnose_and_correct("paper")
    assert changes
    hist = db.get_param_history()
    assert hist[0]["source"] == "reflection"
    assert "loss_rate" in hist[0]["reason"]


def test_no_history_row_when_nothing_changed(temp_db):
    engine.save_params(engine.load_params(), source="manual", reason="noop")
    assert db.get_param_history() == []


# ---------------- F4: heartbeat + auto-pause ----------------

def test_feed_fresh_when_idle_no_cycle():
    from backend.bot import TradingBot
    b = TradingBot.__new__(TradingBot)   # no DB/engine side effects
    b.running = False
    b.last_cycle_ts = None
    fresh, age = TradingBot.feed_fresh(b)
    assert fresh is True and age is None


def test_feed_stale_when_running_no_cycle():
    from backend.bot import TradingBot
    b = TradingBot.__new__(TradingBot)
    b.running = True
    b.last_cycle_ts = None
    fresh, _ = TradingBot.feed_fresh(b)
    assert fresh is False


def test_feed_fresh_uses_cycle_age():
    from backend.bot import TradingBot, _now_iso
    b = TradingBot.__new__(TradingBot)
    b.running = True
    b.last_cycle_ts = (datetime.now(timezone.utc)
                       - timedelta(seconds=120)).isoformat()
    fresh, age = TradingBot.feed_fresh(b)
    assert fresh is False and age and age >= 120
    b.last_cycle_ts = _now_iso()
    fresh, _ = TradingBot.feed_fresh(b)
    assert fresh is True


def test_consecutive_errors_auto_pause(temp_db, monkeypatch):
    from collections import deque
    from backend.bot import TradingBot, MAX_CONSECUTIVE_ERRORS
    b = TradingBot.__new__(TradingBot)
    b.running = True
    b.consecutive_errors = 0
    b.activity = deque(maxlen=120)
    monkeypatch.setattr(db, "set_state", lambda *a, **k: None)
    for _ in range(MAX_CONSECUTIVE_ERRORS - 1):
        b._note_cycle_error()
        assert b.running is True
    b._note_cycle_error()
    assert b.running is False   # auto-paused on the Nth consecutive failure
    b._note_cycle_ok()
    assert b.consecutive_errors == 0 and b.last_cycle_ts is not None


def test_health_and_history_endpoints(temp_db):
    pytest.importorskip("fastapi.testclient")
    from fastapi.testclient import TestClient
    import backend.main as mainmod
    c = TestClient(mainmod.app, raise_server_exceptions=False,
                    base_url="http://127.0.0.1:8000")
    r = c.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    for k in ("ok", "running", "symbol", "timeframe", "cycle_age_seconds",
              "feed_stale", "consecutive_errors", "trading_allowed",
              "real_unlocked"):
        assert k in body
    r2 = c.get("/api/params/history?limit=5")
    assert r2.status_code == 200 and "history" in r2.json()
