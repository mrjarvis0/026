"""The librarian: records A015's facts in the persistent brain (design spec section 11).

A *recorder*, not an actor: it may store events from detectors that are still ``implemented``
(``min_maturity="implemented"``) precisely because the maturity label is stored with the fact.
Idempotent by ``event_id`` — a redelivered event is recorded once.
"""
from __future__ import annotations

from collections.abc import Callable

from brain.store import Brain
from orchestrator.event_bus.store import ConsumeStats, EventStore

NAME = "librarian"
NAMESPACE = "markets"
TYPES = ["a015.*"]


def librarian_handler(brain: Brain) -> Callable[[dict], None]:
    def handle(event: dict) -> None:
        key = f"event:{event['event_id']}"
        if brain.history(NAMESPACE, key):          # already recorded: redelivery is a no-op
            return
        brain.write(NAMESPACE, key, {k: v for k, v in event.items() if k != "seq"}, by=NAME)

    return handle


BATCH = 200
MAX_ATTEMPTS = 20        # one attempt per 5-minute bus cycle: ~100 minutes of outage before an event is parked
MAX_BATCHES = 100        # up to 20,000 events per run; the rest is picked up next cycle


def run_once(store: EventStore, brain: Brain) -> ConsumeStats:
    """Drain what is pending (many batches, not one). Stops as soon as a batch makes no progress, so a
    failing handler (retry/backoff in the store) can never spin this loop."""
    handler = librarian_handler(brain)
    total = ConsumeStats()
    for _ in range(MAX_BATCHES):
        s = store.consume(NAME, handler, types=TYPES, min_maturity="implemented", batch=BATCH,
                          max_attempts=MAX_ATTEMPTS)
        total.delivered += s.delivered
        total.skipped_other_type += s.skipped_other_type
        total.skipped_low_maturity += s.skipped_low_maturity
        total.failed += s.failed
        total.parked += s.parked
        total.last_seq = s.last_seq or total.last_seq
        if s.delivered + s.skipped_other_type + s.skipped_low_maturity + s.parked == 0:
            break
    return total


def retry_parked(store: EventStore, brain: Brain) -> int:
    """Re-deliver the librarian's dead-lettered events (e.g. after a brain outage). Returns how many recovered."""
    return store.retry_parked(NAME, librarian_handler(brain))
