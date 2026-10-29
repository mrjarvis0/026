"""Run one round of messages through the real message bus and return its trace.

Read by the dashboard's /trace page. Uses the same composition root as the kernel
(bootstrap.wire.build_bus: real manifests, the sentinel gate, the A001/A002/A015
read-only adapters, no brain handle, so nothing is written).

stdin:  {"messages": [{"to", "type", "payload", "action"?, "budget"?}, ...]}
stdout: {"results": [{"message", "response", "ms"}], "trace": [...]}
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root

from bootstrap.wire import build_bus  # noqa: E402
from orchestrator.event_bus.message import Budget, Message  # noqa: E402

MAX_PAYLOAD_BYTES = 3000


def main() -> None:
    request = json.load(sys.stdin)
    bus = build_bus()
    results = []
    for spec in request["messages"]:
        message = Message(
            to=spec["to"], type=spec["type"], payload=spec.get("payload") or {},
            action=spec.get("action"), budget=Budget(calls=int(spec.get("budget", 100))),
        )
        started = time.perf_counter()
        try:
            response = asdict(bus.send(message))
        except Exception as exc:  # the bus already contains handler crashes; this is belt and braces
            response = {"ok": False, "status": "error", "payload": {}, "reason": f"{type(exc).__name__}: {exc}"}
        body = json.dumps(response.get("payload") or {}, default=str)
        if len(body) > MAX_PAYLOAD_BYTES:
            response["payload"] = {"_truncated": True, "_bytes": len(body), "preview": body[:1500]}
        results.append({
            "message": message.as_dict(),
            "response": response,
            "ms": round((time.perf_counter() - started) * 1000, 1),
        })
    print(json.dumps({"results": results, "trace": bus.trace.entries}, default=str))


if __name__ == "__main__":
    main()
