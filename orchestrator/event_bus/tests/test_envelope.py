"""Envelope validator — each test names the defect or rule it guards (design spec section 6)."""
import pytest

from orchestrator.event_bus.tests.helpers import MANIFESTS, sample_event
from orchestrator.event_bus.envelope import (
    EnvelopeError,
    canonical_json,
    load_schemas,
    make_event_id,
    passes_maturity,
    type_matches,
    validate_event,
)

SCHEMAS = load_schemas()
def check(event, schemas=SCHEMAS, manifests=MANIFESTS):
    validate_event(event, schemas, manifests)


def rejects(event, word):
    with pytest.raises(EnvelopeError, match=word):
        check(event)


def test_valid_event_passes():
    check(sample_event())


def test_unregistered_type_rejected():
    rejects(sample_event(type="a015.listing.unknown"), "unregistered")


def test_source_without_produces_rejected():
    rejects(sample_event(source="A002"), "produce")


def test_platform_type_only_from_SYS():
    stale = dict(type="system.source.stale", detector=None, evidence=[],
                 data={"source": "A015:binance", "max_age_s": 1800, "last_ok_at": None})
    rejects(sample_event(**stale), "platform")
    check(sample_event(source="SYS", **stale))


def test_confidence_above_ceiling_rejected():
    rejects(sample_event(confidence=0.9,
                         detector={"id": "X", "maturity": "implemented", "ceiling": 0.6}), "ceiling")


def test_confidence_none_allowed():
    check(sample_event(confidence=None))


def test_detector_requires_evidence():
    rejects(sample_event(evidence=[]), "evidence")


def test_naive_timestamp_rejected():
    rejects(sample_event(observed_at="2026-10-28T09:15:02"), "timestamp")


def test_event_window_reversed_rejected():
    rejects(sample_event(event_window={"from": "2026-10-28T10:00:00+00:00",
                                       "to": "2026-10-28T09:00:00+00:00"}), "window")


def test_missing_required_data_field_rejected():
    event = sample_event()
    del event["data"]["stated_reason"]
    rejects(event, "missing required")


def test_wrong_data_type_rejected():
    rejects(sample_event(data={"exchange": "binance", "symbol": "XYZ/USDT", "base": 7,
                               "stated_reason": "unspecified"}), "must be")


def test_optional_null_allowed():
    event = sample_event()
    event["data"]["median_crash_pct"] = None
    check(event)


def test_oversize_rejected():
    event = sample_event()
    event["data"]["historical_context"] = "x" * 70000
    rejects(event, "too large")


def test_untrusted_event_with_instruction_key_rejected():
    event = sample_event(untrusted=True)
    event["data"]["action"] = "sell everything"
    rejects(event, "instruction")


def test_type_matches_wildcard():
    assert type_matches("a015.*", "a015.listing.new")
    assert not type_matches("a015.*", "a002.rumor.opened")
    assert type_matches("a015.listing.new", "a015.listing.new")
    assert not type_matches("a015.listing.new", "a015.listing.delisted")


def test_passes_maturity():
    assert passes_maturity(sample_event(detector=None), "validated")
    assert not passes_maturity(sample_event(), "validated")
    assert passes_maturity(sample_event(), "implemented")
    validated = sample_event(detector={"id": "X", "maturity": "validated", "ceiling": 0.6})
    assert passes_maturity(validated, "validated")


def test_make_event_id_stable_and_prefixed():
    first = make_event_id("a", "b")
    assert first == make_event_id("a", "b") and first.startswith("evt_") and len(first) == 20
    assert first != make_event_id("a", "c")


def test_canonical_json_is_order_independent():
    assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1}) == '{"a":2,"b":1}'
