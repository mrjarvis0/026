# Label sources

Every label loaded from this folder records its origin. A label without a
source is not trusted, and no label is ever inferred from behaviour.

## evm_cex.csv

- **Source:** https://gist.github.com/xfwil/07dadf39ae559829132952734ca524f3
- **Obtained:** 2026-08-12
- **Rows:** **2,859** addresses across 316 exchanges — corrected from 2,858 on
  2026-08-14. The file holds 2,860 lines, one of them the header, and the
  loader accepted 2,859 with no duplicates and nothing rejected. The earlier
  figure was off by one; the count here is now the measured one.
- **Validated:** 0 malformed addresses, 0 duplicates
- **Loaded:** 2026-08-14 via `a01 labels --load data/labels
  --source gist:xfwil/07dadf39`, into `data/a01.db`
- **Columns:** `address,cex_name,distinct_name` — `cex_name` is stored as the
  operator (`labels.entity`) and `distinct_name` as the address's own label.
  Both are kept: attribution groups by operator, and the per-address label is
  what makes a row traceable back to this file.
- **Category:** all rows are `exchange`
- **Chains:** EVM only. One address is valid across every EVM chain, so no
  `chain` column is needed or wanted here.

**Not covered — these need their own lists when those chains are wired:**
TRON (matters most; largest USDT flow), Bitcoin, Solana. Each uses a different
address format, so an EVM list cannot serve them.

**Confidence:** community-maintained list, unverified against an authoritative
source. Load as `source="gist:xfwil/07dadf39"`, `verification_status`
unverified — a large well-formed list is evidence of care, not of correctness.
