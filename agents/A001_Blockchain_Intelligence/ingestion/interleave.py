"""Poll one block, drain it to the store, repeat.

The poller advances its checkpoint the moment a record is *queued*, not when it is stored. Draining only
after a whole run therefore lets the checkpoint run up to ``blocks`` ahead of the store: a process killed
in between (the live supervisor is, at PC shutdown) leaves checkpointed blocks that were never written, a
permanent hole. Draining after every block bounds that to the single block in flight.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any


def poll_and_drain(poller: Any, consume: Callable[[list], Any], blocks: int) -> tuple[list, list]:
    """Run ``poller`` one step at a time, calling ``consume(results_of_that_step)`` after each.

    Stops after ``blocks`` steps or when the poller reports there is nothing more to do (same stop rule
    as ``BlockPoller.run``). Returns ``(all_results, consume_return_values)``.
    """
    results: list = []
    reports: list = []
    while len(results) < blocks:
        chunk = poller.run(max_steps=1)
        if not chunk:
            break
        results.extend(chunk)
        reports.append(consume(chunk))
        if not chunk[-1].should_retry:
            break
    return results, reports
