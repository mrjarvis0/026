"""Load the 026 fleet: registry + each agent.yaml + the AGENTS.md §3 table."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_ROW = re.compile(r"^\|\s*`(A\d{2})`\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|")


@dataclass
class AgentRecord:
    id: str
    dir: Path
    manifest: dict[str, Any]
    registry_row: dict[str, Any]
    fleet_row: dict[str, Any] | None


def parse_fleet_table(agents_md_text: str) -> dict[str, dict]:
    table: dict[str, dict] = {}
    for line in agents_md_text.splitlines():
        m = _ROW.match(line)
        if not m:
            continue
        agent_id, name, status = m.group(1), m.group(2), m.group(3)
        if "reserved" in name.lower():
            continue
        table[agent_id] = {"id": agent_id, "name": name.strip(), "status": status.strip()}
    return table


def load_fleet(repo_root: Path, policy: dict) -> list[AgentRecord]:
    reg_path = repo_root / policy["registry"]["registry_file"]
    registry = yaml.safe_load(reg_path.read_text(encoding="utf-8")) or {}
    agents = registry.get("agents", {})
    fleet_table = parse_fleet_table(
        (repo_root / policy["registry"]["agents_md"]).read_text(encoding="utf-8"))

    records: list[AgentRecord] = []
    for agent_id, row in agents.items():
        agent_dir = repo_root / row["dir"]
        manifest_path = repo_root / row["manifest"]
        manifest: dict[str, Any] = {}
        if manifest_path.exists():
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        records.append(AgentRecord(
            id=agent_id, dir=agent_dir, manifest=manifest,
            registry_row=row, fleet_row=fleet_table.get(agent_id)))
    return records
