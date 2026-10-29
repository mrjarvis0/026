"""Phase 0 pipeline hardening — each test names the defect it guards.

Run: pytest agents/A007_Public_Record_Intelligence/tests -q
"""
import pytest

from agents.A007_Public_Record_Intelligence.ingestion.mcp_client import (
    fetch_congress_trades,
    fetch_insider_trades,
)
from agents.A007_Public_Record_Intelligence.intelligence.cluster import (
    detect_congress_clusters,
    detect_congress_insider_correlation,
)
from agents.A007_Public_Record_Intelligence.normalization.cleaner import (
    normalize_insider_trade,
    normalize_trade,
)
from agents.A007_Public_Record_Intelligence.store import db
from agents.A007_Public_Record_Intelligence.store.db import (
    get_insider_trades_by_ticker,
    get_trades_by_ticker,
    init_db,
    store_insider_trade,
    store_trade,
)

RAW = {"id": "fetch-1", "politician": "Nancy Pelosi", "ticker": "nvda",
       "transaction_date": "2026-09-01", "filing_date": "2026-09-10",
       "transaction_type": "Purchase", "amount": "$1,000,001 - $5,000,000", "source": "S119"}


# ---- idempotency: the id is the trade, not the fetch ---------------------------------

def test_same_trade_gets_same_id_whatever_the_fetch_id():
    # regression: ids were uuid4 per fetch, so INSERT OR IGNORE never deduplicated a rerun
    assert normalize_trade(RAW)["id"] == normalize_trade({**RAW, "id": "fetch-2"})["id"]


def test_a_different_trade_gets_a_different_id():
    assert normalize_trade(RAW)["id"] != normalize_trade({**RAW, "amount": "$15,001 - $50,000"})["id"]
    assert normalize_trade(RAW)["id"] != normalize_trade({**RAW, "politician": "Ro Khanna"})["id"]


def test_insider_trade_id_is_the_trade_not_the_fetch():
    raw = {"id": "a", "insider_name": "Huang Jen Hsun", "ticker": "NVDA", "transaction_date": "2026-09-02",
           "filing_date": "2026-09-03", "transaction_type": "Sale", "shares": 10000, "price": 450.5}
    assert normalize_insider_trade(raw)["id"] == normalize_insider_trade({**raw, "id": "b"})["id"]


def test_rerunning_the_pipeline_does_not_duplicate_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "a007.db"))
    conn = init_db()
    for _ in range(2):                                   # two scheduled runs over the same filings
        for raw in fetch_congress_trades(mock=True):
            store_trade(conn, normalize_trade(raw))
        for raw in fetch_insider_trades(mock=True):
            store_insider_trade(conn, normalize_insider_trade(raw))
    assert len(get_trades_by_ticker(conn, "NVDA")) == 2
    assert len(get_insider_trades_by_ticker(conn, "NVDA")) == 2
    conn.close()


# ---- known_at: when the evidence became public ----------------------------------------

def _congress():
    return [normalize_trade(r) for r in fetch_congress_trades(mock=True)]


def _insiders():
    return [normalize_insider_trade(r) for r in fetch_insider_trades(mock=True)]


def test_cluster_reports_when_it_became_public():
    # regression: windows use transaction_date but congressional trades are only public at
    # filing_date (up to 45 days later); a consumer must not act on a cluster before known_at
    [cluster] = detect_congress_clusters(_congress(), window_days=7, min_trades=2)
    assert cluster["known_at"] == "2026-09-11"           # Pelosi filed 09-10, Tuberville 09-11


def test_cluster_known_at_is_unknown_when_a_filing_date_is_missing():
    trades = [{k: v for k, v in t.items() if k != "filing_date"} for t in _congress()]
    [cluster] = detect_congress_clusters(trades, window_days=7, min_trades=2)
    assert cluster["known_at"] is None                    # "cannot be determined", not a guess


def test_correlation_known_at_is_the_latest_filing_of_all_its_evidence():
    [corr] = detect_congress_insider_correlation(_congress(), _insiders(), window_days=7)
    assert corr["known_at"] == "2026-09-11"


# ---- an unimplemented live fetch must not look like "no trades" ------------------------

@pytest.mark.parametrize("fetch", [fetch_congress_trades, fetch_insider_trades])
def test_live_fetch_is_not_pretending_there_are_no_trades(fetch):
    # regression: mock=False returned [] — indistinguishable from "nothing was traded",
    # which breaks coverage_required_for_absence
    with pytest.raises(NotImplementedError):
        fetch(mock=False)
