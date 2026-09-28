"""Ask the real brain access layer whether an agent may read or write a namespace.

Read by the dashboard's /brain page. Runs brain.AgentBrainView against a throwaway
in-memory Brain, so nothing is stored anywhere. An allowed write is performed twice to
show versioning; an allowed read shows the read being logged.

stdin:  {"agent": "A002", "manifest": "<abs path to agent.yaml>", "op": "read"|"write", "namespace": "news"}
stdout: {"decision": "allowed"|"denied"|"invalid", "reason"?, "versions"?, "history"?, "value"?, "reads"?}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root

import yaml  # noqa: E402

from brain import AgentBrainView, Brain, NamespaceDenied, valid_namespace  # noqa: E402

KEY = "dashboard-check"


def main() -> None:
    req = json.load(sys.stdin)
    manifest = yaml.safe_load(Path(req["manifest"]).read_text(encoding="utf-8")) or {}
    brain = Brain()  # :memory: — discarded when this process exits
    view = AgentBrainView(brain, req["agent"], manifest)
    ns = req["namespace"]
    out: dict = {"valid_namespace": valid_namespace(ns)}
    try:
        if req["op"] == "write":
            first = view.write(ns, KEY, {"write": 1})
            second = view.write(ns, KEY, {"write": 2})
            out.update(decision="allowed", versions=[first, second], history=brain.history(ns, KEY))
        else:
            value = view.read(ns, KEY)
            out.update(decision="allowed", value=value, reads=brain.reads_of(ns, KEY))
    except NamespaceDenied as exc:
        out.update(decision="denied", reason=str(exc))
    except ValueError as exc:
        out.update(decision="invalid", reason=str(exc))
    print(json.dumps(out, default=str))


if __name__ == "__main__":
    main()
