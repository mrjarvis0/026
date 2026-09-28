# 026 — Operator Console (dashboard/frontend)

Next.js 16 (App Router) · Tailwind v4 · react-three-fiber · motion.

```bash
npm install
npm run dev      # http://localhost:3000
npm run build
```

- **Pages** are built one at a time. Live: `/` (026 home), `/narratives` (A002 news by
  topic × verdict), `/agents?id=A001` (full manifest contract per agent), `/sentinel`
  (conformance scan + gate simulator), `/trace` (send rounds through the real bus, read
  the trace), `/orchestrator` (command console + what the orchestrator can do today),
  `/brain` (memory contract + access checker), `/onchain` (A001 chain data), `/desk` (T01
  trading desk). All nine pages are built.
- `/desk` needs T01 running: `python -m uvicorn backend.main:app --app-dir
  agents/T01_Smart_Binance_Intelligence --host 127.0.0.1 --port 8000` from the repo root
  (or the `t01` entry in `.claude/launch.json`). Override the address with `T01_URL`.
- `/sentinel` shells out to the repo's Python (`python -m security.sentinel scan --json`
  and `security.sentinel.gate.check_action`) — read-only, fixed commands, inputs validated
  against the registry. Override the interpreter with `PYTHON`.
- **Data** comes from the repo, never hand-typed: `lib/fleet.ts` reads
  `config/agents/registry.yaml` + every `agents/*/agent.yaml`; `lib/narratives.ts` opens
  A002's `a002.db` **read-only** (`node:sqlite`). Repo root = `../..`, override with
  `FLEET_ROOT`. Refresh news with `python -m agents.A002_News_Intelligence.cli scan`.
- **Design system** lives in `app/globals.css` (`@theme` tokens). Build maturity is an
  ordinal one-hue ramp; status colors (good/warning/serious/critical) are reserved
  for real states and always ship with an icon + label.
- Read `AGENTS.md` here before touching Next.js APIs — this version differs from
  older training data; version-matched docs are in `node_modules/next/dist/docs/`.
