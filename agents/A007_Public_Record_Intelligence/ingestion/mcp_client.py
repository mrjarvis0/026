import urllib.request
import json
import uuid

# Mock ingestion client for LuxAlgo MCP trackers_congress_trades tool.
# In a real scenario, this would use MCP protocol.
# Here we simulate fetching from an open data source or mock data.

def fetch_congress_trades(mock=False):
    if mock:
        return [
            {
                "id": str(uuid.uuid4()),
                "politician": "Nancy Pelosi",
                "ticker": "NVDA",
                "transaction_date": "2026-09-01",
                "filing_date": "2026-09-10",
                "transaction_type": "Purchase",
                "amount": "$1,000,001 - $5,000,000",
                "source": "S119"
            },
            {
                "id": str(uuid.uuid4()),
                "politician": "Tommy Tuberville",
                "ticker": "NVDA",
                "transaction_date": "2026-09-02",
                "filing_date": "2026-09-11",
                "transaction_type": "Purchase",
                "amount": "$100,001 - $250,000",
                "source": "S119"
            },
            {
                "id": str(uuid.uuid4()),
                "politician": "Ro Khanna",
                "ticker": "AAPL",
                "transaction_date": "2026-09-05",
                "filing_date": "2026-09-12",
                "transaction_type": "Sale",
                "amount": "$15,001 - $50,000",
                "source": "S119"
            }
        ]
    # We could implement real fetch logic here if needed.
    return []

def fetch_insider_trades(mock=False):
    if mock:
        return [
            {
                "id": str(uuid.uuid4()),
                "insider_name": "Huang Jen Hsun",
                "insider_title": "CEO",
                "ticker": "NVDA",
                "transaction_date": "2026-09-02",
                "filing_date": "2026-09-03",
                "transaction_type": "Sale",
                "shares": 10000,
                "price": 450.50,
                "value": 4505000,
                "source": "S028"
            },
            {
                "id": str(uuid.uuid4()),
                "insider_name": "Stevens Mark A",
                "insider_title": "Director",
                "ticker": "NVDA",
                "transaction_date": "2026-09-01",
                "filing_date": "2026-09-03",
                "transaction_type": "Purchase",
                "shares": 5000,
                "price": 448.20,
                "value": 2241000,
                "source": "S028"
            }
        ]
    return []
