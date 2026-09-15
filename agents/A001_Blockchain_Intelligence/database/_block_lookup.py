"""
CIE-OS
A001 Blockchain Intelligence Agent

Module:
    database._block_lookup

Purpose:
    Ask which of a set of block hashes exist in the ``blocks`` table for one
    chain. Extracted from ``database.tokens`` and ``database.approvals``, which
    both need the same orphan-guard before inserting foreign-key-bound rows;
    keeping the SQL in one place stops the two copies from drifting.

Notes:
    Chunked to stay under SQLite's ``SQLITE_LIMIT_VARIABLE_NUMBER`` (999 on
    older builds, 32766 on 3.32+). A single ingestion batch spanning more
    distinct blocks than the limit would otherwise raise ``too many SQL
    variables`` at the top of the write path -- silent in scope but hard to
    diagnose from outside.
"""

from __future__ import annotations

from .connection import Database

#: Below both the historical (999) and modern (32766) SQLite limits, leaving
#: room for the two static params (chain and the query itself).
_CHUNK: int = 500


def known_blocks(database: Database, chain: str, hashes: set[str]) -> set[str]:
    """Which of ``hashes`` are stored in ``blocks`` for ``chain``."""
    if not hashes:
        return set()
    found: set[str] = set()
    remaining = list(hashes)
    for i in range(0, len(remaining), _CHUNK):
        chunk = remaining[i : i + _CHUNK]
        placeholders = ",".join("?" for _ in chunk)
        rows = database.connection.execute(
            f"SELECT block_hash FROM blocks WHERE chain = ? "
            f"AND block_hash IN ({placeholders})",
            (chain, *chunk),
        )
        found.update(row["block_hash"] for row in rows)
    return found


__all__ = ["known_blocks"]
