"""
026 live supervisor — keeps the agents' data fresh so the dashboard is live.

What it does (all local, no new services):
  - On start: run A001 ingest + A002 scan once, step by step. This is the
    "PC on -> rescan" behaviour: launch it at logon and the fleet refreshes.
  - Then on a schedule: A001 ingest every 30 min, A002 scan every 2 hours.
  - After each A002 scan it asks A002 for upcoming scheduled events (its
    best-effort `events` command). For each event it fires BOTH agents twice,
    5 minutes apart, around the event time.

State is persisted to live/state.json so a restart resumes without repeating
work or re-firing past events. Everything is logged to live/supervisor.log.
Stop it with stop-026.bat or by ending the python process.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STATE_FILE = REPO / "live" / "state.json"
LOG_FILE = REPO / "live" / "supervisor.log"
# A001 uses bare top-level imports (interfaces.*, cli.*), so it must run from its
# own directory as `cli.main`, with a db path relative to that directory.
A001_DIR = REPO / "agents" / "A001_Blockchain_Intelligence"
A001_DB = "data/a001.db"

# Cadence (minutes). Defaults per operator.
A001_EVERY_MIN = 30
A002_EVERY_MIN = 120
# A001 tuning. Token-transfer fetching is ~600 logs/block and very slow on a free
# RPC key, so the live loop fetches headers+transactions only (fast: ~30 blocks/80s).
# Exchange flows (token-based) then refresh only when you run a token ingest by hand.
# With a paid RPC key you can raise A001_BLOCKS and set A001_TOKENS = True.
# ponytail: free-key ceiling — 60 blocks/cycle won't fully keep pace with Ethereum's
# head (~150 blocks/30min); raise blocks or add RPC quota to close the gap.
A001_BLOCKS = 60
A001_TOKENS = False
EVENT_SCANS = 2                 # scans per detected event
EVENT_GAP_MIN = 5              # minutes between those scans
EVENT_GRACE_MIN = 120         # if PC was off, don't fire an event more than this late
TICK_SEC = 30                 # how often the loop checks what's due

PY = sys.executable


def log(msg: str) -> None:
    line = f"{datetime.now(UTC).isoformat(timespec='seconds')}  {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def run(args: list[str], label: str, timeout: int = 900, cwd: Path = REPO) -> None:
    """Run one agent command; log the outcome, never raise into the loop."""
    log(f"RUN {label}: {' '.join(args)}")
    try:
        p = subprocess.run([PY, "-m", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)
        tail = (p.stdout or p.stderr or "").strip().splitlines()
        log(f"  {label} exit={p.returncode}" + (f" | {tail[-1]}" if tail else ""))
    except subprocess.TimeoutExpired:
        log(f"  {label} TIMEOUT after {timeout}s")
    except Exception as exc:  # noqa: BLE001 - the loop must survive anything
        log(f"  {label} ERROR {type(exc).__name__}: {exc}")


def a001_ingest() -> None:
    args = ["cli.main", "ingest", "--db", A001_DB, "--blocks", str(A001_BLOCKS)]
    if A001_TOKENS:
        args.append("--tokens")
    run(args, "A001 ingest", cwd=A001_DIR)


def a002_scan() -> None:
    run(["agents.A002_News_Intelligence.cli", "scan"], "A002 scan")


def a002_events() -> list[dict]:
    """Ask A002 for upcoming events (JSON on stdout). Empty on any failure."""
    try:
        p = subprocess.run(
            [PY, "-m", "agents.A002_News_Intelligence.cli", "events"],
            cwd=REPO, capture_output=True, text=True, timeout=120,
        )
        data = json.loads(p.stdout or "{}")
        return data.get("events", [])
    except Exception as exc:  # noqa: BLE001
        log(f"  A002 events ERROR {type(exc).__name__}: {exc}")
        return []


# ---- state -------------------------------------------------------------------

def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"a001_last": None, "a002_last": None, "events": {}}


def save_state(state: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError as exc:
        log(f"  state save ERROR {exc}")


def _due(last_iso: str | None, every_min: int, now: datetime) -> bool:
    if not last_iso:
        return True
    return now - datetime.fromisoformat(last_iso) >= timedelta(minutes=every_min)


def fire_event_pair(state: dict) -> None:
    """Both agents together — the event moment is worth an on-chain + news look."""
    a001_ingest()
    a002_scan()


def refresh_events(state: dict, now: datetime) -> None:
    """Merge A002's detected events into the watch list (keyed by when+claim)."""
    for ev in a002_events():
        key = f"{ev['when']}::{ev['claim'][:40]}"
        if key not in state["events"]:
            state["events"][key] = {"when": ev["when"], "matched": ev.get("matched", ""), "runs_done": 0, "next_run": ev["when"]}
            log(f"  watch event @ {ev['when']} ({ev.get('matched','')})")


def process_events(state: dict, now: datetime) -> None:
    for key, ev in list(state["events"].items()):
        when = datetime.fromisoformat(ev["when"])
        if ev["runs_done"] >= EVENT_SCANS:
            # keep briefly, then forget once well past
            if now - when > timedelta(hours=6):
                del state["events"][key]
            continue
        if now - when > timedelta(minutes=EVENT_GRACE_MIN) and ev["runs_done"] == 0:
            log(f"  event @ {ev['when']} missed by >{EVENT_GRACE_MIN}m (PC off?) — skipping")
            ev["runs_done"] = EVENT_SCANS
            continue
        if now >= datetime.fromisoformat(ev["next_run"]):
            log(f"EVENT FIRE {ev['runs_done']+1}/{EVENT_SCANS} @ {ev['when']} ({ev['matched']})")
            fire_event_pair(state)
            ev["runs_done"] += 1
            ev["next_run"] = (now + timedelta(minutes=EVENT_GAP_MIN)).isoformat()


def main() -> None:
    log("=" * 60)
    log(f"026 supervisor start · A001 every {A001_EVERY_MIN}m · A002 every {A002_EVERY_MIN}m · py={PY}")
    state = load_state()

    # PC-on step-by-step refresh: A002 first (fast, and events depend on it),
    # then A001 (slower). "jab bhi PC open karu -> rescan chalu."
    log("startup refresh (step by step)")
    a002_scan()
    state["a002_last"] = datetime.now(UTC).isoformat()
    refresh_events(state, datetime.now(UTC))
    save_state(state)
    a001_ingest()
    state["a001_last"] = datetime.now(UTC).isoformat()
    save_state(state)

    while True:
        try:
            now = datetime.now(UTC)
            if _due(state["a001_last"], A001_EVERY_MIN, now):
                a001_ingest()
                state["a001_last"] = datetime.now(UTC).isoformat()
                save_state(state)
            if _due(state["a002_last"], A002_EVERY_MIN, now):
                a002_scan()
                state["a002_last"] = datetime.now(UTC).isoformat()
                refresh_events(state, datetime.now(UTC))
                save_state(state)
            process_events(state, datetime.now(UTC))
            save_state(state)
        except Exception as exc:  # noqa: BLE001 - never let the loop die
            log(f"LOOP ERROR {type(exc).__name__}: {exc}")
        time.sleep(TICK_SEC)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("supervisor stopped (KeyboardInterrupt)")
