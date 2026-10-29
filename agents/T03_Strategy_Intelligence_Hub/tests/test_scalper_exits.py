"""Scalper exits: flatten on a risk halt, and a protective stop on every position (operator-approved 2026-10-29).

Testnet only; every transmission still needs armed + the human-confirm phrase. Run:
    python -m pytest agents/T03_Strategy_Intelligence_Hub/tests/test_scalper_exits.py -q
"""
import sys
from pathlib import Path

import pytest

T03_ROOT = Path(__file__).resolve().parent.parent
if str(T03_ROOT) not in sys.path:
    sys.path.insert(0, str(T03_ROOT))

from core.futures import scalper as sc
from core.futures.scalper import FuturesScalper, flatten_order, stop_order
from core.paper import HUMAN_CONFIRM_PHRASE, OrderRefused
from core.paper import binance_futures_testnet as fut


# ---- pure planning ----------------------------------------------------------------------------------------

def test_flatten_closes_a_long_with_a_reduce_only_sell():
    assert flatten_order(0.5, 60_000.0) == {"side": "sell", "qty": 0.5, "notional": 30_000.0, "reduce_only": True}


def test_flatten_closes_a_short_with_a_reduce_only_buy():
    order = flatten_order(-0.3, 60_000.0)
    assert order["side"] == "buy" and order["qty"] == 0.3 and order["reduce_only"] is True


def test_nothing_to_flatten_when_flat():
    assert flatten_order(0.0, 60_000.0) is None and flatten_order(0.0004, 60_000.0) is None   # below min qty


def test_stop_for_a_long_sits_one_atr_below():
    assert stop_order(0.5, 60_000.0, 600.0) == {"side": "sell", "qty": 0.5, "stop_price": 59_400.0}


def test_stop_for_a_short_sits_one_atr_above():
    assert stop_order(-0.5, 60_000.0, 600.0) == {"side": "buy", "qty": 0.5, "stop_price": 60_600.0}


def test_stop_falls_back_to_one_percent_without_an_atr():
    assert stop_order(0.5, 60_000.0, 0.0)["stop_price"] == 59_400.0


def test_no_stop_for_a_flat_target():
    assert stop_order(0.0, 60_000.0, 600.0) is None


# ---- broker calls are gated by the human-confirm phrase ---------------------------------------------------

class FakeClient:
    def __init__(self):
        self.calls = []

    def create_order(self, **kw):
        self.calls.append(("create_order", kw))
        return {"id": "1", "status": "NEW"}

    def cancel_all_orders(self, symbol):
        self.calls.append(("cancel_all_orders", symbol))


def test_submit_stop_is_reduce_only_stop_market():
    client = FakeClient()
    fut.submit_stop(client, "BTC/USDT", "sell", 0.5, 59_400.0, HUMAN_CONFIRM_PHRASE)
    [(_, kw)] = client.calls
    assert kw["type"] == "STOP_MARKET" and kw["side"] == "sell" and kw["amount"] == 0.5
    assert kw["params"]["stopPrice"] == 59_400.0 and kw["params"]["reduceOnly"] is True


def test_stop_and_cancel_refuse_without_the_phrase():
    client = FakeClient()
    with pytest.raises(OrderRefused):
        fut.submit_stop(client, "BTC/USDT", "sell", 0.5, 59_400.0, None)
    with pytest.raises(OrderRefused):
        fut.cancel_open_orders(client, "BTC/USDT", "nope")
    assert client.calls == []


# ---- _sync_stop with a fake broker module ----------------------------------------------------------------

@pytest.fixture
def scalper(monkeypatch):
    s = object.__new__(FuturesScalper)
    s.symbol, s._broker = "BTC/USDT", object()
    log = []
    monkeypatch.setattr(fut, "cancel_open_orders", lambda c, sym, tok=None: log.append(("cancel", sym)))
    monkeypatch.setattr(fut, "submit_stop",
                        lambda c, sym, side, qty, px, tok=None: log.append(("stop", side, qty, px)) or {"id": "9"})
    monkeypatch.setattr(fut, "close_position", lambda c, sym, tok=None: log.append(("close", sym)) or {"id": "c"})
    monkeypatch.setattr(fut, "round_qty", lambda c, sym, q: round(abs(q), 3))
    return s, log


def test_an_entry_gets_old_orders_cancelled_then_a_fresh_stop(scalper):
    s, log = scalper
    notes: list = []
    s._sync_stop(0.5, 60_000.0, 600.0, HUMAN_CONFIRM_PHRASE, notes)
    assert log == [("cancel", "BTC/USDT"), ("stop", "sell", 0.5, 59_400.0)]
    assert any("protective stop" in n for n in notes)


def test_a_flatten_cancels_the_stop_and_places_none(scalper):
    s, log = scalper
    s._sync_stop(0.0, 60_000.0, 600.0, HUMAN_CONFIRM_PHRASE, [])
    assert log == [("cancel", "BTC/USDT")]


def test_if_the_stop_cannot_be_placed_the_position_is_closed(scalper, monkeypatch):
    s, log = scalper

    def refused(*a, **k):
        raise RuntimeError("exchange rejected the stop")

    monkeypatch.setattr(fut, "submit_stop", refused)
    notes: list = []
    s._sync_stop(0.5, 60_000.0, 600.0, HUMAN_CONFIRM_PHRASE, notes)
    assert ("close", "BTC/USDT") in log                                  # never leave a position unprotected
    assert any("STOP FAILED" in n and "flattened" in n for n in notes)
