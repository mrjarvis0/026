# 02 · Analysis Bureau (`R`) — samajhne wali team

[← Intelligence Team](01-intelligence-team.md) · [Teams](README.md) · *Next: [Trading Desk](03-trading-desk.md)*

> **Mission:** A ke facts aur stored data se **derive** karna — pattern, regime, risk, spread, correlation — aur Desk ko advisory output dena. Read-only, kabhi order nahi. Series letter `R` = Research/Reasoning (provisional).

## 1. Ye team alag kyun hai

A-series ke andar do cheezein mili thi: *raw jankari lana* aur *jankari se kuch nikalna*. Dono ke jhoothe hone ke tareeke alag hain:

- Collector galat ho to **source ya coverage** galat hota hai (stale feed, fetch fail).
- Analyst galat ho to **inference** galat hota hai (overconfidence, double-counting, look-ahead).

Isliye rules alag hain, aur inhe ek hi team me rakhne se collector standard ([01](01-intelligence-team.md) §1) analysts par fit nahi baithta. [Team Topologies](https://martinfowler.com/bliki/TeamTopologies.html) ki bhasha me R ek *complicated-subsystem* team hai: gehri specialist cheezein, jinka output Desk bina andar ghuse leta hai.

## 2. Analyst standard

| # | Niyam | Source |
|---|---|---|
| 1 | **Confidence ≤ sabse kamzor input.** Average nahi. | [AGENTS.md](../../AGENTS.md) §4 rule 1 |
| 2 | **Conflicts record hote hain, resolve nahi.** A001 aur A002 asahmat hon to dono output me. | §4 rule 2 |
| 3 | **Provenance split rehta hai.** Har input ki apni chain; merged chain nahi. | §4 rule 3 |
| 4 | **Independence underlying source se naapo, agent se nahi.** Do agents ek hi tweet se aaye ho sakte hain. | audit §4.6 |
| 5 | **Sirf bus / brain se input.** Apna external fetch nahi — warna wo A hai. | [README](README.md) §2 |
| 6 | **Correlation = hypothesis, verdict nahi**, jab tak har half apne maturity gate se pass na ho. | §4 rule 4 |
| 7 | **Output events me `confidence` + `ceiling` + `maturity` + `coverage`**, aur `evidence_refs` apne inputs ke event ids. | envelope ([05](05-handoffs-and-contracts.md)) |
| 8 | **Deviation / advisory shape.** "Position size 0.4%" theek; "buy karo" nahi. | `reports_deviation_only` |

## 3. Roster (folders abhi `A0NN` naam par; rename baad me)

| Naya ID | Abhi folder | Kaam (README se) | Inputs (kahan se) | Output (kis ko) | Overlap jo tay karna hai |
|---|---|---|---|---|---|
| `R01` | `A009_Technical_Pattern_Intelligence` | chart patterns, TA | **A005** OHLCV | T01/T03 ko advisory | T03 scanner (8 strategies) + T01 ke `signals.py` — **teen TA engines** |
| `R02` | `A010_Volatility_Regime_Intelligence` | volatility regime (calm/trending/choppy) | **A005**, A017 | R03, T01/T03 (regime gate) | T01 ka ATR/ADX regime gate, T03 MTF chop-detect |
| `R03` | `A012_Risk_Assessment_Intelligence` | position sizing, stop, portfolio exposure (advisory) | A005, R02, R05, A-events | **sentinel gate → T01/T03** | T03 `core/live/risk.py` `RiskEngine`, T01 `safety/circuit_breaker.py` — **teen risk engines** |
| `R04` | `A013_Arbitrage_Detection_Intelligence` | cross-exchange spread, triangular FX | A005 (multi-exchange) | T Desk (alag gated arb job) | — |
| `R05` | `A014_Correlation_Intelligence` | BTC↔Nasdaq, DXY↔EURUSD, USD↔gold | A005, A006 | R03, orchestrator fusion | A002 ka news-driven cross-asset correlation |

**Sabhi abhi sirf README hain** — na manifest, na registry, na code, na test. ([G-R-01](06-gap-register.md))

## 4. Critical path: R team A005 par ruki hai

Audit ke "intended feeds" ke hisaab se R01–R05 sabka input A005 (Market Data) hai, aur A005 me ek bhi `.py` nahi. **R ka koi bhi agent A005 se pehle banana bekaar hai** — wo chhoti synthetic data par chalega aur "validated" ban nahi sakta ([AGENTS.md](../../AGENTS.md) §10: backtest labelled window par).

Salah ka order: A005 → R02/R05 (sirf OHLCV chahiye) → R03 (R02+R05 par tika) → R01/R04.

## 5. R03 aur ek hi risk authority

Teen risk engines hain (R03 README, T03 `RiskEngine`, T01 circuit breaker). Do tareeke se ye ulajh sakta hai: ya to teeno apne-apne numbers dein, ya koi ek "authority" nahi. Salah ([03](03-trading-desk.md) §4): **R03 advisory number deta hai → sentinel gate use enforce karta hai → T01/T03 ke local breakers *last-resort backstop* rahte hain, authority nahi.** R03 kabhi order nahi bhejta — [A012 README](../../agents/A012_Risk_Assessment_Intelligence/README.md) me yahi likha hai.

## 6. Rename ka plan (abhi nahi, alag go-ahead par)

| Abhi | Baad me | Kya chhoona padega |
|---|---|---|
| `A009_…` | `R01_…` | folder naam, docs ke references, `sources/` ke "consumed by" columns |
| `A010_…` | `R02_…` | wahi |
| `A012_…` | `R03_…` | wahi + audit/ADR ke A012 mentions |
| `A013_…` | `R04_…` | wahi |
| `A014_…` | `R05_…` | wahi |

Ye sab empty README scaffolds hain — na code, na manifest, na registry — isliye rename sasta hai. **Par blind substring replace nahi:** hamesha word-boundary (`\bA012\b`) + `A012_` prefix se (pehle `A01→A001` rename me hex addresses me `A01` ghus gaya tha). Freed IDs (`A009, A010, A012, A013, A014`) khaali chhodein ya baad me reuse karein? `A011` ka precedent *reuse* tha — operator ka call ([README open question](#7-operator-ke-sawal)).

## 7. Operator ke sawal

1. Letter `R` aur naam "Analysis Bureau" theek?
2. Freed A-IDs khaali ya reuse?
3. R03 ka output sirf gate ko jaye, ya T01/T03 ko bhi seedha (advisory display)?

## 8. Is team ki kamiyan

[Gap register](06-gap-register.md): `G-R-01` … `G-R-04`, `G-A-02`.
