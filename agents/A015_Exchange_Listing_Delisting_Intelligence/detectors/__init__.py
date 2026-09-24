"""A015 detectors + a convenience pipeline that runs all four over one diff."""
from __future__ import annotations

from .delisting import detect_delisting
from .new_listing import detect_new_listing
from .pair_change import detect_pair_change
from .status_change import detect_status_change

__all__ = [
    "detect_new_listing", "detect_delisting", "detect_status_change",
    "detect_pair_change", "run_all",
]


def run_all(changes: list[dict], old_snapshot: dict | None = None,
            new_snapshot: dict | None = None) -> dict[str, list[dict]]:
    """Run every detector over one diff. Passing both snapshots keeps the four
    detectors mutually exclusive (a pair add/remove is not also a listing/delisting)."""
    return {
        "NEW_LISTING": detect_new_listing(changes, old_snapshot),
        "DELISTING": detect_delisting(changes, new_snapshot=new_snapshot),
        "STATUS_CHANGE": detect_status_change(changes),
        "PAIR_CHANGE": detect_pair_change(changes, old_snapshot, new_snapshot),
    }
