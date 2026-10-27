"""LiveTrader — run one agent's strategy against a (testnet) account.

Each closed bar: read the target position, reconcile against the account, and place
only the *delta* order. Dry-run by default; testnet only. Faithful to the backtest:
acts on the last FULLY-CLOSED bar (the forming candle is dropped), matching the
`position[t] held over t+1` convention in core/backtest/runner.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from ..config import LiveConfig
from ..data import get_data
from ..learn import MistakeMemory, check_trade, latest_context
from .broker import LiveBroker
from . import state as live_state


def _primary_symbol(config: dict) -> str:
    s = config.get("symbols", config.get("symbol"))
    return s[0] if isinstance(s, (list, tuple)) else s


@dataclass
class Decision:
    agent: str
    bar_ts: str
    target: float
    price: float
    equity: float
    held_units: float
    account_mode: str            # 'testnet' | 'simulated(no keys)'
    order: dict[str, Any] | None = None   # {side, qty, notional}
    placed: bool = False
    armed: bool = False
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if self.order is None:
            act = "no order (position already matches target)"
        else:
            act = f"{self.order['side'].upper()} {self.order['qty']} (~{self.order['notional']:.2f} USDT)"
            act += " [SENT]" if self.placed else " [dry-run]"
        return (f"{self.agent} bar={self.bar_ts} target={self.target:+.0f} "
                f"price={self.price:.2f} equity={self.equity:.2f} held={self.held_units:g} "
                f"[{self.account_mode}] -> {act}")


class LiveTrader:
    def __init__(self, agent_dir: Path, config: dict, strategy, live_cfg: LiveConfig | None = None) -> None:
        self.agent_dir = agent_dir
        self.agent = agent_dir.name
        self.config = config
        self.strategy = strategy
        self.market = config["market"]
        self.symbol = _primary_symbol(config)
        self.timeframe = config.get("timeframe", "1d")
        self.live_cfg = live_cfg or LiveConfig.from_dict(config.get("live"))
        self.broker = LiveBroker(self.market)

    # -- 1. what does the strategy want right now? --
    def decide(self) -> tuple[float, pd.Timestamp, float]:
        d = self.config.get("data", {}) or {}
        data = get_data(self.market, self.symbol, self.timeframe,
                        d.get("start", "2020-01-01"), None, use_cache=False)
        # Drop the still-forming bar (the rightmost candle is incomplete).
        # data.iloc[:-1] is the correct drop regardless of timeframe — on daily
        # data it drops today's forming bar; on 1h it drops the current hour.
        # The old approach `data[data.index < now.normalize()]` was correct for
        # daily only and incorrectly dropped *all* of today's hourly bars on
        # sub-daily timeframes (BUG-FIX). Matches scan.py's `closed = data.iloc[:-1]`.
        closed = data.iloc[:-1]
        if len(closed) < 2:
            raise RuntimeError("not enough closed bars to decide")
        signals = self.strategy.generate_signals(closed)
        target = float(signals["position"].iloc[-1])
        self._last_closed = closed  # kept for the pre-trade guard
        return target, closed.index[-1], float(closed["Close"].iloc[-1])

    # -- 2. read the account (or simulate if no keys / not wired) --
    def _account(self, close_price: float, last_target: float) -> tuple[float, float, float, str, list[str]]:
        notes: list[str] = []
        try:
            if not self.broker.connected:
                self.broker.connect()
            price = self.broker.price(self.symbol)
            equity = self.broker.equity(self.symbol, price)
            held = self.broker.position_units(self.symbol)
            return equity, held, price, "testnet", notes
        except Exception as exc:  # no keys / not wired -> simulate for a useful dry-run
            equity = float((self.config.get("backtest", {}) or {}).get("starting_cash", 10_000))
            price = close_price
            held = (self.live_cfg.size_frac * equity / price) if last_target > 0 else 0.0
            notes.append(f"account unavailable ({type(exc).__name__}: {exc}); simulated equity/held")
            return equity, held, price, "simulated(no keys)", notes

    # -- 3. what order (if any) moves us to the target? --
    def reconcile(self, target: float, price: float, equity: float, held: float,
                  notes: list[str]) -> dict[str, Any] | None:
        target_eff = target
        if self.market == "crypto" and target < 0:
            target_eff = 0.0
            notes.append("spot testnet can't short -> target -1 mapped to FLAT")

        target_units = target_eff * self.live_cfg.size_frac * equity / price
        delta = target_units - held
        notional = abs(delta) * price
        full_exit = target_eff == 0.0 and held > 0

        if notional < self.live_cfg.min_order_usdt and not full_exit:
            return None  # dust / below exchange min notional

        side = "buy" if delta > 0 else "sell"
        qty = held if full_exit else abs(delta)
        if self.broker.connected:
            qty = self.broker.round_qty(self.symbol, qty)
        else:
            qty = round(qty, 6)
        if qty <= 0:
            return None
        return {"side": side, "qty": qty, "notional": abs(qty) * price}

    # -- orchestrate one step --
    def step(self, armed: bool = False, confirm: str | None = None) -> Decision:
        st = live_state.load_state(self.agent_dir)
        target, bar_ts, close_price = self.decide()
        equity, held, price, mode, notes = self._account(close_price, float(st.get("last_target", 0.0)))

        dec = Decision(agent=self.agent, bar_ts=str(bar_ts), target=target, price=price,
                       equity=equity, held_units=held, account_mode=mode, armed=armed, notes=notes)

        # idempotency: an armed run never re-acts on a bar it already acted on
        if armed and st.get("last_bar_acted") is not None and str(bar_ts) <= str(st["last_bar_acted"]):
            dec.notes.append("already acted on this bar; skipping")
            return dec

        order = self.reconcile(target, price, equity, held, dec.notes)
        dec.order = order
        if order is None:
            if armed:
                st["last_bar_acted"] = str(bar_ts)
                st["last_target"] = target
                live_state.save_state(self.agent_dir, st)
            return dec

        # pre-trade GUARD: warn if this entry repeats a known mistake (learning agent).
        # Non-blocking by default; set live.block_on_mistake: true in config.yaml to skip such trades.
        if target != 0:
            try:
                warns = check_trade(int(target), latest_context(self._last_closed),
                                    MistakeMemory(self.agent_dir))
                for w in warns:
                    dec.notes.append("GUARD " + w["message"])
                if warns and (self.config.get("live", {}) or {}).get("block_on_mistake"):
                    dec.notes.append("BLOCKED by guard (block_on_mistake=true); not trading this setup")
                    return dec
            except Exception:
                pass

        # bounds (Constitution R-B.9)
        if order["notional"] > self.live_cfg.max_order_usdt:
            dec.notes.append(f"REFUSED: order {order['notional']:.2f} > max_order_usdt "
                             f"{self.live_cfg.max_order_usdt}")
            return dec
        if live_state.trades_today(st) >= self.live_cfg.max_trades_per_day:
            dec.notes.append(f"REFUSED: max_trades_per_day ({self.live_cfg.max_trades_per_day}) reached")
            return dec

        if not armed:
            dec.notes.append("dry-run: not sent (use --arm --confirm to transmit to testnet)")
            return dec

        # armed -> transmit to testnet
        resp = self.broker.place_market(self.symbol, order["side"], order["qty"], confirm)
        dec.placed = True
        dec.notes.append(f"testnet order id={resp.get('id', '?')} status={resp.get('status', '?')}")
        st["last_bar_acted"] = str(bar_ts)
        st["last_target"] = target
        live_state.record_trade(st, dec.summary())
        live_state.save_state(self.agent_dir, st)
        return dec
