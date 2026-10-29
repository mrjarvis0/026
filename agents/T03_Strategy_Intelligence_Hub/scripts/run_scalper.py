"""Run the futures scalper on a strategy agent (default: $009-scalper).

DRY-RUN BY DEFAULT: shows the fused signal + intended order, sends nothing.
Transmit only with BOTH --arm and the human-confirm token.
Testnet only; real money is not built here (Constitution R-B.4).

Examples:
    python scripts/run_scalper.py '$009-scalper'
    python scripts/run_scalper.py '$009-scalper' --arm --confirm I-CONFIRM-PAPER-ORDER
    python scripts/run_scalper.py '$009-scalper' --loop --interval 300
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HUB_ROOT))

from _common import HUB_ROOT  # noqa: E402,F401  (also configures UTF-8 stdout)
from core.paper import HUMAN_CONFIRM_PHRASE  # noqa: E402
from core.registry import load_agent_config, resolve_agent  # noqa: E402
from core.futures.scalper import FuturesScalper  # noqa: E402


def _log(agent: str, line: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    print(f"[{stamp}] {line}")
    try:
        safe = agent.replace("$", "").replace("/", "-")
        log_path = HUB_ROOT / "logs" / f"scalper_{safe}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"{stamp}  {line}\n")
    except OSError:
        pass


def run_once(agent_name: str, armed: bool, confirm: str | None) -> int:
    agent_dir = resolve_agent(agent_name)
    config = load_agent_config(agent_dir)

    scalper = FuturesScalper(config, agent_dir)
    dec = scalper.step(armed=armed, confirm=confirm, use_cache=True)

    _log(agent_name, dec.summary())
    for n in dec.notes:
        _log(agent_name, f"    {n}")

    # Print fused signal detail
    f = dec.fused
    if f.stand_aside:
        _log(agent_name, f"    ⚪ STAND ASIDE — {f.reason}")
    else:
        dir_sym = "🟢 LONG" if f.direction > 0 else "🔴 SHORT"
        _log(agent_name, (
            f"    {dir_sym}  conf={f.confidence:.0%}  scanner={f.scanner_direction:+d}({f.scanner_strength:.0%})"
            f"  mtf={f.mtf_alignment:+d}({f.mtf_confidence:.0%})"
            f"  p_up={f.p_up:.3f}  edge={f.p_up_edge:.3f}"
        ))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the futures scalper for an agent.")
    ap.add_argument("agent", nargs="?", default="$009-scalper",
                    help="agent id (default: '$009-scalper')")
    ap.add_argument("--arm", action="store_true", help="transmit orders to the Futures Testnet")
    ap.add_argument("--confirm", default=None,
                    help=f"must equal '{HUMAN_CONFIRM_PHRASE}' to send")
    ap.add_argument("--loop", action="store_true", help="run continuously on a timer")
    ap.add_argument("--interval", type=float, default=300.0,
                    help="loop interval in seconds (default 300 = 5 min, matches 5m bars)")
    ap.add_argument("--no-cache", action="store_true",
                    help="bypass data cache, always re-download")
    args = ap.parse_args()

    if args.arm and args.confirm != HUMAN_CONFIRM_PHRASE:
        print(f"ERROR: --arm requires --confirm '{HUMAN_CONFIRM_PHRASE}'")
        return 1

    if not args.loop:
        return run_once(args.agent, args.arm, args.confirm)

    print(f"scalper loop: {args.agent}  interval={args.interval:.0f}s  armed={args.arm}  Ctrl+C to stop")
    try:
        while True:
            run_once(args.agent, args.arm, args.confirm)
            print(f"    next run in {args.interval:.0f}s")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
