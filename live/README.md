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
