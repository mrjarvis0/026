# Slice 2 design — T01 entry pause flags (A015 -> bus -> T01)

> **Status:** DRAFT, nothing built. T01 is the real-money agent, so this needs the operator's approval of the
> whole document before any code (AGENTS.md section 9, funds boundary). **Date:** 2026-10-29.
> **Builds on:** `2026-10-28-phase1-event-bus-design.md` (section 12, Slice 2), ADR-0005.
> **Operator decision already taken (2026-10-28):** T01 may act on A015 events at the `implemented` bar,
> **pause-only**. `[call]` marks my choices; change any you dislike.

## 1. Intent

When A015 sees a market leave an exchange (`a015.listing.delisted`) or go into HALT/BREAK
(`a015.market.status_changed`), T01 should stop opening **new** entries on that market. Nothing else changes.

## 2. Goals / non-goals / anti-goals

- **Goals:** a pause can only reduce what T01 does; every set/clear is traced and auditable; T01 stays a
  standalone service (no platform import); a broken flag path never makes T01 less safe than it is today.
- **Non-goals:** closing or adjusting open positions; touching exits, stops, sizing, the accuracy gate,
  `_guard`, credentials or the real-mode switch; any new way to *enable* trading; T03/T02.
- **Anti-goals:** a flag that silently blocks exits (traps a position); a flag that can enable or loosen
  anything; a missing/corrupt flag file stopping the bot; an unvalidated event acting without a trace.

## 3. Design

```
bus.db --a015.* events--> bootstrap/consumers/risk_flagger.py --atomic write--> data/risk/pause_flags.json
                                   |                                                  ^ read once per cycle
                                   +-- publishes system.risk.flag_set / flag_cleared (audit, causation_id)   |
                                                                                    T01 backend/safety/pause_flags.py
                                                                                    bot._cycle: skip BUY only
```

- **Contract = a file**, like A015's `event_log`: `data/risk/pause_flags.json`, versioned, written atomically
  by the platform consumer, read with stdlib `json` by T01. T01 imports nothing from `orchestrator`/`bootstrap`.
- **Flag record** (key = event subject, e.g. `market:binance:XYZ/USDT`): `{set_at, expires_at|null, reason,
  event_id, event_type, maturity}`.
- **Which events act** `[call]`: only `exchange == binance` (T01 trades Binance; its Kraken fallback is
  market-data only). `a015.listing.delisted` -> flag, **no expiry** (cleared by a later `a015.listing.new` for the
  same market or by the operator). `a015.market.status_changed` with `status_to` in {BREAK, HALT} -> flag,
  **expires after 24 h** unless renewed; `status_to == TRADING` clears it. A015 sees a delisting only after the
  market has left the list, so HALT/BREAK is the earlier, more useful signal.
- **Consumer:** `risk_flagger`, `min_maturity="implemented"` (the operator's bar), idempotent by `event_id`,
  runs in the existing bus cycle (`bootstrap.consume`), so no new process.
- **T01 side** (`backend/safety/pause_flags.py`, ~40 lines): `is_paused(exchange, symbol) -> (bool, reason)`,
  mtime-cached, ignores expired flags. `bot._cycle`: the entry condition becomes
  `allowed and not paused and signal.action == "buy"`; a blocked BUY logs `[PAUSED] ... (reason)` and is
  counted. **SELL and `check_exits` are untouched.** Kill-switch: config `PAUSE_FLAGS_ENABLED` (default true).
- **Failure modes (all fail toward today's behavior, never toward more risk):** file missing -> no flags;
  corrupt/unreadable -> no flags + one warning per minute; expired -> ignored; consumer dead -> existing flags
  stay (a pause is never lost), and `bus_stats` already shows the consumer lag.
- **Operator control:** `python -m bootstrap.flags list | clear <subject> | set <subject> --hours N` (set is
  for tests/drills; every change is traced and emits the audit event).
- **Evidence standard:** the flag carries the triggering `event_id` and its `maturity` (`implemented`) so the
  dashboard can say *why* and *how sure*. No flag is ever described as an alert.

## 4. Slices (each independently shippable)

- **S2a — platform side, T01 untouched:** `risk_flagger`, `pause_flags.json` writer, `bootstrap.flags` CLI,
  audit events + schemas (`system.risk.flag_set/flag_cleared`). Observe it on live data first (flags appear,
  nothing reads them).
- **S2b — T01 reader:** `pause_flags.py`, the one-line cycle condition, config knob, tests; then a paper-mode
  soak before real mode could ever see it.

## 5. Tests (TDD)

Flagger: delisted sets a no-expiry flag; BREAK sets 24 h; TRADING and `listing.new` clear; non-binance ignored;
redelivered event is idempotent; file written atomically; audit event published with `causation_id`.
T01: paused symbol blocks BUY only; SELL and exits run while paused; expired flag ignored; missing and corrupt
file -> not paused; other symbols unaffected; knob off -> never paused; a paused entry is logged and counted.
Architecture: T01 imports no platform module (existing rule, all agents).

## 6. Open questions

1. TTL for HALT/BREAK: 24 h OK, or longer?
2. Should the T01 desk page show paused markets (small follow-up in the dashboard)?
3. Approve S2a now and S2b only after S2a has run on live events for a while? *(my recommendation)*

## 7. Self-critique

Fragile: a file contract means T01 reads stale data if the consumer is down (mitigated: flags persist and
`bus_stats` shows lag). Assumed: A015's binance symbol format equals T01's ccxt format (`XYZ/USDT` on both).
Untested: everything (design). T01 trading semantics beyond the entry condition were not changed in this design.
