from collections import defaultdict
from datetime import datetime

def detect_congress_clusters(trades, window_days=7, min_trades=2):
    """
    Detects if multiple politicians are trading the same ticker in the same direction
    within a short time window.
    """
    clusters = []

    # Group by ticker
    by_ticker = defaultdict(list)
    for t in trades:
        by_ticker[t["ticker"]].append(t)

    for ticker, ticker_trades in by_ticker.items():
        if len(ticker_trades) < min_trades:
            continue

        # Group by transaction type (Purchase, Sale)
        by_type = defaultdict(list)
        for t in ticker_trades:
            by_type[t["transaction_type"]].append(t)

        for t_type, type_trades in by_type.items():
            if len(type_trades) < min_trades:
                continue

            # Sort by date
            type_trades.sort(key=lambda x: x["transaction_date"])

            # Simple window check: max date - min date
            try:
                min_date = datetime.strptime(type_trades[0]["transaction_date"], "%Y-%m-%d")
                max_date = datetime.strptime(type_trades[-1]["transaction_date"], "%Y-%m-%d")

                if (max_date - min_date).days <= window_days:
                    # Verify they are from distinct politicians
                    politicians = set(t["politician"] for t in type_trades)
                    if len(politicians) >= min_trades:
                        clusters.append({
                            "detector_id": "DET-PUBREC-CLUSTER-01",
                            "ticker": ticker,
                            "transaction_type": t_type,
                            "politicians": list(politicians),
                            "trade_count": len(type_trades),
                            "window_start": type_trades[0]["transaction_date"],
                            "window_end": type_trades[-1]["transaction_date"],
                            "evidence_ids": [t["id"] for t in type_trades]
                        })
            except ValueError:
                pass # skip if date parsing fails

    return clusters
