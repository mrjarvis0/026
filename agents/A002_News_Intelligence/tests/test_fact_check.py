import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from agents.A002_News_Intelligence.intelligence.verification import FactCheckClient, get_fact_check_client

def test_fact_check_client():
    client = FactCheckClient(api_key="test_key")
    results = client.check_claim("Bitcoin is dead")
    print(results)

if __name__ == "__main__":
    test_fact_check_client()
