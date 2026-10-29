from collections import defaultdict
from datetime import datetime


def _known_at(filing_dates):
    """The date the LAST piece of evidence became public (max filing date). Windows are built
    on transaction_date, but a trade is only public at filing_date (up to ~45 days later), so
    a consumer must not act on a finding before this. None if any filing date is missing:
    "cannot be determined", not a guess."""
    if not filing_dates or any(not d for d in filing_dates):
        return None
    return max(filing_dates)


def detect_congress_clusters(trades, window_days=7, min_trades=2):
    """
    Detects if multiple politicians are trading the same ticker in the same direction
    within a short time window. Uses a sliding window to find dense clusters.
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

            # Filter out missing dates and parse them
            valid_trades = []
            for t in type_trades:
                try:
                    dt = datetime.strptime(t["transaction_date"], "%Y-%m-%d")
                    valid_trades.append((dt, t))
                except (ValueError, TypeError):
                    continue

            if len(valid_trades) < min_trades:
                continue

            # Sort by date
            valid_trades.sort(key=lambda x: x[0])

            # Sliding window to find clusters
            n = len(valid_trades)
            for i in range(n):
                window_start = valid_trades[i][0]
                cluster_candidates = [valid_trades[i][1]]

                for j in range(i + 1, n):
                    window_end = valid_trades[j][0]
                    if (window_end - window_start).days <= window_days:
                        cluster_candidates.append(valid_trades[j][1])
                    else:
                        break

                if len(cluster_candidates) >= min_trades:
                    politicians = set(c["politician"] for c in cluster_candidates)
                    if len(politicians) >= min_trades:
                        # Avoid duplicate subset clusters
                        cluster_id = f"{ticker}-{t_type}-{valid_trades[i][0].strftime('%Y-%m-%d')}"
                        # check if already added a superset
                        already_added = False
                        for c in clusters:
                            if c["ticker"] == ticker and c["transaction_type"] == t_type:
                                existing_ids = set(c["evidence_ids"])
                                cand_ids = set(c_cand["id"] for c_cand in cluster_candidates)
                                if cand_ids.issubset(existing_ids):
                                    already_added = True
                                    break

                        if not already_added:
                            clusters.append({
                                "detector_id": "DET-PUBREC-CLUSTER-01",
                                "ticker": ticker,
                                "transaction_type": t_type,
                                "politicians": list(politicians),
                                "trade_count": len(cluster_candidates),
                                "window_start": valid_trades[i][1]["transaction_date"],
                                "window_end": cluster_candidates[-1]["transaction_date"],
                                "known_at": _known_at([c.get("filing_date") for c in cluster_candidates]),
                                "evidence_ids": [c["id"] for c in cluster_candidates]
                            })

    return clusters

def detect_congress_insider_correlation(congress_trades, insider_trades, window_days=7):
    """
    Detects if Congress trades and Insider trades on the same ticker and same direction
    occur within a short time window (smart money convergence).
    """
    correlations = []

    # Group by ticker
    c_by_ticker = defaultdict(list)
    for t in congress_trades:
        c_by_ticker[t["ticker"]].append(t)

    i_by_ticker = defaultdict(list)
    for t in insider_trades:
        i_by_ticker[t["ticker"]].append(t)

    for ticker in set(c_by_ticker.keys()).intersection(i_by_ticker.keys()):
        for c_trade in c_by_ticker[ticker]:
            for i_trade in i_by_ticker[ticker]:
                # Check if same direction (Purchase == Purchase, Sale == Sale)
                if c_trade["transaction_type"] == i_trade["transaction_type"]:
                    try:
                        c_date = datetime.strptime(c_trade["transaction_date"], "%Y-%m-%d")
                        i_date = datetime.strptime(i_trade["transaction_date"], "%Y-%m-%d")

                        if abs((c_date - i_date).days) <= window_days:
                            correlations.append({
                                "detector_id": "DET-PUBREC-CORRELATION-01",
                                "ticker": ticker,
                                "transaction_type": c_trade["transaction_type"],
                                "congress_politician": c_trade["politician"],
                                "insider_name": i_trade["insider_name"],
                                "congress_trade_date": c_trade["transaction_date"],
                                "insider_trade_date": i_trade["transaction_date"],
                                "filing_dates": [c_trade.get("filing_date"), i_trade.get("filing_date")],
                                "evidence_ids": [c_trade["id"], i_trade["id"]]
                            })
                    except (ValueError, TypeError):
                        pass

    # Group correlations by ticker and transaction type and date window
    # In a real scenario, this would create a single cluster of correlation rather than pairwise.
    # We will combine them by insider trade for the same ticker + direction
    combined = defaultdict(list)
    for corr in correlations:
        key = (corr["ticker"], corr["transaction_type"], corr["insider_name"], corr["insider_trade_date"])
        combined[key].append(corr)

    unique_correlations = []
    for key, corrs in combined.items():
        congress_politicians = set()
        evidence_ids = set()
        filing_dates = []
        for c in corrs:
            congress_politicians.add(c["congress_politician"])
            filing_dates.extend(c["filing_dates"])
            for e_id in c["evidence_ids"]:
                evidence_ids.add(e_id)

        unique_correlations.append({
            "detector_id": "DET-PUBREC-CORRELATION-01",
            "ticker": key[0],
            "transaction_type": key[1],
            "insider_name": key[2],
            "insider_trade_date": key[3],
            "congress_politicians": list(congress_politicians),
            "known_at": _known_at(filing_dates),
            "evidence_ids": list(evidence_ids)
        })

    return unique_correlations
