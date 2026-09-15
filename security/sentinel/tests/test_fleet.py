from pathlib import Path

from security.sentinel.fleet import parse_fleet_table, load_fleet
from security.sentinel.policy import load_policy

FLEET_MD = """
| ID    | Agent                     | Status    | Domain          |
| ----- | ------------------------- | --------- | --------------- |
| `A001` | Blockchain Intelligence   | substantial | On-chain        |
| `A002` | News Intelligence         | substantial | Rumor           |
| `A03` | *(reserved)* DeFi Flow    | planned   | Liquidity       |
"""


def test_parse_fleet_table_skips_reserved():
    table = parse_fleet_table(FLEET_MD)
    assert table["A001"]["name"] == "Blockchain Intelligence"
    assert table["A001"]["status"] == "substantial"
    assert "A03" not in table  # reserved row skipped


def test_load_fleet_reads_real_agents():
    root = Path(__file__).resolve().parents[3]  # F:\026
    records = load_fleet(root, load_policy())
    ids = {r.id for r in records}
    assert {"A001", "A002"} <= ids
    a001 = next(r for r in records if r.id == "A001")
    assert a001.manifest["invariants"]["execution_enabled"] is False
    assert a001.dir.name == "A001_Blockchain_Intelligence"
