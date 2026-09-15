# 026 Manual — Index

> The handbook for 026. Hand this folder to anyone who needs to understand the
> project — they should be able to read it top to bottom and know what 026 is,
> how it is built, how it works, where its data comes from, and how it is secured.
>
> **This manual is living.** As the project grows, its sections grow with it. The
> rule (from `AGENTS.md` §9.7): whenever a file is created, moved, or given a new
> role, the matching manual section is updated in the same session.

---

## How to read this manual

Read in order the first time. After that, jump to the section you need.

| # | Section | Read it to learn… | Status |
|---|---------|-------------------|--------|
| 01 | [Overview](01-overview.md) | What 026 is, in plain language, and why it exists | ✅ written |
| 02 | [Structure](02-structure.md) | Every folder (files added as built) — what lives where | ✅ folders done |
| 03 | Architecture | How the pieces fit and how data flows through them | ⬜ planned |
| 04 | [Security](04-security.md) | Trust levels, the execution boundary, secrets, the sentinel | ✅ written |
| 05 | [Data sources](05-data-sources.md) | Where 026's data comes from, and how the `sources/` registry governs it | ✅ written |
| 06 | [Agents](06-agents.md) | The fleet layers (Intelligence / Execution / Platform), which agent sits where, and how to add one | ✅ written |
| 07 | [Glossary](07-glossary.md) | Every 026 term defined in one place | ✅ written |
| 08 | Manual log | What changed in the manual, and the rules for updating it | ⬜ planned |

*Sections 03 and 08 are planned and will be added one at a time — no rush.*

---

## The one thing to remember

> **An agent may not assert what its evidence cannot license.**

Everything in 026 — every folder, every rule, every design choice — exists to keep
that promise. If a section ever seems over-engineered, this is why: the system is
built to say *"cannot be determined"* instead of a confident wrong answer.

---

## Status legend (used throughout the manual)

| Mark | Meaning |
|------|---------|
| ✅ built | Exists, works, and is verified by a command recorded in `BUILD_LOG.md` |
| 🟦 partial | Some code exists; not complete or not verified end-to-end |
| ⬜ planned | Designed and documented here, but not yet built (0 bytes / empty) |
| 🔒 invariant | A rule that must always hold; enforced in code + tests |

At genesis (2026-09-04) almost everything is ⬜ planned. That is expected and
honest — the manual documents the design first, and each section flips marks to
✅ as the build sessions make them real.
