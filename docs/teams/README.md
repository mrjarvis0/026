# 026 Teams — fleet ko chaar teams me baantna

> **Date:** 2026-10-28 · **Type:** design + research docs (koi code, registry ya folder-rename nahi) · **Tag:** BUILD-NEW (doc)
> **Status:** structure operator ne approve kiya (2026-10-28). **Team ke naam aur series-letter `R` provisional hain** — review me badal sakte hain.
> **Supersedes (in part):** [`docs/manual/06-agents.md`](../manual/06-agents.md) §1 ke "teen fleet layers" — dekho [ADR-0006](../adr/ADR-0006-fleet-teams.md).
> **Method:** repo + PROJECT_STATE + 10-28 audit padhkar; chhote claims aaj grep/read se dobara verify hue ([gap register](06-gap-register.md) me ✅ se mark). Kuch chalaya nahi.

## Seedha nateeja

026 me ab 21 agent folders hain, par "kaun kis kaam ka hai" ka saaf ghar nahi. Isse teen asli dikkatein bani hain:

1. **A-series me do alag kisam ke agents mile hain.** Kuch internet se raw jankari lete hain (collectors), kuch dusron ke output se derive karte hain (analysts). Dono ke rules alag hone chahiye.
2. **A → T ka koi contract nahi.** 8 manifests me sirf A015 `produces` declare karta hai, `consumes` kisi me nahi. T01 ko A-series ka ek bhi signal nahi milta.
3. **Agents ki dekh-bhaal 5 jagah bikhri hai** (supervisor, bus, sentinel, bootstrap, dashboard) aur uska koi owner nahi.

Chaar teams yahi theek karti hain: **A** jankari lata hai, **R** use samajhta hai, **T** use istemal karta hai, **X** in sabki dekh-bhaal karta hai.

## 1. Chaar teams

| Team | Series | Kaam | Paisa chhuta hai? | Team Topologies role |
|---|---|---|---|---|
| **Intelligence Team** | `A` | external source se raw jankari, read-only. Facts, advice nahi. | Nahi | stream-aligned (har agent ek data domain end-to-end) |
| **Analysis Bureau** | `R` (Research/Reasoning) | dusre agents ke output / stored data se derive: TA, volatility, risk, arbitrage, correlation. Read-only, advisory. | Nahi | complicated-subsystem (specialist, Desk ko X-as-a-Service) |
| **Trading Desk** | `T` | A + R ka sahi istemal: decide aur act (gated). | **Haan, sentinel gate se** | stream-aligned |
| **Control Tower** | `X` | steward: orchestration design, pipeline, comms/handoff, rules, failure, self-improvement, registry. | Nahi | platform + enabling |

```
            +--------------------- X  Control Tower (steward) ----------------------+
            |  orchestration | pipeline | comms+handoff | rules | failure | evolve | registry |
            +-- dekhta, naapta, sudharta hai - kisi ko chalata nahi, trade nahi karta ---+
                  ^                  ^                    ^
 internet ->  A  Intelligence  ->  R  Analysis  ->  T  Trading Desk -> (sentinel gate) -> exchange
                  \_______ hard-stop facts (halt / delisting) seedha _______/
```

**"Control Tower" naam kyun:** air-traffic control khud plane nahi udata; wo plane ko takrane ya kho jaane se bachata hai. X ka kaam yahi hai.

## 2. Kaun si team? — 4 sawal (order me)

1. **Paisa ya order chhuta hai?** → **T**. (`execution_enabled: true` ya order path.)
2. **External source se raw leta hai?** → **A**.
3. **Dusre agents ka output / stored data se derive karta hai, read-only?** → **R**. (Agar wo khud external fetch karne lage, to wo R nahi, A hai.)
4. **Baaki agents ko chalata, naapta ya sambhalta hai?** → **X**.

Naam mat dekho. Manifest ke `execution_enabled` aur inputs dekho.

| Misaal | Jawab | Kyun |
|---|---|---|
| A015 (CCXT poll-diff) | A | exchange se raw fetch, read-only |
| A012 Risk (advisory) | R | agents ke output + market data se derive; order nahi |
| T02 swarm simulator | T | kabhi trade nahi karta, par ek trade event ka reaction decide karne me madad karta hai — decision-support, Desk ke andar |
| T03 | T | scanner (analysis) + scalper (execution) ek hi hub me; execution flag ki wajah se Desk |
| `live/supervisor.py` | machinery, X ka steward-target | timer par jobs chalata hai; uski design/monitoring X03/X05 ka kaam |
| A002 ka internal cross-asset correlation | A ke andar | news se bandha; general correlation R05 ka kaam, overlap flag hai ([02](02-analysis-bureau.md)) |

## 3. Steward vs machinery

Operator ka faisla: **maujooda platform actors alag rehte hain** — X unko replace nahi karta.

| | Machinery (platform actors) | Steward (X team) |
|---|---|---|
| Kaam | **execute**: bus, gate, brain, console | **design, monitor, tune, repair** unhe |
| Kaun | `orchestrator`, `sentinel`, `librarian`, `operator-io` | `X01`–`X07` (proposed) |
| Trust | 3 (platform) / 2 | 1 se shuru, tests + evidence se 2 |
| Bypass | — | **sentinel ko bypass nahi**; orchestrator ko replace nahi |

Misaal: `sentinel` rule **enforce** karta hai; `X04 Rulesmith` rule **design/version/test** karta hai. `orchestrator` playbook **chalata** hai; `X01 Conductor` playbook **likhta** hai.

## 4. Har agent ek hi team me

| ID | Naam | Team | Domain | Haal (2026-10-28) |
|---|---|---|---|---|
| `A001` | Blockchain Intelligence | A | on-chain | substantial; read-only bus adapter |
| `A003` | DeFi Flow | A | on-chain | README-only |
| `A016` | Protocol/Infrastructure Event | A | on-chain | README-only |
| `A018` | Token Unlock/Vesting | A | on-chain | README-only |
| `A002` | News Intelligence | A | news / social | substantial; adapter + brain view; bus relay nahi |
| `A004` | Social Sentiment | A | news / social | README-only; borderline (AGENTS.md §3 me "sentiment fusion") |
| `A005` | Market Data | A | market / exchange | README-only — **R aur T dono ka critical path** |
| `A015` | Exchange Listing/Delisting | A | market / exchange | partial; bus par pehla producer |
| `A017` | Derivatives/Leverage | A | market / exchange | README-only; borderline (derived signals) |
| `A006` | Macro/Econ | A | macro / public | manifest-only, code nahi |
| `A007` | Public-Record | A | macro / public | partial; ingestion MOCK-only |
| `A008` | Earnings Calendar | A | macro / public | README-only |
| `A011` | Reserved | A | TBD | README-only, domain tay nahi |
| `R01` ← `A009` | Technical Pattern | R | analysis | README-only; folder abhi `A009_*` |
| `R02` ← `A010` | Volatility Regime | R | analysis | README-only; folder abhi `A010_*` |
| `R03` ← `A012` | Risk Assessment (advisory) | R | analysis | README-only; folder abhi `A012_*` |
| `R04` ← `A013` | Arbitrage Detection | R | analysis | README-only; folder abhi `A013_*` |
| `R05` ← `A014` | Correlation | R | analysis | README-only; folder abhi `A014_*` |
| `T01` | Smart Binance Intelligence | T | spot trading | substantial; triple-gated real path; kernel-wired nahi |
| `T02` | Swarm Trading Intelligence | T | decision-support | partial; kabhi trade nahi |
| `T03` | Strategy Intelligence Hub | T | strategy + futures testnet | partial; testnet-only |
| `X01`–`X07` | Control Tower roster | X | steward | **sab planned**, kuch nahi bana — [04](04-control-tower.md) |
| `X08+` | reserved | X | "baaki dekh lenge" | — |

Platform actors (`orchestrator`, `sentinel`, `librarian`, `operator-io`) isse bahar hain — upar §3.

**Code ki sachchai:** 18 A-slots me sirf 4 me code hai (A001, A002, A007, A015); A006 ka sirf manifest hai; baaki 13 sirf README hain. Isliye ye docs ek **structure aur contract** tay karte hain, bani hui team ka description nahi.

## 5. Team Topologies se mapping, aur Conway ka kaanoon

[Fowler](https://martinfowler.com/bliki/TeamTopologies.html) ke saar ke hisaab se: team ka dhancha software ke dhanche ko dhalta hai (Conway), aur platform ka asli fayda stream-aligned teams ka **cognitive load** ghatana hai. 026 me iska matlab:

- **A aur T stream-aligned** hain — har agent apna kaam end-to-end own karta hai.
- **R complicated-subsystem** hai — risk/volatility/correlation gehri specialist cheezein hain; Desk ko inke andar nahi ghusna padta, wo bas output leta hai (X-as-a-Service).
- **X platform + enabling** hai — bus/gate/scheduler service dete hain; Evolver agents ko seekhne me madad karke peeche hat jata hai.
- **Abhi ka load operator + build session par hai.** X ke bina har naya agent apni retry, apna breaker, apna health check phir se banata hai — T01 ka `circuit_breaker.py` aur T03 ka `RiskEngine` iska saboot hain (dono local, dono alag).

## 6. Team ke beech ke niyam

1. **Agents ek-doosre ko seedha call nahi karte.** Sab bus se ([AGENTS.md](../../AGENTS.md) §5). Contract X02 design karta hai.
2. **Data neeche behta hai: A → R → T.** T kabhi A ya R me nahi likhta; T sirf *outcomes* X ko bhejta hai.
3. **A → T seedha sirf hard-stop facts ke liye** (halt, delisting, exploit outflow) — aur wo bhi sirf "naye entry pause" tak. Kabhi auto-trade nahi.
4. **R ka confidence ≤ uske sabse kamzor input ka** ([AGENTS.md](../../AGENTS.md) §4). R apna raw external fetch nahi karta; wo karne lage to A hai.
5. **Execution sirf T me**, aur wo bhi sentinel gate se ([ADR-0002](../adr/ADR-0002-gated-execution-charter.md)). A, R, X ke manifest me `execution_enabled: false`.
6. **X na market data fetch karta hai na trade karta hai.** X sirf agents ke stores/events/metrics padhta hai, aur apna kaam `ops.*` namespace + `x0N.*` events me likhta hai (naya namespace — proposal).
7. **X kisi aur agent ka code, rule ya param seedha nahi badalta** — ya to allowlisted auto-lane ([04](04-control-tower.md) §3), ya proposal → operator.
8. **Naya agent:** pehle §2 ka 4-sawal test, phir manifest me `produces`/`consumes`, phir build.

## 7. Abhi kya hai, kya sirf proposal

| Cheez | Haal |
|---|---|
| A→bus→librarian→brain ka ek raasta (A015) | ✅ chalta hai ([ADR-0005](../adr/ADR-0005-sqlite-event-bus.md)) |
| `produces` declare + sentinel `contracts` check | ✅ (sirf A015) |
| Teams, `R`/`X` series, `team:` manifest field | ⬜ proposal — sentinel ka `_ROW` regex abhi `[AT]` hi parse karta hai |
| X ka koi bhi agent | ⬜ koi nahi bana |
| R folders ka rename (A009→R01 …) | ⬜ alag go-ahead par |

## 8. Aage padhein

[01 Intelligence Team](01-intelligence-team.md) · [02 Analysis Bureau](02-analysis-bureau.md) · [03 Trading Desk](03-trading-desk.md) · [04 Control Tower](04-control-tower.md) · [05 Handoffs aur contracts](05-handoffs-and-contracts.md) · [06 Gap register](06-gap-register.md) · [07 Research](07-research.md)
