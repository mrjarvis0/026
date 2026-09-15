"""
CIE-OS
A001 Blockchain Intelligence Agent

Package:
    pipeline

Purpose:
    Turn a block into an answer without turning it into rows.

The old path was: fetch a block, normalize every transaction, store every
transaction, query the store later. Measured cost on ethereum: **0.70 MB per
block** -- roughly 5 GB a day, 150 GB a month, for one chain -- to keep 334
transactions per block so that a handful could later be counted.

The path here:

    RPC (cached, budgeted)
      -> block body in memory
      -> stream transactions through the materiality gate
           material?  -> kept
           otherwise  -> counted, then dropped
      -> one small aggregate row
      -> the body is released

The counting happens once, at capture. The rows it counted are never written.

Modules:
    ``materiality``  the keep-or-drop decision, percentile-based
    ``aggregate``    the counters that make dropping honest
    ``budget``       what each provider has been asked for, per day and month
    ``labels``       address lists read off disk into the ledger, with provenance
    ``flows``        stored transfers classified into exchange deposits and
                     withdrawals, bucketed by hour

The last two are the pair that makes the labelled-address rule real. The gate
above has always been able to keep a small transfer into a known exchange
address; until a list was loadable it had nothing to check against, and said so.
"""

from __future__ import annotations

from .aggregate import BlockAccumulator, FilterStats, accumulate
from .budget import Allowance, CallBudget, Pressure, Window
# NOTE: `Verdict` at package level is materiality.Verdict (imported below). budget.py
# has its own `Verdict` — import it explicitly as `pipeline.budget.Verdict`. Importing
# it here too shadowed one silently and risked flipping which class `pipeline.Verdict`
# resolves to if import order changed (ruff F811). Removed 2026-09-07.
from .flows import (
    Classification,
    FlowDirection,
    FlowStats,
    classify,
    roll_up,
    totals_by_entity,
)
from .labels import LabelFileError, LoadReport, discover, load, load_file, parse_file
from .writer import SelectiveStats, SelectiveWriter
from .materiality import (
    DEFAULT_PERCENTILE,
    MIN_POPULATION,
    Decision,
    MaterialityGate,
    Verdict,
    floor_from,
)

__all__ = [
    "DEFAULT_PERCENTILE",
    "MIN_POPULATION",
    "BlockAccumulator",
    "Decision",
    "FilterStats",
    "Allowance",
    "CallBudget",
    "Classification",
    "FlowDirection",
    "FlowStats",
    "LabelFileError",
    "LoadReport",
    "MaterialityGate",
    "Pressure",
    "Window",
    "SelectiveStats",
    "SelectiveWriter",
    "Verdict",
    "accumulate",
    "classify",
    "discover",
    "floor_from",
    "load",
    "load_file",
    "parse_file",
    "roll_up",
    "totals_by_entity",
]
