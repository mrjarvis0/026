# 05 · Handoffs aur contracts — teams ke beech kya, kaise aur kaun zimmedar

[← Control Tower](04-control-tower.md) · [Teams](README.md) · *Next: [Gap register](06-gap-register.md)*

> **Is doc ka sawal:** jab ek agent/team doosre ko kuch deti hai, to *kya* jaata hai, *kis raaste*, *kitna bharosa* ke saath, aur *aage kaun zimmedar* hai. Naya message-format **nahi** bana raha — jo hai (bus envelope + `Message`) uspar map kar raha hoon.

## 1. Do duniya: events (facts) aur messages (requests)

| | Events | Messages |
|---|---|---|
| Kya | **facts**, async, durable (`data/bus/bus.db`) | request/response, sync, trace in-memory (+ persisted `trace`) |
| Code | `orchestrator/event_bus/envelope.py`, `store.py` | `orchestrator/event_bus/message.py`, `bus.py` |
| Niyam | *"Events carry facts, never commands."* (`envelope.py` docstring) | non-read message ko `action` declare karna padta hai, warna deny |
| Kaun use karta hai | relays (`bootstrap/relays/`), consumers | orchestrator, dashboard console |

Handoff ke saare design isi vibhajan par tike hain: **A→R→T ka data events me jaata hai; kaam ka request messages me.**

## 2. Chaar kisam ke handoff

| # | Kisam | Kaun → kaun | Aaj kya hai | Kya chahiye |
|---|---|---|---|---|
| 1 | **Intel handoff** | A → R / T (facts) | events table; sirf A015 → librarian chalta hai | `consumes` declare; R aur T consumers |
| 2 | **Human handoff** | gate / X → operator | `approvals` table (`store.py:47`, `pending_approvals :384`); gate `held` | dashboard approvals page; proposals ka `kind` |
| 3 | **Task handoff** | orchestrator → agent | `Message`/`Response`; statuses `ok·denied·held·error·degraded·timeout·no_handler` | persisted task state, deadline, ack |
| 4 | **Session handoff** | build session → build session | `PROJECT_STATE.md` (overwrite) + `BUILD_LOG.md` (append) + "Next session should start at" | ✅ ye chalta hai |

## 3. Team-to-team contracts

| Raasta | Transport | Kya jaata hai | Guarantee | Haal |
|---|---|---|---|---|
| **A → R** | events `a0NN.<noun>.<verb>` | facts + `coverage` + 3 timestamps | at-least-once, consumer dedup; `min_maturity` default `validated` | ⬜ R nahi bani |
| **A → T (hard-stop)** | events; Desk ka *pause flag* | sirf allowlist: `a015.market.status_changed` (HALT/BREAK), `a015.listing.delisted` | effect = **naye entry pause** — kabhi auto-trade nahi; resume = fact saaf ya operator | ⬜ Slice 2 (T01 pause flag) — **aur maturity gate se rukta hai, niche dekho** |
| **R → T (advisory)** | events `r0N.<noun>.<verb>` → **sentinel gate** → T | R03 ke risk numbers | gate enforce karta hai, T display/use | ⬜ |
| **T → X (outcomes)** | relay T ke DB se `t0N.decision.*`, `t0N.outcome.*` | licensing-evidence record + baad ka outcome ([03](03-trading-desk.md) §5) | T bus-unaware rehta hai ([ADR-0005](../adr/ADR-0005-sqlite-event-bus.md)) | ⬜ |
| **X → sab** | X-as-a-Service: bus, gate, scheduler | services; X ke events `x0N.*` | read-only on agents | ⬜ |
| **X → operator** | `approvals` queue | proposals (diff + evidence + eval result) | operator approve kare bina kuch nahi | ⬜ |

**A→T hard-stop par maturity gate ka asar (aaj verify hua):** `envelope.passes_maturity` ke hisaab se *plain fact* (koi `detector` block nahi) hamesha guzarta hai, par *detector event* ko `min_maturity` chahiye, aur consumers ka default `validated` hai. A015 ka relay har event par `"detector": {"id": kind, "maturity": …}` lagata hai (`bootstrap/relays/a015.py:79`), aur A015 manifest me paanchon detectors `implemented` hain — isliye A015 ke `status_changed`/`delisted` events `maturity: implemented` ke saath bus par hain. Librarian unhe isliye le paata hai ki wo jaanbujhkar `min_maturity="implemented"` par *recorder* hai (`consumers/librarian.py:39`). **Desk ka pause-consumer default `validated` par unhe skip kar dega** — yani A015 se hard-stop tab tak nahi chal sakta jab tak (a) detectors labelled backtest se `validated` na ho, ya (b) operator tay kare ki exchange-metadata ka status transition *observation* hai, heuristic nahi, aur relay use plain fact ki tarah de. (b) ek gate dheela karna hai, isliye operator ka faisla ([G-ORG-06](06-gap-register.md)). Isi tarah A001 ka DET-EXPLOIT-02 `implemented` aur muted hai — wo bhi pause nahi laga sakta.

**Dead-man switch alag cheez hai:** `system.source.stale` ek *platform* event hai (`source: SYS`, koi detector nahi) — wo maturity gate se guzarta hai. Isliye "A015 ka source stale → naye entry pause" bina detector validation ke bhi chal sakta hai; "A015 ne delisting dekhi → pause" nahi.

## 4. Handoff packet = maujooda envelope

| Packet ka hissa | Envelope field | Required? |
|---|---|---|
| kya/kaun | `event_id`, `type` (`^[a-z0-9]+(\.[a-z0-9_]+){2,3}$`), `schema_version`, `source`, `subject` | haan |
| kab | `observed_at` · `event_time`, `known_at` | `observed_at` haan; baaki optional (tz-aware UTC) |
| trace | `trace_id` | haan |
| epistemic | `coverage`, `evidence`, `untrusted` · `detector{maturity}`, `confidence` | `coverage`/`evidence`/`untrusted` haan |
| payload | `data` (schema `config/events/<type>.v<N>.yaml` se validate) | haan |

`source` authorized hota hai manifest ke `produces` se (`envelope.py:114`); platform types (`system.*`) sirf `SYS` publish kare. Untrusted payload me `action`/`command`/`tool` keys **banned** (`envelope.py:25`).

**Jo packet me abhi nahi hai** (proposal, envelope badle bina): `deadline`, `owner-after-handoff`/`ack`, `budget`. `Message` me `budget`, `trace_id`, `parent_id` pehle se hain; `deadline` aur `ack` task-handoff ke liye jodne honge ([G-X-08](06-gap-register.md)).

## 5. Task states (A2A se, sirf data model)

[A2A v1.0](07-research.md#a2a-mast-aur-baaki-audit-se) ke task states 026 par yun map hote hain (HTTP nahi, sirf state model):

| A2A state | 026 aaj | Proposal |
|---|---|---|
| `SUBMITTED` | `Message` bheja gaya | persisted task row |
| `WORKING` | handler chal raha | heartbeat |
| `INPUT_REQUIRED` | gate `held` → `approvals` row `pending` | ✅ sabse kareeb |
| `AUTH_REQUIRED` | — | single host par zaroorat nahi |
| `COMPLETED` | `Response` ok | — |
| `FAILED` | `error` / `timeout` / `degraded` | X05 incident |
| `CANCELED` | — | kill switch / operator |
| `REJECTED` | `denied` | — |

## 6. Handoff ke baad zimmedari — 5 niyam

1. **Bhejne wala tab tak owner jab tak receiver ack na kare;** ack ke baad receiver owner.
2. **Deadline tak ack nahi aaya → X05 incident**, silent drop nahi.
3. **Summary nahi, evidence refs jaayein.** Delegation boundary par jaankari ka sirf hissa transfer hota hai; summary provenance tod deti hai. (secondary research, [07](07-research.md#handoffs))
4. **Chain bounded:** `budget.calls` hops ko cap karta hai — "endless handoff" ka guard.
5. **Galat fact cascade na kare:** har hop maturity/coverage dobara label kare; R ka ceiling ≤ min(inputs); fusion kabhi average nahi ([AGENTS.md](../../AGENTS.md) §4).

## 7. Naye producer / consumer ki checklist

- [ ] manifest me `produces` / `consumes`, schema_version ke saath
- [ ] `config/events/<type>.v1.yaml` schema
- [ ] plain fact hai ya detector event (maturity)
- [ ] `coverage` + teen timestamp; natural key se `make_event_id`
- [ ] health/stale event (A015 wala pattern)
- [ ] `python -m security.sentinel scan` ka `contracts` check PASS
- [ ] e2e test: relay → bus → consumer ([`tests/integration/test_event_bus_e2e.py`](../../tests/integration/test_event_bus_e2e.py) jaisa)

## 8. Khule sawal

1. `consumes` ka exact syntax (type pattern `a015.*` jaisa, `type_matches` pehle se hai).
2. Proposals ke liye `approvals` table me `kind` column, ya alag table?
3. `deadline`/`ack` `Message` me, ya task-event type me?
