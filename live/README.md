# 026 live supervisor

Keeps the fleet's data fresh so the dashboard shows live-ish data instead of a
frozen snapshot. Pure local orchestration — it just runs the agents' own CLIs on
a schedule; it adds no new services and writes no agent data itself.

## What it does

- **On start** (i.e. every time you turn the PC on and it launches): one
  step-by-step refresh — A002 news scan, then A001 chain ingest.
- **Then on a schedule:** A001 ingest every **30 min**, A002 scan every **2 hours**.
- **Event watch:** after each A002 scan it asks A002 for upcoming *scheduled*
  events in the news (a meeting/launch/unlock with an explicit time). At each such
  time it runs **both** agents **twice, 5 minutes apart**.

State lives in `live/state.json` (gitignored) so a restart resumes without
repeating work or re-firing past events; activity is logged to
`live/supervisor.log`.

## Run it

Once, in a terminal:

```bash
python live/supervisor.py
```

Hidden (no console window):

```bash
wscript start-live.vbs
```

**Auto-start when you log in:** press `Win+R`, type `shell:startup`, Enter, and
drop a shortcut to `start-live.vbs` in that folder. Now the fleet refreshes on
every login, and stops when the PC is off — exactly as intended.

Stop everything (dashboard, T01, supervisor) with `stop-026.bat`.

## Event-bus jobs (Phase 1, 2026-10-28)

Two more jobs run on the same tick, reusing the retry/backoff/lock below. Config: `config/bus.json`.

- **A015 poll** every `a015_every_min` (15) minutes for the configured exchanges
  (`binance, bybit, coinbase, okx`) — one `fetch_markets` call each, network only, no API keys.
  Writes `memory/event_log/` and `memory/poll_status.json`.
- **Bus cycle** every 5 minutes: `python -m bootstrap.relay --once` (A015 facts -> `data/bus/bus.db`,
  source health, stale-source events) then `python -m bootstrap.consume --once` (-> persistent brain).
- Check it: `python -m bootstrap.bus_stats` (exit 1 on a parked event or a stale source).
- The **first** A015 poll compares against the old snapshots on disk, so it can publish a burst of
  events covering the whole gap since they were taken (each event states that window).

## Reliability (hardened 2026-10-28)

- **Single instance:** an OS lock on `live/supervisor.lock` — a second launch logs and exits.
- **Failures are failures:** a job counts as done only when its command exits 0. A failed or
  timed-out job is **not** stamped; it retries with capped exponential backoff + jitter
  (1 min → 30 min cap) instead of waiting a full cadence or hammering every tick.
- **State is crash-safe:** `state.json` is written atomically; a corrupt file is kept as
  `state.json.corrupt-<time>` instead of being silently reset.
- **Heartbeat:** every tick stamps `heartbeat` in `state.json`. Check on demand:

```bash
python live/supervisor.py --status
```

  Exit 0 = running with a fresh heartbeat; exit 1 = not running or stale.

## Tuning (top of `supervisor.py`)

- `A001_EVERY_MIN` / `A002_EVERY_MIN` — cadence.
- `A001_BLOCKS` (default 60) and `A001_TOKENS` (default off). Token-transfer
  fetching is very slow on a free RPC key, so exchange-flow data refreshes only
  when you run a token ingest by hand. With a paid RPC key, raise `A001_BLOCKS`
  and set `A001_TOKENS = True` to keep flows and head-tracking current.

## Known limits

- On a free Alchemy key A001 cannot fully keep pace with Ethereum's head
  (~150 blocks/30 min); it advances steadily but lags. Raise the block count or
  add RPC quota to close the gap.
- Event detection is a best-effort heuristic (see
  `agents/A002_News_Intelligence/intelligence/events.py`): it catches explicit
  dates/times, misses vague phrasing, and can occasionally misfire.
