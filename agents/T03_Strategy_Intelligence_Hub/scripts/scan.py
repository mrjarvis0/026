"""Live multi-strategy scanner — see every agent's signal on any token at once.

Examples:
    python scripts/scan.py --symbol BTC/USDT --timeframe 1h
    python scripts/scan.py --symbol ETH/USDT --timeframe 15m --loop
    python scripts/scan.py --symbol SOL/USDT --agents $005,$007
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _common import HUB_ROOT  # noqa: E402,F401  (reconfigures stdout to UTF-8)
from core.scan import consensus, scan  # noqa: E402

_ICON = {"LONG": "🟢 LONG ", "SHORT": "🔴 SHORT", "flat": "⚪ flat ", "ERR": "⚠️  ERR "}


def render(symbol: str, timeframe: str, closed, signals) -> None:
    last = closed.iloc[-1]
    ts = closed.index[-1]
    o, h, l, c = float(last["Open"]), float(last["High"]), float(last["Low"]), float(last["Close"])
    candle = "green ▲" if c >= o else "red ▼"
    rng = (h - l) / o * 100 if o else 0
    print(f"\n=== {symbol}  {timeframe}  |  last closed bar {ts} ===")
    print(f"    O {o:.4g}  H {h:.4g}  L {l:.4g}  C {c:.4g}   ({candle}, range {rng:.2f}%)")
    print("    " + "-" * 60)
    for s in signals:
        tag = _ICON.get(s.signal, s.signal)
        extra = f"  ({s.error})" if s.error else ""
        print(f"    {tag}  {s.agent:<16}  {s.strategy}{extra}")
    con = consensus(signals)
    print("    " + "-" * 60)
    print(f"    CONSENSUS: 🟢{con['long']}  🔴{con['short']}  ⚪{con['flat']}"
          + (f"  ⚠️{con['err']}" if con['err'] else "")
          + f"   →  net bias: {con['bias']} ({con['net']:+d})")
    print(f"    (which strategies fire on this candle pattern ↑)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Scan all agents' signals on one token.")
    ap.add_argument("--symbol", default="BTC/USDT")
    ap.add_argument("--market", default="crypto", choices=["crypto", "forex", "stocks"])
    ap.add_argument("--timeframe", default="1h")
    ap.add_argument("--start", default="2023-01-01")
    ap.add_argument("--agents", default=None, help="comma list, e.g. $005,$007 (default: all)")
    ap.add_argument("--loop", action="store_true", help="rescan continuously")
    ap.add_argument("--interval", type=float, default=60.0, help="loop seconds (default 60)")
    args = ap.parse_args()

    agent_filter = [a for a in args.agents.split(",")] if args.agents else None

    def once():
        closed, signals = scan(args.symbol, args.market, args.timeframe, args.start, agent_filter)
        render(args.symbol, args.timeframe, closed, signals)

    if not args.loop:
        once()
        return 0
    print(f"scanning {args.symbol} every {args.interval:.0f}s — Ctrl+C to stop")
    try:
        while True:
            once()
            print(f"\n    [{datetime.now(timezone.utc):%H:%M:%SZ}] next scan in {args.interval:.0f}s")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
