"""Every A015 test runs against throwaway runtime paths, never the real memory/ directory."""
import pytest

from agents.A015_Exchange_Listing_Delisting_Intelligence.core import event_log, poll_status
from agents.A015_Exchange_Listing_Delisting_Intelligence.tools import ccxt_market_poller as poller


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    # Tests that need a specific layout re-patch these (later patches win); the rest are safe by default.
    monkeypatch.setattr(poll_status, "POLL_STATUS_FILE", tmp_path / "_iso" / "poll_status.json")
    monkeypatch.setattr(event_log, "EVENT_LOG_DIR", tmp_path / "_iso" / "event_log")
    monkeypatch.setattr(poller, "_SNAPSHOT_DIR", tmp_path / "_iso" / "symbol_snapshots")
