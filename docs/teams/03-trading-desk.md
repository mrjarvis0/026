# 03 · Trading Desk (`T`) — istemal karne wali team

[← Analysis Bureau](02-analysis-bureau.md) · [Teams](README.md) · *Next: [Control Tower](04-control-tower.md)*

> **Mission:** A ka fact aur R ka analysis lekar **decide aur act** karna — sahi tareeke se: har faisle ka sabut, har order sentinel gate se, aur "cannot be determined" par haath rok lena. T = decision layer; execution ek *flag* hai, team ki pehchaan nahi.

## 1. Desk ke niyam

| # | Niyam | Source |
|---|---|---|
| 1 | **Har action ka licensing evidence record.** Kaunsa signal, kin events (id + maturity + ceiling) ne license kiya, kaun-se veto laga, gate ne kya kaha, mode (paper/testnet/real). | [AGENTS.md](../../AGENTS.md) §0: *"No order is silent; each traces to its licensing evidence."* |
| 2 | **Paper by default.** Real sirf gate se, aur gate operator ka faisla hai. | [ADR-0002](../adr/ADR-0002-gated-execution-charter.md) |
| 3 | **Ek risk authority:** R03 advisory → sentinel gate. Local breakers last-resort backstop. | [02](02-analysis-bureau.md) §5 |
| 4 | **Sirf declared `consumes` se input.** Hard-stop facts (A015 halt/delisting) naye entry pause karte hain — auto-trade kabhi nahi. Par maturity gate lagta hai: A015 ke events abhi `implemented` hain, isliye content-based pause tab tak nahi jab tak validated ya plain-fact ka faisla na ho ([05 §3](05-handoffs-and-contracts.md)); *source-stale* pause (platform event) chal sakta hai. | [README](README.md) §6 rule 3 |
| 5 | **Outcomes X ko wapas** (prediction → result) — calibration ledger (X06) ke liye. | [04](04-control-tower.md) |
| 6 | **Stand aside:** "cannot be determined" ya chop → koi trade nahi. | T03 charter |
| 7 | **Desk agents bus-unaware rahte hain;** relay unke DB se events publish karta hai (A015 wala pattern). | [ADR-0005](../adr/ADR-0005-sqlite-event-bus.md) |

## 2. Roster

| Agent | Execution | Haal | Gate | Kernel-wired |
|---|---|---|---|---|
| `T01` Smart Binance | `execution_enabled: true` — **real** path, triple-gated | substantial; paper live; 53 tests | internal `_guard()` (`real_engine.py:51`): ≥70% accuracy over ≥50 trades **+** keys **+** operator enable | Nahi; `reads: []` |
| `T02` Swarm | `false` — sirf simulate | partial; 5 `.py` files | n/a | Nahi; namespace `market` (A015 `markets` likhta hai) |
| `T03` Strategy Hub | `true` — **sirf Binance Futures Testnet**, `armed=False` default | partial; 67 `.py` files; `runtime_verified: false` | `--arm` + `HUMAN_CONFIRM_TOKEN` | Nahi |

Fleet me aaj Desk ki **ek hi live link** hai: T03 → T01 soft veto (`T01 backend/bot.py:158-167`, sirf BUY entries par; `engine.py:102 apply_t03_veto`). A ya R ka koi signal Desk tak nahi pahunchta.

## 3. T-series ka trust tier — operator ka faisla (trust boundary)

Problem: [`06-agents.md`](../manual/06-agents.md) §4 pehle se kehta hai ki trust 2 ("scoped writes") order place karne ka dawa kam hai, aur trust 3 ("platform") T01 ke liye galat hai. Sentinel aaj T03 ko `level 2 not earned (no evidence.detectors) → capped to 1` karta hai, aur T01/T03 ke `execution_enabled: true` hone par execution scan unhe **skip** karta hai (`security/sentinel/checks/execution.py:9-10`: "gate not asserted").

| Option | Kya | Kaisa |
|---|---|---|
| **a** | naya trust level 4 sirf T ke liye | trust ek line me execution aur write-scope mila deta hai |
| **b (meri salah)** | **orthogonal `execution_tier` field** manifest me: `none` → `paper` → `testnet` → `real-gated`. `trust.level` write-scope hi rahe. | do alag sawal alag fields me; sentinel tier ke hisaab se alag check laga sakta hai |
| c | kuch nahi, har T agent khud gate kare (aaj ki haalat) | sentinel ko pata hi nahi T01 kitna dangerous hai |

**Ye proposal hai, faisla nahi.** [AGENTS.md](../../AGENTS.md) §9 ke hisaab se execution-gate/funds ki boundary par main akela nahi chunta. X04 Rulesmith ([04](04-control-tower.md)) isko design karega *jab operator option chun le*.

## 4. Teen-teen engines ka overlap

| Kaam | Kahan-kahan | Salah |
|---|---|---|
| **TA signal** | R01 (planned), T03 scanner (8 strategies, backtested), T01 `signals.py` | Desk ke andar execution-time signal rahe; R01 sirf tab bane jab wo *shared* aur backtested ho. **Chautha engine mat banao.** |
| **Risk** | R03 (planned), T03 `core/live/risk.py:50` `RiskEngine`, T01 `safety/circuit_breaker.py` | R03 authority (advisory) → gate; baaki backstop. |
| **Correlation** | R05 (planned), A002 internal, T03 `core/research` / `fuse.py` local | R05 shared; A002 news-linked; T03 fuse sirf local scalper ke liye. |

## 5. Licensing-evidence record (proposal)

Ek chhota "decision record" jo har T action ke saath bane (paper bhi, testnet bhi):

```
decision_id · agent · symbol · action · mode(paper|testnet|real)
inputs:   [ {event_id, type, maturity, ceiling, known_at} ... ]    # kin facts ne license kiya
vetoes:   [ {by, reason} ... ]                                      # jaise T03 soft veto
gate:     {decision(allow|hold|deny), reason}                       # sentinel
outcome:  (baad me) {pnl, horizon, resolved_at}                     # X06 ke liye
```

Isse AGENTS.md ka law ("each traces to licensing evidence") lagu hota hai, aur X06 ko calibration ke liye "prediction → outcome" milta hai. Relay isse bus par `t0N.decision.*` event me daal sakta hai. **Abhi ye kisi T agent me nahi hai** — T01 ka trades table kya record karta hai wo maine verify nahi kiya ([G-T-05](06-gap-register.md)).

## 6. Pehle kya band karna hai (Desk ki khuli bugs)

1. **T03 scalper ke breakers asar nahi karte.** `scalper.py:267` har step par naya `RiskEngine(limits)` banata hai, khali `RiskState` ke saath; `scalper.py:275` `can_trade(risk_state)` ko **dict** deta hai jabki `risk.py:70` `can_trade(self, equity: float)` maangta hai. Khali state me `peak_equity`/`day_start_equity` 0 hain, to drawdown aur daily-loss check shuru hi nahi hote. ([G-T-01](06-gap-register.md))
2. **T01/T03 execution sentinel ki nazar se bahar.** ([G-T-02](06-gap-register.md))
3. **T03 sentinel FAIL** — `HUMAN_CONFIRM_TOKEN` (`core/paper/__init__.py:15`) ek public confirmation phrase hai, secret nahi; regex false-positive. Fleet verdict aaj bhi FAIL hai. Operator ka call: rename ya whitelist.
4. **T01 `ready()` routing** (`bot.py:145-148`): `ready()` false hote hi paper engine par switch; khuli real position ka kya hoga — audit ne flag kiya, aaj dobara verify nahi hua.

## 7. T02 aur T03 kyun Desk me hi

- **T02** kabhi order nahi bhejta, par uska kaam "ye trade event aaya to market kaise react karega" hai — ye *faisle ki madad* hai, jankari lana nahi. A me jaata to collector standard (raw source) fit nahi hota, R me jaata to uska input ek *trade event* hai, A-ke-facts nahi. Operator ne Desk me hi rakhne ko kaha (2026-10-28); renumber ka purana sawal ([AGENTS.md](../../AGENTS.md) §3 aur `06-agents.md` §2) isi se band hota hai.
- **T03** ek hi hub me scanner (analysis) aur scalper (execution) hai. Aaj ke liye Desk. Agar scanner kal shared service ban jaye to wo R01 ban sakta hai — tab alag kiya jayega.

## 8. Is team ki kamiyan

[Gap register](06-gap-register.md): `G-T-01` … `G-T-10`.
