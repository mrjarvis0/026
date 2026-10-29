"""Paper-trade an agent's latest signal on a TESTNET / PRACTICE account.

DRY-RUN BY DEFAULT: computes the latest target position, prints the *intended*
order, and sends nothing. Transmitting requires BOTH --send and the explicit
human-confirm token (Constitution R-B.4). Even then it targets testnet/practice
only — never real money.

Usage (safe, default):
    python scripts/papertrade.py '$001-dennis'

Usage (actually send to testnet — deliberate, human act):
    python scripts/papertrade.py '$001-dennis' --send --confirm I-CONFIRM-PAPER-ORDER
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _common import fetch_for, load_agent, primary_symbol  # noqa: E402
from core.paper import HUMAN_CONFIRM_PHRASE, OrderRefused, PaperOrder  # noqa: E402

BROKERS = {
    "crypto": "core.paper.binance_testnet",
    "forex": "core.paper.oanda_practice",
    "stocks": "core.paper.alpaca_paper",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Paper-trade an agent (dry-run by default).")
    ap.add_argument("agent", help="agent id, e.g. '$001-dennis'")
    ap.add_argument("--send", action="store_true", help="actually transmit to testnet/practice")
    ap.add_argument("--confirm", default=None, help=f"must equal '{HUMAN_CONFIRM_PHRASE}' to send")
    ap.add_argument("--notional", type=float, default=None, help="override notional to size the order")
    args = ap.parse_args()

    agent_dir, config, strategy = load_agent(args.agent)
    market = config["market"]
    symbol = primary_symbol(config)
    _, timeframe, data = fetch_for(config)

    signals = strategy.generate_signals(data)
    target = float(signals["position"].iloc[-1])
    last_close = float(data["Close"].iloc[-1])
    notional = args.notional if args.notional is not None else float(
        (config.get("backtest", {}) or {}).get("starting_cash", 10_000)
    )
    qty = round(notional / last_close, 6) if last_close > 0 else 0.0

    print(f"Agent: {agent_dir.name}  market={market}  symbol={symbol}  timeframe={timeframe}")
    print(f"Latest bar: {data.index[-1]}  close={last_close}")
    print(f"Target position: {target:+.0f}  (notional~{notional}, qty~{qty})")

    if target == 0:
        print("\nIntended action: FLAT — close any open position (no new entry).")
        order = None
    else:
        side = "buy" if target > 0 else "sell"
        order = PaperOrder(market=market, symbol=symbol, side=side, qty=qty, note="latest signal")
        print(f"\nIntended order: {order.describe()}")

    if not args.send:
        print("\n[DRY-RUN] Nothing sent. To transmit to the testnet/practice account, re-run with:")
        print(f"    --send --confirm {HUMAN_CONFIRM_PHRASE}")
        return 0

    if order is None:
        print("\nNo order to send (target is flat).")
        return 0

    import importlib
    broker = importlib.import_module(BROKERS[market])
    try:
        client = broker.connect()
        resp = broker.submit_order(client, order, confirm_token=args.confirm)
        print(f"\nSENT to {market} testnet/practice. Response: {resp}")
    except OrderRefused as exc:
        print(f"\nREFUSED: {exc}", file=sys.stderr)
        return 2
    except (RuntimeError, ImportError) as exc:
        print(f"\nCannot send (setup needed): {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
