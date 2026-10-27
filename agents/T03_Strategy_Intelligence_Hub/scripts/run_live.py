"""Run an agent as a (paper) trader on Binance Testnet.

DRY-RUN BY DEFAULT: shows the target position + the exact delta order it would place,
and sends nothing. Transmit only with BOTH --arm and the human-confirm token. Testnet
only; real money is out of scope (Constitution R-B.4).

Examples:
    python scripts/run_live.py '$005-seykota'                         # dry-run, once
    python scripts/run_live.py '$005-seykota' --arm --confirm I-CONFIRM-PAPER-ORDER
    python scripts/run_live.py '$005-seykota' --loop                  # persistent (daily bar)
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HUB_ROOT))

from _common import load_agent  # noqa: E402  (also reconfigures stdout to UTF-8)
from core.config import LOGS_DIR  # noqa: E402
from core.live import LiveTrader  # noqa: E402
from core.paper import HUMAN_CONFIRM_TOKEN  # noqa: E402


def _log(agent: str, line: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    safe = agent.replace("$", "").replace("/", "-")
    print(line)
    try:
        with (LOGS_DIR / f"live_{safe}.log").open("a", encoding="utf-8") as fh:
            fh.write(f"{stamp}  {line}\n")
    except OSError:
        pass


def _record_fill(agent_dir: Path, dec) -> None:
    path = agent_dir / "results" / "live_trades.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["utc_time", "bar_ts", "side", "qty", "notional_usdt", "price", "account_mode"])
        w.writerow([datetime.now(timezone.utc).isoformat(), dec.bar_ts, dec.order["side"],
                    dec.order["qty"], round(dec.order["notional"], 2), dec.price, dec.account_mode])


def _seconds_until(hour: int = 0, minute: int = 5) -> float:
    """Seconds until the next daily HH:MM UTC (for aligning to the daily bar close)."""
    now = datetime.now(timezone.utc)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return max(60.0, (target - now).total_seconds())


def run_once(agent_dir, config, strategy, armed: bool, confirm: str | None) -> None:
    trader = LiveTrader(agent_dir, config, strategy)
    dec = trader.step(armed=armed, confirm=confirm)
    _log(agent_dir.name, dec.summary())
    for n in dec.notes:
        _log(agent_dir.name, f"    - {n}")
    if dec.placed and dec.order is not None:
        _record_fill(agent_dir, dec)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run an agent as a (paper) trader on testnet.")
    ap.add_argument("agent", help="agent id, e.g. '$005-seykota'")
    ap.add_argument("--arm", action="store_true", help="actually transmit orders to the testnet")
    ap.add_argument("--confirm", default=None, help=f"must equal '{HUMAN_CONFIRM_TOKEN}' to send")
    ap.add_argument("--loop", action="store_true", help="run continuously, once per daily bar close")
    ap.add_argument("--interval", type=float, default=None,
                    help="loop sleep seconds (overrides daily alignment)")
    args = ap.parse_args()

    if args.arm and args.confirm != HUMAN_CONFIRM_TOKEN:
        print(f"--arm requires --confirm {HUMAN_CONFIRM_TOKEN} (nothing sent).", file=sys.stderr)
        return 2

    agent_dir, config, strategy = load_agent(args.agent)
    mode = "ARMED (testnet)" if args.arm else "DRY-RUN"
    _log(agent_dir.name, f"=== run_live {agent_dir.name} [{mode}] ===")

    if not args.loop:
        run_once(agent_dir, config, strategy, args.arm, args.confirm)
        return 0

    _log(agent_dir.name, "loop mode: Ctrl+C to stop")
    try:
        while True:
            run_once(agent_dir, config, strategy, args.arm, args.confirm)
            wait = args.interval if args.interval is not None else _seconds_until(0, 5)
            _log(agent_dir.name, f"sleeping {wait:.0f}s until next check")
            time.sleep(wait)
    except KeyboardInterrupt:
        _log(agent_dir.name, "stopped by user")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
