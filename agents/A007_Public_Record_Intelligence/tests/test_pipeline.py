import os
import sqlite3
import unittest
import tempfile
import sys
from pathlib import Path

# Add project root to sys.path to allow imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from agents.A007_Public_Record_Intelligence.store.db import init_db, store_trade, get_trades_by_ticker, store_insider_trade, get_insider_trades_by_ticker
from agents.A007_Public_Record_Intelligence.ingestion.mcp_client import fetch_congress_trades, fetch_insider_trades
from agents.A007_Public_Record_Intelligence.normalization.cleaner import normalize_trade, normalize_insider_trade
from agents.A007_Public_Record_Intelligence.intelligence.cluster import detect_congress_clusters, detect_congress_insider_correlation

class TestA007Pipeline(unittest.TestCase):
    def setUp(self):
        # Override DB path for testing
        self.test_dir = tempfile.TemporaryDirectory()
        import agents.A007_Public_Record_Intelligence.store.db as db
        db.DB_PATH = os.path.join(self.test_dir.name, "test_a007.db")
        self.conn = init_db()

    def tearDown(self):
        self.conn.close()
        self.test_dir.cleanup()

    def test_end_to_end_pipeline(self):
        # 1. Ingestion
        raw_trades = fetch_congress_trades(mock=True)
        self.assertEqual(len(raw_trades), 3)

        # 2. Normalization
        normalized_trades = [normalize_trade(rt) for rt in raw_trades]

        # Verify normalization
        nvda_trades = [t for t in normalized_trades if t["ticker"] == "NVDA"]
        self.assertEqual(len(nvda_trades), 2)
        self.assertEqual(nvda_trades[0]["amount_min"], 1000001)
        self.assertEqual(nvda_trades[0]["amount_max"], 5000000)

        # 3. Store
        for nt in normalized_trades:
            store_trade(self.conn, nt)

        db_trades = get_trades_by_ticker(self.conn, "NVDA")
        self.assertEqual(len(db_trades), 2)

        # 4. Intelligence (Clustering Congress Trades)
        db_trades_dicts = []
        for row in db_trades:
            db_trades_dicts.append({
                "id": row[0],
                "politician": row[1],
                "ticker": row[2],
                "transaction_date": row[3],
                "transaction_type": row[5]
            })

        clusters = detect_congress_clusters(db_trades_dicts, window_days=7, min_trades=2)
        self.assertEqual(len(clusters), 1)

        cluster = clusters[0]
        self.assertEqual(cluster["ticker"], "NVDA")
        self.assertEqual(cluster["detector_id"], "DET-PUBREC-CLUSTER-01")
        self.assertEqual(cluster["trade_count"], 2)
        self.assertIn("Nancy Pelosi", cluster["politicians"])
        self.assertIn("Tommy Tuberville", cluster["politicians"])

    def test_insider_pipeline_and_correlation(self):
        # 1. Ingestion
        raw_congress = fetch_congress_trades(mock=True)
        raw_insider = fetch_insider_trades(mock=True)

        # 2. Normalization & Store
        for rt in raw_congress:
            nt = normalize_trade(rt)
            store_trade(self.conn, nt)

        for rt in raw_insider:
            nit = normalize_insider_trade(rt)
            store_insider_trade(self.conn, nit)

        # Verify store
        insider_db = get_insider_trades_by_ticker(self.conn, "NVDA")
        self.assertEqual(len(insider_db), 2)

        congress_db = get_trades_by_ticker(self.conn, "NVDA")

        c_dicts = [{"id": r[0], "politician": r[1], "ticker": r[2], "transaction_date": r[3], "transaction_type": r[5]} for r in congress_db]
        i_dicts = [{"id": r[0], "insider_name": r[1], "ticker": r[3], "transaction_date": r[4], "transaction_type": r[6]} for r in insider_db]

        # 3. Cross-Domain Intelligence (Correlation)
        correlations = detect_congress_insider_correlation(c_dicts, i_dicts, window_days=7)

        self.assertEqual(len(correlations), 1)
        corr = correlations[0]
        self.assertEqual(corr["detector_id"], "DET-PUBREC-CORRELATION-01")
        self.assertEqual(corr["ticker"], "NVDA")
        self.assertEqual(corr["transaction_type"], "Purchase")
        # Mark Stevens bought on 2026-09-01, Pelosi bought on 2026-09-01, Tuberville bought on 2026-09-02
        self.assertEqual(corr["insider_name"], "Stevens Mark A")
        self.assertIn("Nancy Pelosi", corr["congress_politicians"])
        self.assertIn("Tommy Tuberville", corr["congress_politicians"])
        self.assertEqual(len(corr["evidence_ids"]), 3)

if __name__ == '__main__':
    unittest.main()
