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
import os
import random
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STATE_FILE = REPO / "live" / "state.json"
LOG_FILE = REPO / "live" / "supervisor.log"
LOCK_FILE = REPO / "live" / "supervisor.lock"   # held for the process lifetime = single instance
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
RUN_TIMEOUT_SEC = 900         # one agent job may run this long before it counts as failed
# A failed job is retried with capped exponential backoff + jitter (AWS Builders' Library),
# not stamped as done and not hammered every tick.
BACKOFF_BASE_SEC = 60
BACKOFF_CAP_SEC = 30 * 60
# No heartbeat for longer than the slowest job (+ margin) means the supervisor is dead.
HEARTBEAT_STALE_SEC = 2 * RUN_TIMEOUT_SEC

PY = sys.executable

# Event-bus jobs (Phase 1). config/bus.json is plain JSON so this supervisor stays stdlib-only.
BUS_CONFIG_FILE = REPO / "config" / "bus.json"
_BUS_DEFAULTS = {"a015_exchanges": ["binance", "coinbase", "okx"], "a015_every_min": 15,
                 "stale_factor": 2, "retention_days": 90}
A015_CLI = "agents.A015_Exchange_Listing_Delisting_Intelligence.cli"
BUS_EVERY_MIN = 5             # relay + consume are two short subprocesses; A015 only produces every 15 min
PRUNE_EVERY_MIN = 7 * 24 * 60  # retention: weekly
JOB_NAMES = ("a001", "a002", "a015", "bus", "prune")
# Two lanes run in parallel threads: a long A001 ingest (up to RUN_TIMEOUT_SEC) must not delay the
# 15-minute A015 poll past its stale window. Each lane owns disjoint state keys.
LANES = {"slow": ("a002", "a001"), "fast": ("a015", "bus", "prune")}


def load_bus_config(path: Path | None = None) -> dict:
    try:
        raw = json.loads(Path(path or BUS_CONFIG_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    return {**_BUS_DEFAULTS, **(raw if isinstance(raw, dict) else {})}


A015_EVERY_MIN = int(load_bus_config()["a015_every_min"])


def log(msg: str) -> None:
    line = f"{datetime.now(UTC).isoformat(timespec='seconds')}  {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def run(args: list[str], label: str, timeout: int = RUN_TIMEOUT_SEC, cwd: Path = REPO) -> bool:
    """Run one agent command; log the outcome, never raise into the loop.
    True only when it exited 0 — a non-zero exit, timeout or crash is a failure."""
    log(f"RUN {label}: {' '.join(args)}")
    try:
        p = subprocess.run([PY, "-m", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)
        tail = (p.stdout or p.stderr or "").strip().splitlines()
        log(f"  {label} exit={p.returncode}" + (f" | {tail[-1]}" if tail else ""))
        return p.returncode == 0
    except subprocess.TimeoutExpired:
        log(f"  {label} TIMEOUT after {timeout}s")
    except Exception as exc:  # noqa: BLE001 - the loop must survive anything
        log(f"  {label} ERROR {type(exc).__name__}: {exc}")
    return False


def a001_ingest() -> bool:
    args = ["cli.main", "ingest", "--db", A001_DB, "--blocks", str(A001_BLOCKS)]
    if A001_TOKENS:
        args.append("--tokens")
    return run(args, "A001 ingest", cwd=A001_DIR)


def a002_scan() -> bool:
    return run(["agents.A002_News_Intelligence.cli", "scan"], "A002 scan")


def a015_poll() -> bool:
    """Poll the configured exchanges (explicit --exchange list: A015's default --limit 2 would cut it)."""
    args = [A015_CLI, "poll", "--partial-ok"]   # one unreachable exchange must not fail the whole job
    for exchange in load_bus_config()["a015_exchanges"]:
        args += ["--exchange", exchange]
    return run(args, "A015 poll")


def bus_prune() -> bool:
    """Weekly retention: archive then delete old events (never past a consumer's cursor)."""
    return run(["bootstrap.prune", "--once"], "bus prune")


def bus_cycle() -> bool:
    """A015 facts -> bus (relay) -> brain (consume). Both always run; True only if both succeeded."""
    relayed = run(["bootstrap.relay", "--once"], "bus relay")
    consumed = run(["bootstrap.consume", "--once"], "bus consume")
    return relayed and consumed


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

def _fresh_state() -> dict:
    state: dict = {"events": {}, "heartbeat": None}
    for name in JOB_NAMES:
        state.update({f"{name}_last": None, f"{name}_fails": 0, f"{name}_retry_at": None})
    return state


def load_state() -> dict:
    """Saved state over fresh defaults (so older state files gain new keys). A corrupt
    file is set aside as state.json.corrupt-<time>, not silently overwritten."""
    state = _fresh_state()
    try:
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("state is not a JSON object")
        state.update(raw)
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as exc:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        log(f"  state load ERROR {exc} — keeping the bad file as .corrupt-{stamp}, starting fresh")
        try:
            os.replace(STATE_FILE, STATE_FILE.with_name(f"{STATE_FILE.name}.corrupt-{stamp}"))
        except OSError:
            pass
    return state


def save_state(state: dict) -> None:
    """Write to a temp file then os.replace, so a crash mid-write cannot truncate state."""
    tmp = STATE_FILE.with_name(f"{STATE_FILE.name}.{threading.get_ident()}.tmp")   # one per thread: both lanes save
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(5):   # ponytail: the other lane may add an event key mid-dump; retry instead of locking
            try:
                payload = json.dumps(state, indent=2)
                break
            except RuntimeError:
                continue
        else:
            raise OSError("state changed under every dump attempt")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, STATE_FILE)
    except OSError as exc:
        log(f"  state save ERROR {exc}")
        tmp.unlink(missing_ok=True)


def acquire_lock(path: Path | None = None):
    """Hold an exclusive OS lock on the lock file for the process lifetime (released by the
    OS on exit or crash, so no stale-PID cleanup). Returns the open file, or None if another
    supervisor already holds it."""
    path = path or LOCK_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "a+")
    try:
        fh.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return None
    return fh


def is_stale(state: dict, now: datetime) -> bool:
    """True when the supervisor has not ticked recently (or never has). With per-lane heartbeats, ANY
    stale lane makes it stale: a live fast lane must not hide a dead A001/A002 lane."""
    beats = [state.get(f"heartbeat_{lane}") for lane in LANES if state.get(f"heartbeat_{lane}")]
    beats = beats or [state.get("heartbeat")]
    for beat in beats:
        if not beat or (now - datetime.fromisoformat(beat)).total_seconds() > HEARTBEAT_STALE_SEC:
            return True
    return False


def backoff_sec(fails: int, rnd=random.random) -> float:
    """Capped exponential backoff with equal jitter: half fixed, half random."""
    delay = min(BACKOFF_CAP_SEC, BACKOFF_BASE_SEC * 2 ** (fails - 1))
    return delay / 2 + rnd() * delay / 2


def _due(last_iso: str | None, every_min: int, now: datetime) -> bool:
    if not last_iso:
        return True
    return now - datetime.fromisoformat(last_iso) >= timedelta(minutes=every_min)


def _retry_ok(state: dict, name: str, now: datetime) -> bool:
    retry_at = state.get(f"{name}_retry_at")
    return not retry_at or now >= datetime.fromisoformat(retry_at)


def _record(state: dict, name: str, ok: bool, clock) -> None:
    """Stamp a job done only on success; on failure schedule a backed-off retry."""
    if ok:
        state[f"{name}_last"] = clock().isoformat()
        state[f"{name}_fails"] = 0
        state[f"{name}_retry_at"] = None
        return
    fails = state.get(f"{name}_fails", 0) + 1
    state[f"{name}_fails"] = fails
    state[f"{name}_retry_at"] = (clock() + timedelta(seconds=backoff_sec(fails))).isoformat()
    log(f"  {name} FAILED ({fails}x in a row) — retrying after backoff")


def fire_event_pair(state: dict) -> bool:
    """Both agents together — the event moment is worth an on-chain + news look.
    True if at least one of them succeeded."""
    a001_ok = a001_ingest()
    a002_ok = a002_scan()
    return bool(a001_ok or a002_ok)


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
            if fire_event_pair(state):   # a pair where both agents failed does not count
                ev["runs_done"] += 1
            ev["next_run"] = (now + timedelta(minutes=EVENT_GAP_MIN)).isoformat()


def tick(state: dict, now: datetime, clock=lambda: datetime.now(UTC), lane: str | None = None) -> None:
    """One pass of a lane (all jobs if ``lane`` is None): run what is due, stamp the heartbeat. The slow
    lane also watches events (A002 first — events depend on it). ``clock`` reads the time after a job
    finishes; ``now`` decides what is due."""
    jobs = (("a002", A002_EVERY_MIN, lambda: a002_scan()),
            ("a001", A001_EVERY_MIN, lambda: a001_ingest()),
            ("a015", A015_EVERY_MIN, lambda: a015_poll()),
            ("bus", BUS_EVERY_MIN, lambda: bus_cycle()),
            ("prune", PRUNE_EVERY_MIN, lambda: bus_prune()))
    if lane:
        state[f"heartbeat_{lane}"] = clock().isoformat()   # alive before the (possibly long) jobs run
    for name, every_min, job in jobs:
        if lane is not None and name not in LANES[lane]:
            continue
        if _due(state[f"{name}_last"], every_min, now) and _retry_ok(state, name, now):
            ok = job()
            _record(state, name, ok, clock)
            if ok and name == "a002":
                refresh_events(state, clock())
    if lane in (None, "slow"):
        process_events(state, clock())
    state["heartbeat"] = clock().isoformat()
    if lane:
        state[f"heartbeat_{lane}"] = state["heartbeat"]


def status() -> int:
    """`python live/supervisor.py --status`: 0 when running with a fresh heartbeat, else 1."""
    held = acquire_lock()
    running = held is None
    if held:
        held.close()
    state = load_state()
    stale = is_stale(state, datetime.now(UTC))
    print(f"supervisor: {'running' if running else 'NOT running'}"
          f" · heartbeat {state.get('heartbeat') or 'never'}{' (STALE)' if stale else ''}")
    return 0 if running and not stale else 1


def main() -> None:
    lock = acquire_lock()
    if lock is None:
        log("another supervisor already holds the lock — exiting")
        return
    log("=" * 60)
    log(f"026 supervisor start · A001 every {A001_EVERY_MIN}m · A002 every {A002_EVERY_MIN}m · py={PY}")
    state = load_state()

    # PC-on refresh: make both jobs due now (A002 first, then A001), whatever the last stamps say.
    # "jab bhi PC open karu -> rescan chalu."
    log("startup refresh (step by step)")
    for name in JOB_NAMES:
        state[f"{name}_last"] = None
        state[f"{name}_retry_at"] = None

    slow = threading.Thread(target=_lane_loop, args=(state, "slow"), daemon=True, name="lane-slow")
    slow.start()
    _lane_loop(state, "fast")   # the main thread runs the fast lane; Ctrl+C lands here


def _lane_loop(state: dict, lane: str) -> None:
    while True:
        try:
            tick(state, datetime.now(UTC), lane=lane)
            save_state(state)
        except Exception as exc:  # noqa: BLE001 - never let a lane die
            log(f"LOOP ERROR ({lane}) {type(exc).__name__}: {exc}")
        time.sleep(TICK_SEC)


if __name__ == "__main__":
    if "--status" in sys.argv:
        sys.exit(status())
    try:
        main()
    except KeyboardInterrupt:
        log("supervisor stopped (KeyboardInterrupt)")
