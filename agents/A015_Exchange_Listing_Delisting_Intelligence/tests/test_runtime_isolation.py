"""Tests must never read or write A015's real runtime files (memory/).

Regression: an older poll test ran `cli.poll` before poll_status existed to be patched, so it wrote
its fake "binance: RuntimeError: down" into the real memory/poll_status.json, and the bus relay
then reported that fake outage as real source health.
"""
from pathlib import Path

from agents.A015_Exchange_Listing_Delisting_Intelligence import cli
from agents.A015_Exchange_Listing_Delisting_Intelligence.core import event_log, poll_status
from agents.A015_Exchange_Listing_Delisting_Intelligence.tools import ccxt_market_poller as poller

REAL_MEMORY = Path(cli.__file__).resolve().parent / "memory"


def test_runtime_paths_are_redirected_for_every_test():
    for path in (poll_status.POLL_STATUS_FILE, event_log.EVENT_LOG_DIR, poller._SNAPSHOT_DIR):
        assert REAL_MEMORY not in Path(path).resolve().parents and Path(path).resolve() != REAL_MEMORY
