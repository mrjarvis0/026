from backend.data import database as db
from backend.trading.paper_engine import PaperEngine


def setup_module(module):
    db.init_db()


def test_paper_engine_init():
    engine = PaperEngine()
    engine.reset(start_balance=1000)
    assert engine.balance == 1000


def test_open_trade():
    engine = PaperEngine()
    engine.reset(start_balance=1000)

    trade = engine.open_trade("BTC/USDT", 50000, "test")
    assert trade is not None
    assert trade["symbol"] == "BTC/USDT"
    assert trade["entry_price"] == 50000

    # Check paper balance is reduced
    assert engine.balance < 1000


def test_equity():
    engine = PaperEngine()
    engine.reset(start_balance=1000)

    engine.open_trade("BTC/USDT", 50000, "test")
    # Mark price stays the same, equity should still be 1000
    eq = engine.equity({"BTC/USDT": 50000})
    assert eq == 1000
