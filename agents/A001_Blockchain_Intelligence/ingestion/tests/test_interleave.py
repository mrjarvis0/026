"""poll_and_drain: the checkpoint must never run ahead of the store by more than one block.

Regression (2026-10-28 audit): the poller advances its checkpoint when a record is QUEUED, but the queue was
only drained after the whole run, so a process killed mid-run (the supervisor was, at PC shutdown) left
checkpointed blocks that were never stored: a permanent hole.

Run: python -m pytest agents/A001_Blockchain_Intelligence/ingestion/tests/test_interleave.py -q
"""
import sys
from pathlib import Path

import pytest

A001_DIR = Path(__file__).resolve().parents[2]
if str(A001_DIR) not in sys.path:
    sys.path.insert(0, str(A001_DIR))

from ingestion.interleave import poll_and_drain  # noqa: E402


class Result:
    def __init__(self, should_retry=True):
        self.should_retry = should_retry


class FakePoller:
    def __init__(self, log, steps, fail_at=None):
        self.log, self.steps, self.fail_at, self.n = log, steps, fail_at, 0

    def run(self, max_steps):
        assert max_steps == 1                       # one block at a time
        self.n += 1
        if self.n == self.fail_at:
            raise RuntimeError("killed")
        self.log.append(f"poll{self.n}")
        return [Result(should_retry=self.n < self.steps)]


def test_each_block_is_drained_before_the_next_is_polled():
    log: list = []
    results, reports = poll_and_drain(FakePoller(log, steps=3), lambda c: log.append("drain") or "r", blocks=10)
    assert log == ["poll1", "drain", "poll2", "drain", "poll3", "drain"]
    assert len(results) == 3 and reports == ["r", "r", "r"]       # stopped when the poller said caught up


def test_a_kill_mid_run_leaves_every_earlier_block_stored():
    log: list = []
    with pytest.raises(RuntimeError):
        poll_and_drain(FakePoller(log, steps=10, fail_at=3), lambda c: log.append("drain"), blocks=10)
    assert log == ["poll1", "drain", "poll2", "drain"]            # blocks 1 and 2 were already drained


def test_stops_at_the_block_limit():
    log: list = []
    results, _ = poll_and_drain(FakePoller(log, steps=100), lambda c: None, blocks=4)
    assert len(results) == 4 and log == ["poll1", "poll2", "poll3", "poll4"]


def test_an_empty_poll_stops_the_loop():
    class Empty:
        def run(self, max_steps):
            return []

    results, reports = poll_and_drain(Empty(), lambda c: "r", blocks=5)
    assert results == [] and reports == []
