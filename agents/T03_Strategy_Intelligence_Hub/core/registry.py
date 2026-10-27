"""Serial registry: allocate agent serials in order and resolve agent folders.

`AGENTS_INDEX.md` is the single source of truth. It holds a markdown table plus a
`<!-- next-serial: N -->` marker. Serials are allocated strictly in order so they
are never reused (Constitution: naming rule in $trategy-master.agent.md §3).
"""
from __future__ import annotations

import importlib.util
import inspect
import re
from datetime import date
from pathlib import Path
from typing import Any

from .config import AGENTS_DIR, REGISTRY_FILE
from .strategy_base import StrategySpec

_ROW_RE = re.compile(r"^\|\s*\$(\d+)\s*\|\s*([^|]+?)\s*\|", re.MULTILINE)
_NEXT_RE = re.compile(r"<!--\s*next-serial:\s*(\d+)\s*-->")


def slugify(owner: str) -> str:
    """Turn a trader's name into a folder-safe lowercase slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", owner.strip().lower()).strip("-")
    return slug or "unknown"


def format_serial(n: int) -> str:
    """3-digit zero-padded serial with the `$` prefix, e.g. 1 -> '$001'."""
    return f"${n:03d}"


def agent_folder_name(n: int, owner_slug: str) -> str:
    """'$001-dennis' from (1, 'dennis')."""
    return f"{format_serial(n)}-{owner_slug}"


def _read_registry() -> str:
    return REGISTRY_FILE.read_text(encoding="utf-8")


def existing_serials() -> list[int]:
    """All serial numbers already recorded in the table."""
    return sorted(int(m.group(1)) for m in _ROW_RE.finditer(_read_registry()))


def next_serial() -> int:
    """The next serial to allocate.

    Cross-checks the `<!-- next-serial -->` marker against the max serial in the
    table and returns whichever is larger, so a hand-edit can never cause reuse.
    """
    text = _read_registry()
    marker = _NEXT_RE.search(text)
    marker_val = int(marker.group(1)) if marker else 1
    serials = [int(m.group(1)) for m in _ROW_RE.finditer(text)]
    table_next = (max(serials) + 1) if serials else 1
    return max(marker_val, table_next)


def append_agent_row(
    serial: int,
    owner: str,
    owner_slug: str,
    market: str,
    strategy: str,
    status: str = "scaffolded",
) -> str:
    """Append a row for a new agent and bump the next-serial marker.

    Returns the agent folder name (e.g. '$001-dennis').
    """
    folder = agent_folder_name(serial, owner_slug)
    row = (
        f"| {format_serial(serial)} | {folder} | {owner} | {market} "
        f"| {strategy} | {status} | {date.today().isoformat()} |"
    )
    text = _read_registry()

    # insert the row directly after the last existing table row
    lines = text.splitlines()
    last_row_idx = max(
        (i for i, ln in enumerate(lines) if _ROW_RE.match(ln)), default=None
    )
    if last_row_idx is None:
        raise RuntimeError("AGENTS_INDEX.md has no table rows to append after")
    lines.insert(last_row_idx + 1, row)
    text = "\n".join(lines)

    # bump the marker
    text = _NEXT_RE.sub(f"<!-- next-serial: {serial + 1} -->", text)
    REGISTRY_FILE.write_text(text, encoding="utf-8")
    return folder


# --- resolving & loading agents ----------------------------------------------
def resolve_agent(name: str) -> Path:
    """Find an agent folder from a flexible identifier.

    Accepts '$001-dennis', '001-dennis', 'dennis', '$001', '001', or '1'.
    """
    name = name.strip()
    candidates = [p for p in AGENTS_DIR.iterdir() if p.is_dir()] if AGENTS_DIR.exists() else []

    # exact folder-name match
    for p in candidates:
        if p.name == name or p.name == f"${name}":
            return p

    # by serial number
    digits = re.sub(r"\D", "", name)
    if digits:
        serial = format_serial(int(digits))
        for p in candidates:
            if p.name.startswith(serial + "-") or p.name == serial:
                return p

    # by owner slug
    slug = slugify(name)
    for p in candidates:
        if p.name.split("-", 1)[-1] == slug:
            return p

    raise FileNotFoundError(
        f"No agent matching '{name}' under {AGENTS_DIR}. "
        f"Available: {[p.name for p in candidates]}"
    )


def load_agent_config(agent_dir: Path) -> dict[str, Any]:
    """Load an agent's config.yaml (symbols, timeframe, params, market)."""
    import yaml  # local import so pandas-only tasks don't require PyYAML

    cfg_path = agent_dir / "config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"{cfg_path} not found")
    with cfg_path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_strategy(agent_dir: Path, **param_overrides: Any) -> StrategySpec:
    """Dynamically import strategy.py and instantiate its StrategySpec subclass.

    Agent folders are named with '$' and '-', which are not valid module names, so
    we load by file path via importlib rather than a normal import.

    We ensure HUB_ROOT is on sys.path so the strategy file's top-level
    `from core.strategy_base import StrategySpec` always resolves — even when
    load_strategy() is called without running through scripts/_common.py first
    (e.g. from the T01 bridge, tests, or the 026 orchestrator).
    """
    import sys as _sys
    from .config import HUB_ROOT as _HUB_ROOT
    _hub_str = str(_HUB_ROOT)
    if _hub_str not in _sys.path:
        _sys.path.insert(0, _hub_str)

    strat_path = agent_dir / "strategy.py"
    if not strat_path.exists():
        raise FileNotFoundError(f"{strat_path} not found")

    mod_name = "agent_strategy_" + re.sub(r"\W", "_", agent_dir.name)
    spec = importlib.util.spec_from_file_location(mod_name, strat_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module spec from {strat_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for _, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, StrategySpec) and obj is not StrategySpec:
            return obj(**param_overrides)

    raise TypeError(f"No StrategySpec subclass found in {strat_path}")
