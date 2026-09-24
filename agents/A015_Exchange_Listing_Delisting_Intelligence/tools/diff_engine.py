"""
Generic snapshot-diff utility for A015 agent.
Computes differences between two snapshots of exchange market data.
"""

import json
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

@dataclass
class MarketChange:
    exchange: str
    symbol: str
    change_type: str  # 'added', 'removed', 'changed'
    old_value: Any = None
    new_value: Any = None
    detected_at: str = None

    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.now(timezone.utc).isoformat()

def load_snapshot(filepath: str) -> Dict[str, Dict]:
    """Load a snapshot from a JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_snapshot(snapshot: Dict[str, Dict], filepath: str) -> None:
    """Save a snapshot to a JSON file."""
    with open(filepath, 'w') as f:
        json.dump(snapshot, f, indent=2)

def diff_snapshots(old: Dict[str, Dict], new: Dict[str, Dict]) -> List[MarketChange]:
    """
    Compute differences between two snapshots.
    Each snapshot is a dict: {symbol: market_info_dict}
    """
    changes = []
    old_symbols = set(old.keys())
    new_symbols = set(new.keys())

    # Added symbols
    for symbol in new_symbols - old_symbols:
        changes.append(MarketChange(
            exchange="",  # Will be filled by caller
            symbol=symbol,
            change_type="added",
            new_value=new[symbol]
        ))

    # Removed symbols
    for symbol in old_symbols - new_symbols:
        changes.append(MarketChange(
            exchange="",
            symbol=symbol,
            change_type="removed",
            old_value=old[symbol]
        ))

    # Changed symbols (present in both)
    for symbol in old_symbols & new_symbols:
        if old[symbol] != new[symbol]:
            changes.append(MarketChange(
                exchange="",
                symbol=symbol,
                change_type="changed",
                old_value=old[symbol],
                new_value=new[symbol]
            ))

    return changes

def filter_symbol_changes(changes: List[MarketChange], 
                          include_added: bool = True,
                          include_removed: bool = True,
                          include_changed: bool = False) -> List[MarketChange]:
    """Filter changes by type."""
    filtered = []
    for change in changes:
        if change.change_type == "added" and not include_added:
            continue
        if change.change_type == "removed" and not include_removed:
            continue
        if change.change_type == "changed" and not include_changed:
            continue
        filtered.append(change)
    return filtered

if __name__ == "__main__":
    # Simple test
    old_snap = {"BTC/USDT": {"id": "BTC/USDT", "active": True},
                "ETH/USDT": {"id": "ETH/USDT", "active": True}}
    new_snap = {"BTC/USDT": {"id": "BTC/USDT", "active": True},
                "ETH/USDT": {"id": "ETH/USDT", "active": False},  # changed
                "ADA/USDT": {"id": "ADA/USDT", "active": True}}   # added
    diffs = diff_snapshots(old_snap, new_snap)
    for d in diffs:
        print(f"{d.change_type}: {d.symbol}")