# 01 · Intelligence Team (`A`) — jankari lane wali team

[← Teams](README.md) · *Next: [Analysis Bureau](02-analysis-bureau.md)*

> **Mission:** external duniya se raw jankari laana, use sourced aur timestamped fact banana, aur bus par rakh dena. **Facts, advice nahi.** Kuch trade nahi, kuch tay nahi.

## 1. Collector standard (A015 ka pattern, sab A agents ke liye)

A015 pehla agent hai jo is pattern par poora bana ([ADR-0005](../adr/ADR-0005-sqlite-event-bus.md), BUILD_LOG 2026-10-28). Har A agent ko ye 9 niyam maanne hain. Har niyam ke peeche ek asli ghatna hai:

| # | Niyam | Kyun (asli ghatna / research) |
|---|---|---|
| 1 | **`produces` pehle declare karo, build baad me.** Event type + schema_version manifest me. | Sirf A015 declare karta hai; envelope validator `source` ko manifest `produces` se authorize karta hai (`envelope.py:114`). |
| 2 | **Teen timestamp:** `event_time` (duniya me kab hua), `observed_at` (humne kab dekha), `known_at` (publicly kab pata chala). | A007 ke clusters `transaction_date` par bante the jabki filing ~45 din late public hoti hai → look-ahead risk (audit §2). |
| 3 | **Coverage aur lag har event me.** Absence ka claim bina coverage ke nahi. | Law: *coverage before absence* ([AGENTS.md](../../AGENTS.md) §0). |
| 4 | **Fetch fail ≠ khali.** Fail par error; "kuch nahi mila" alag cheez. Shrink guard. | A015 me fail par `{}` se mass-false DELISTING ban sakti thi (audit); ab shrink guard hai. A007 `mock=False → []` ab raise karta hai. |
| 5 | **Pehla (baseline) poll kabhi "ok" nahi.** | Cold start par NEW_LISTING ka flood (audit §2). |
| 6 | **Source health publish karo**, stale hone par ek hi `system.source.stale` (har outage par ek). | Supervisor 8 din band raha, kisi ko pata nahi chala (audit §4.9). |
| 7 | **Natural-key ids, idempotent writes.** | A007 `uuid4` + `INSERT OR IGNORE` = rerun par duplicates (audit). |
| 8 | **Untrusted text sirf structured fields me;** raw text kabhi instruction nahi. | Envelope `untrusted` flag + `action/command/tool` keys untrusted payload me banned (`envelope.py:25`); [Prompt Infection](07-research.md#a2a-mast-aur-baaki-audit-se). A002 untrusted news padhta hai. |
| 9 | **Source registry se bandha:** har source ka `S0xx` ID, consumer agent, rate limit, cost. | [`sources/`](../../sources/README.md), ADR-0004. |

Plus: deviation-only (kabhi bullish/bearish/buy/sell nahi), `execution_enabled: false`, `trust.level` 1 se shuru; "cannot be determined" guess se upar.

## 2. Roster, domain ke hisaab se

| Domain | Agent | Haal | Pehle kya chahiye |
|---|---|---|---|
| **On-chain** | `A001` Blockchain | substantial; 4 validated detectors; read-only bus adapter | bus relay (flows, exploit outflow); checkpoint-vs-store hole (audit) |
| | `A003` DeFi Flow | README-only | A001 ke saath overlap tay karna, phir manifest |
| | `A016` Protocol/Infra Event | README-only (detailed spec) | manifest + `produces` |
| | `A018` Token Unlock/Vesting | README-only (detailed spec) | DefiLlama free-vs-Pro sawal (README me open) |
| **News / social** | `A002` News | substantial; narratives + learning loop | bus relay (Slice 3, narrative ka natural key pehle) |
| | `A004` Social Sentiment | README-only | borderline — niche dekho |
| **Market / exchange** | `A005` Market Data | README-only | **sabse pehle** — niche dekho |
| | `A015` Listing/Delisting | partial; bus par producer | bybit network se unreachable (STALE); text-feeds |
| | `A017` Derivatives/Leverage | README-only | borderline — niche dekho |
| **Macro / public** | `A006` Macro/Econ | manifest-only | pehla real source (LuxAlgo COT/Fed) |
| | `A007` Public-Record | partial; MOCK-only | live MCP fetch + CLI |
| | `A008` Earnings Calendar | README-only | manifest |
| **TBD** | `A011` Reserved | README-only | domain tay karo ya free chhodo |

## 3. Build ki priority (meri salah)

1. **`A005` Market Data pehle.** Audit ka "intended feeds": A005 → A009, A010, A012, A013, A014, T01, T02, T03. Yani **poori R team aur Desk ka ek hissa A005 par ruka hai**, aur A005 me ek bhi `.py` nahi. Ye is poore fleet ka critical path hai.
2. **A002 ka bus relay** (Slice 3) — rumor A001/A015 tak pahunchne ke liye.
3. **A007 live fetch.** Tab tak wo alert nahi karta, sirf mock chalata hai.
4. **A006** — Forex/macro, phir baaki scaffolds jab zaroorat bane.

## 4. Borderline agents (operator ke sawal)

- **`A004` Social Sentiment:** [AGENTS.md](../../AGENTS.md) §3 me domain "Social/market sentiment **fusion**" likha hai. Agar wo sirf social platforms se raw data leta hai → A. Agar A002/A005 ke output ko fuse karta hai → R ban jata hai. README ke hisaab se A (social data); wording `fusion` hata dena behtar.
- **`A017` Derivatives/Leverage:** funding, open interest, liquidation exchanges se aate hain (raw, A). "Cascade risk" jaisa derived signal R ka kaam ho sakta hai. Salah: A017 sirf raw funding/OI/liquidation events de; cascade-risk R me jaye jab R banega.
- **`A002` ka internal cross-asset correlation:** news ke baad ke asset-reaction ke liye A002 ke andar rahe; general, always-on correlation `R05` ka. README me pehle se likha hai ki redundant nikla to A014 wapas A002 me fold ho sakta hai.

## 5. Intelligence Team ko X se kya milta hai

| X agent | A ko kya |
|---|---|
| X03 Pipeline Keeper | schedule, freshness SLO, backfill/replay |
| X02 Courier | schema registry, `produces`/`consumes` check |
| X05 Medic | retry/restart policy, incident log, stale-feed escalation |
| X07 Registrar | computed registry flags, lifecycle state |
| X06 Evolver | detector calibration ledger (A001/A002 ka promotion pipeline isi ka beej hai) |

## 6. Is team ki kamiyan

[Gap register](06-gap-register.md): `G-A-01` … `G-A-06`, `G-ORG-01`, `G-ORG-02`.
