import pytest

from brain.store import Brain, valid_namespace
from brain.access import AgentBrainView, NamespaceDenied

A01_MANIFEST = {"memory": {"reads": ["global", "entities", "chain", "projects.*"],
                           "writes": ["chain", "projects.*"]}}
A02_MANIFEST = {"memory": {"reads": ["global", "entities", "news", "projects.*"],
                           "writes": ["news", "projects.*"]}}


def test_write_then_read_and_read_is_logged():
    b = Brain()
    b.write("chain", "0xabc", {"z": 7.1}, by="A01")
    assert b.read("chain", "0xabc", by="A02") == {"z": 7.1}
    reads = b.reads_of("chain", "0xabc")
    assert len(reads) == 1 and reads[0]["by"] == "A02"


def test_writes_are_versioned_never_overwritten():
    b = Brain()
    assert b.write("news", "rumor1", {"score": 40}, by="A02") == 1
    assert b.write("news", "rumor1", {"score": 78}, by="A02") == 2
    assert b.read("news", "rumor1", by="A02") == {"score": 78}
    hist = b.history("news", "rumor1")
    assert [h["version"] for h in hist] == [1, 2]
    assert hist[0]["value"] == {"score": 40}


def test_invalid_namespace_rejected():
    b = Brain()
    assert valid_namespace("entities") and valid_namespace("projects/inv1")
    assert not valid_namespace("../etc") and not valid_namespace("Global")
    with pytest.raises(ValueError):
        b.write("../etc", "k", 1, by="A01")


def test_agent_view_enforces_write_scope():
    b = Brain()
    a01 = AgentBrainView(b, "A01", A01_MANIFEST)
    a01.write("chain", "0xabc", {"z": 7.1})           # declared -> ok
    a01.write("projects/inv1", "note", {"n": 1})       # projects.* -> ok
    with pytest.raises(NamespaceDenied):
        a01.write("news", "rumor1", {"score": 1})      # not declared -> denied


def test_agent_view_enforces_read_scope_and_shared_entities():
    b = Brain()
    a01 = AgentBrainView(b, "A01", A01_MANIFEST)
    a02 = AgentBrainView(b, "A02", A02_MANIFEST)
    # A01 records a shared entity; A02 cites it (the correlation fuel of §7).
    b.write("entities", "0xabc", {"label": "exchange"}, by="A01")
    assert a02.read("entities", "0xabc") == {"label": "exchange"}
    # But A02 may not read A01's private domain namespace.
    with pytest.raises(NamespaceDenied):
        a02.read("chain", "0xabc")
