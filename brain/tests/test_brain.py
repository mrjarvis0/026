import pytest

from brain.store import Brain, valid_namespace
from brain.access import AgentBrainView, NamespaceDenied

A001_MANIFEST = {"memory": {"reads": ["global", "entities", "chain", "projects.*"],
                           "writes": ["chain", "projects.*"]}}
A002_MANIFEST = {"memory": {"reads": ["global", "entities", "news", "projects.*"],
                           "writes": ["news", "projects.*"]}}


def test_write_then_read_and_read_is_logged():
    b = Brain()
    b.write("chain", "0xabc", {"z": 7.1}, by="A001")
    assert b.read("chain", "0xabc", by="A002") == {"z": 7.1}
    reads = b.reads_of("chain", "0xabc")
    assert len(reads) == 1 and reads[0]["by"] == "A002"


def test_writes_are_versioned_never_overwritten():
    b = Brain()
    assert b.write("news", "rumor1", {"score": 40}, by="A002") == 1
    assert b.write("news", "rumor1", {"score": 78}, by="A002") == 2
    assert b.read("news", "rumor1", by="A002") == {"score": 78}
    hist = b.history("news", "rumor1")
    assert [h["version"] for h in hist] == [1, 2]
    assert hist[0]["value"] == {"score": 40}


def test_invalid_namespace_rejected():
    b = Brain()
    assert valid_namespace("entities") and valid_namespace("projects/inv1")
    assert not valid_namespace("../etc") and not valid_namespace("Global")
    with pytest.raises(ValueError):
        b.write("../etc", "k", 1, by="A001")


def test_agent_view_enforces_write_scope():
    b = Brain()
    a001 = AgentBrainView(b, "A001", A001_MANIFEST)
    a001.write("chain", "0xabc", {"z": 7.1})           # declared -> ok
    a001.write("projects/inv1", "note", {"n": 1})       # projects.* -> ok
    with pytest.raises(NamespaceDenied):
        a001.write("news", "rumor1", {"score": 1})      # not declared -> denied


def test_agent_view_enforces_read_scope_and_shared_entities():
    b = Brain()
    a001 = AgentBrainView(b, "A001", A001_MANIFEST)
    a002 = AgentBrainView(b, "A002", A002_MANIFEST)
    # A001 records a shared entity; A002 cites it (the correlation fuel of §7).
    b.write("entities", "0xabc", {"label": "exchange"}, by="A001")
    assert a002.read("entities", "0xabc") == {"label": "exchange"}
    # But A002 may not read A001's private domain namespace.
    with pytest.raises(NamespaceDenied):
        a002.read("chain", "0xabc")


def test_file_brain_uses_wal(tmp_path):
    # the first live consume wrote ~1.4 s per event with a rollback journal + full fsync on a slow disk
    b = Brain(str(tmp_path / "brain.db"))
    assert b._db.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


def test_memory_brain_is_unaffected():
    b = Brain(":memory:")
    assert b.write("global", "k", {"v": 1}, by="t") == 1 and b.read("global", "k", by="t") == {"v": 1}
