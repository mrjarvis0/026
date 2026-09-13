"""Architecture law: downward-only imports (AGENTS.md §0, §10; ADR-0001).

The kernel never imports an agent, and an agent never imports the kernel or the
composition root. The sentinel (a low platform service) never imports the manager
above it. This is checked mechanically over *absolute* imports.

Note on the fleet: A01/A02 were migrated from CIE-OS and use bare top-level imports
(`config`, `core`, `security`, ...) that name-collide with the platform's packages but
are their OWN modules. So the agent checks only forbid names that do NOT exist inside any
agent — `orchestrator` and `bootstrap` — which makes any such import an unambiguous,
genuine violation.
"""
from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _imported_top_levels(pkg_dir: pathlib.Path):
    """Yield (file, top_level_module) for every absolute import under pkg_dir."""
    for py in pkg_dir.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    yield py, alias.name.split(".")[0]
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:  # absolute import only
                    yield py, node.module.split(".")[0]


def _offenders(pkg_dir: pathlib.Path, forbidden: set[str]):
    return sorted({
        f"{f.relative_to(ROOT)} -> {mod}"
        for f, mod in _imported_top_levels(pkg_dir)
        if mod in forbidden
    })


def test_security_does_not_import_up_or_into_the_fleet():
    # The sentinel is a low platform service: it reads agents as data, imports none,
    # and must not import the manager (orchestrator) or the composition root.
    offenders = _offenders(ROOT / "security", {"orchestrator", "bootstrap", "agents", "brain"})
    assert not offenders, offenders


def test_orchestrator_does_not_import_agents_or_composition_root():
    # The manager may import lower services (e.g. security.sentinel.gate) but never an
    # agent, and never the composition root that wires it.
    offenders = _offenders(ROOT / "orchestrator", {"agents", "bootstrap"})
    assert not offenders, offenders


def test_agents_do_not_import_kernel_or_composition_root():
    forbidden = {"orchestrator", "bootstrap", "brain"}  # names no agent defines internally
    offenders: list[str] = []
    for agent in ("A01_Blockchain_Intelligence", "A02_News_Intelligence"):
        offenders += _offenders(ROOT / "agents" / agent, forbidden)
    assert not offenders, offenders


def test_brain_does_not_import_up_or_into_the_fleet():
    # The brain is a low platform service: stdlib + itself only.
    offenders = _offenders(ROOT / "brain", {"orchestrator", "bootstrap", "agents", "security"})
    assert not offenders, offenders
