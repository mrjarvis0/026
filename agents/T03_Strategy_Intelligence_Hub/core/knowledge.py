"""Read the knowledge source (research dossiers + sources).

Lets scripts/agents query the hub's research memory programmatically. Dossiers are
markdown files with a small YAML frontmatter block; see knowledge/strategies/_TEMPLATE.md.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .config import HUB_ROOT

KNOWLEDGE_DIR: Path = HUB_ROOT / "knowledge"
STRATEGIES_DIR: Path = KNOWLEDGE_DIR / "strategies"
SOURCES_FILE: Path = KNOWLEDGE_DIR / "sources" / "SOURCES.md"

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)
_TABLE_ROW_RE = re.compile(r"^\|\s*`?(\[[^\]]+\])`?\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|")


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        import yaml
        meta = yaml.safe_load(m.group(1)) or {}
    except Exception:
        meta = {}
    return meta, m.group(2)


def load_dossier(slug: str) -> dict[str, Any]:
    """Load one strategy dossier by slug or filename (frontmatter + 'body')."""
    path = STRATEGIES_DIR / (slug if slug.endswith(".md") else f"{slug}.md")
    if not path.exists():
        # try matching by frontmatter slug
        for p in STRATEGIES_DIR.glob("*.md"):
            meta, _ = _parse_frontmatter(p.read_text(encoding="utf-8"))
            if meta.get("slug") == slug:
                path = p
                break
    if not path.exists():
        raise FileNotFoundError(f"No dossier for '{slug}' in {STRATEGIES_DIR}")
    meta, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
    meta["body"] = body.strip()
    meta["file"] = str(path)
    return meta


def list_dossiers() -> list[dict[str, Any]]:
    """All researched strategies (frontmatter only), excluding the template."""
    out: list[dict[str, Any]] = []
    if not STRATEGIES_DIR.exists():
        return out
    for p in sorted(STRATEGIES_DIR.glob("*.md")):
        if p.name.startswith("_"):
            continue
        meta, _ = _parse_frontmatter(p.read_text(encoding="utf-8"))
        meta["file"] = p.name
        out.append(meta)
    return out


def list_sources() -> list[dict[str, str]]:
    """Bibliography entries from SOURCES.md ({tag, source, type, link})."""
    out: list[dict[str, str]] = []
    if not SOURCES_FILE.exists():
        return out
    for line in SOURCES_FILE.read_text(encoding="utf-8").splitlines():
        m = _TABLE_ROW_RE.match(line)
        if m and m.group(1) != "[TAG]":
            out.append({"tag": m.group(1), "source": m.group(2), "type": m.group(3), "link": m.group(4)})
    return out


# convenience alias used in docs
list_traders = list_dossiers
