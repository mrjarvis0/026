# 01 · Overview

[← Index](README.md) · [Next: Structure →](02-structure.md)

---

## What 026 is, in one line

026 is an **operating system for a fleet of intelligence agents** — software that
watches sources, reasons over what it sees, reports only what its evidence can
prove, and — once proven — can act on that evidence through a strictly gated,
risk-limited trading layer.

## The plain-language version

Imagine several specialists, each an expert in one thing:

- one watches **blockchains** (large transfers, money leaving wallets, unusual flows),
- one watches the **news and social feeds** (rumors, coordinated hype, fake stories),
- more can be added later.

Each specialist works carefully: it writes down where every fact came from, and it
refuses to state anything it cannot back up. If it doesn't have enough information,
it says *"cannot be determined"* — it does not guess.

026 is the **office** these specialists work in. It gives them:

- a **shared memory** (a "brain") so one specialist's notes help another,
- a **manager** (the orchestrator) that hands out work and combines the answers,
- a **security guard** (the sentinel) that makes sure no one breaks the rules,
- a **front desk** (the dashboard) where you talk to the whole team at once.

The special thing 026 can do that a single specialist cannot: **connect the dots
across specialists.** If the news-watcher hears a rumor that a project was hacked,
*and* the blockchain-watcher sees money suddenly draining from that project's
wallet, 026 links the two into one finding — while still keeping each half's
evidence separate and honest.

## Why it exists

Most tools that "analyze" data will happily give you a confident answer even when
they have no real basis for it. That confident-but-wrong answer is worse than no
answer — you act on it and get hurt. 026 is built the opposite way: **evidence
first, confidence second.** It is designed for questions where being wrong is
expensive, and where "I don't have enough to say" is a genuinely useful reply.

## What 026 will and will not do

**It will:**
- observe sources and store what it sees, with the source and time attached,
- reason over that stored evidence and report findings with their provenance,
- combine findings across agents into correlated hypotheses,
- predict market moves and tell you plainly how confident it is, and what it could not determine,
- and, when explicitly enabled, act on those findings through a **gated execution layer** — off by default; paper-validated, risk-limited, human-approved.

**It will never (these are hard rules — see [Security](04-security.md)):**
- 🔒 place a trade or move funds **outside** the gated execution layer — nothing fires silently, without risk limits, or without passing its gates,
- 🔒 present a prediction as a certainty, or hide how much it could not determine,
- 🔒 alert on a detector whose error rate has not been measured,
- 🔒 state a "nothing happened" conclusion without proving it actually looked.

## Where 026 is right now

**Genesis.** The structure and this manual exist; the working code does not yet.
The honest, current state is always in [`PROJECT_STATE.md`](../../PROJECT_STATE.md).
The history of how it got here is in [`BUILD_LOG.md`](../../BUILD_LOG.md).

---

[← Index](README.md) · [Next: Structure →](02-structure.md)
