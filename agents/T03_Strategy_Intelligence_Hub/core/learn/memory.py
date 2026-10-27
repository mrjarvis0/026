"""Persistent mistakes memory: remember losing patterns so they aren't repeated.

Stored per agent under results/: `mistakes.jsonl` (raw lessons) + a rendered
`MISTAKES.md` (aggregated, most-costly recurring mistakes first). Mirrors the
sibling StallBreaker's training/mistakes design.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from .reflect import Lesson


class MistakeMemory:
    def __init__(self, agent_dir: Path) -> None:
        self.dir = agent_dir / "results"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.jsonl = self.dir / "mistakes.jsonl"
        self.md = self.dir / "MISTAKES.md"

    # -- write --
    def record(self, lesson: Lesson, source: str = "backtest") -> None:
        row = {
            "date": date.today().isoformat(), "source": source,
            "category": lesson.category, "signature": lesson.signature,
            "message": lesson.message, "rule": lesson.rule,
            "loss_pct": lesson.loss_pct, "direction": lesson.direction,
        }
        with self.jsonl.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")

    def record_many(self, lessons: list[Lesson], source: str = "backtest") -> int:
        for les in lessons:
            self.record(les, source)
        return len(lessons)

    # -- read / aggregate --
    def all_rows(self) -> list[dict]:
        if not self.jsonl.exists():
            return []
        rows = []
        for line in self.jsonl.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    def aggregate(self) -> list[dict]:
        """Group by signature: repeats, total & avg loss, the rule. Costliest first."""
        groups: dict[str, dict] = defaultdict(lambda: {"repeats": 0, "total_loss": 0.0})
        for r in self.all_rows():
            g = groups[r["signature"]]
            g["repeats"] += 1
            g["total_loss"] += float(r.get("loss_pct", 0.0))
            g["category"] = r["category"]
            g["message"] = r["message"]
            g["rule"] = r["rule"]
            g["signature"] = r["signature"]
        out = []
        for sig, g in groups.items():
            g["avg_loss"] = g["total_loss"] / g["repeats"] if g["repeats"] else 0.0
            out.append(g)
        out.sort(key=lambda g: g["total_loss"])  # most negative (costliest) first
        return out

    # -- render --
    def render_markdown(self, agent_name: str) -> Path:
        agg = self.aggregate()
        lines = [
            f"# Mistakes learned — `{agent_name}`",
            "",
            f"_Updated {date.today().isoformat()}. {len(self.all_rows())} losing trades analyzed, "
            f"{len(agg)} distinct mistake patterns._",
            "",
            "Ranked by total cost. Each has a **RULE** to follow so it is not repeated.",
            "",
        ]
        if not agg:
            lines.append("_No losing patterns recorded yet._")
        for i, g in enumerate(agg, 1):
            lines += [
                f"## {i}. {g['category']}  ×{g['repeats']}  (total {g['total_loss']:.1%}, avg {g['avg_loss']:.1%})",
                "",
                f"- {g['message']}",
                f"- **RULE:** {g['rule']}",
                "",
            ]
        self.md.write_text("\n".join(lines), encoding="utf-8")
        return self.md
