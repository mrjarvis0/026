"""Items stored but never clustered must be recovered (found in the 2026-10-28 audit).

Regression: ingest committed items first and ran the narrative update outside any try. If the update raised,
the items stayed stored but un-clustered, and every later scan treated them as duplicates — they never
reached a narrative — and ingest raised despite its "never raises" contract.
"""
import asyncio

from agents.A002_News_Intelligence.core import pipeline
from agents.A002_News_Intelligence.core.models import RawItem
from agents.A002_News_Intelligence.core.storage import Storage


def raw(n=1):
    return RawItem(source="rss_test", source_key=f"rss_test:{n}", url=f"http://x/{n}",
                   title=f"Fed signals rate hold as inflation cools {n}", content="Bitcoin and equities steady.")


def run(db, items, monkeypatch):
    async def fake_fetch(settings, max_workers=4):
        return items, []

    monkeypatch.setattr(pipeline, "fetch_all", fake_fetch)
    return asyncio.run(pipeline.ingest(db_path=str(db)))


def clustered_item_ids(db):
    import sqlite3
    return {r[0] for r in sqlite3.connect(db).execute("SELECT item_id FROM narrative_items")}


def stored_item_ids(db):
    import sqlite3
    return {r[0] for r in sqlite3.connect(db).execute("SELECT id FROM items")}


def test_a_failing_cluster_update_is_reported_not_raised(tmp_path, monkeypatch):
    db = tmp_path / "a002.db"

    async def boom(self, storage, items, now=None):
        raise RuntimeError("cluster exploded")

    monkeypatch.setattr(pipeline.NarrativeEngine, "update", boom)
    report = run(db, [raw(1)], monkeypatch)                      # must not raise
    assert report.stored == 1 and report.failed >= 1
    assert any("cluster" in e and "exploded" in e for e in report.errors)
    assert stored_item_ids(db) and not clustered_item_ids(db)


def test_unclustered_items_are_clustered_on_the_next_ingest(tmp_path, monkeypatch):
    db = tmp_path / "a002.db"
    real_update = pipeline.NarrativeEngine.update

    async def boom(self, storage, items, now=None):
        raise RuntimeError("cluster exploded")

    monkeypatch.setattr(pipeline.NarrativeEngine, "update", boom)
    run(db, [raw(1)], monkeypatch)
    monkeypatch.setattr(pipeline.NarrativeEngine, "update", real_update)
    report = run(db, [], monkeypatch)                            # nothing new fetched; the orphan is recovered
    assert report.recovered == 1
    assert clustered_item_ids(db) == stored_item_ids(db)


def test_clustered_items_are_not_reclustered(tmp_path, monkeypatch):
    db = tmp_path / "a002.db"
    run(db, [raw(1)], monkeypatch)
    assert clustered_item_ids(db) == stored_item_ids(db)
    report = run(db, [], monkeypatch)
    assert report.recovered == 0
    storage = Storage(db)
    assert len(asyncio.run(storage.load_active_narratives("1970-01-01T00:00:00"))) == 1   # no duplicate narrative


def test_one_poison_item_does_not_block_the_rest(tmp_path, monkeypatch):
    # review #8: one item that deterministically raised in update() blocked every later item in the window
    db = tmp_path / "a002.db"
    real = pipeline.NarrativeEngine.update

    async def selective(self, storage, items, now=None):
        if any("POISON" in i.title for i in items):
            raise RuntimeError("poison item")
        return await real(self, storage, items, now)

    monkeypatch.setattr(pipeline.NarrativeEngine, "update", selective)
    poison = RawItem(source="rss_test", source_key="rss_test:p", url="http://x/p",
                     title="POISON headline about gold", content="x")
    report = run(db, [poison, raw(2)], monkeypatch)
    assert len(stored_item_ids(db)) == 2 and len(clustered_item_ids(db)) == 1      # the good one still clustered
    assert report.failed >= 1 and any("poison" in e for e in report.errors)
    other = RawItem(source="rss_test", source_key="rss_test:o", url="http://x/o",
                    title="Oil prices jump after surprise OPEC output cut", content="Brent rallies.")
    run(db, [other], monkeypatch)                                                   # later cycles are not blocked either
    assert len(clustered_item_ids(db)) == 2
