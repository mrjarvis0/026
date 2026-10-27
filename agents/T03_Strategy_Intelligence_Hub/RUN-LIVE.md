# Running an agent as a (paper) trader — Binance Testnet

`scripts/run_live.py` turns any agent into a running paper trader on **Binance Spot Testnet**
(fake money). Each closed daily bar it reads the strategy's target position, checks what the
account already holds, and places **only the delta order**.

> **Safety:** testnet only. **Dry-run by default** — nothing is sent unless you pass BOTH `--arm`
> and the confirm token. **Real-money trading is not built** and must be done by you, manually,
> outside this tool (Constitution R-B.4). Orders are bounded by the `live:` limits in the agent's
> `config.yaml` (max order size, max trades/day).

## 1. Dry-run (no keys needed)

```bash
python scripts/run_live.py '$005-seykota'
```

Shows the latest **closed-bar** target (long/flat), a simulated equity, and the exact order it
*would* place. Sends nothing. (Market data fetch needs internet; the account is simulated until you
add testnet keys.)

## 2. Add Binance Testnet keys (to read the real testnet account + send)

1. Create keys at **https://testnet.binance.vision/** (testnet only — never mainnet keys).
2. Put them in `.env` (copy from `.env.example`):
   ```
   BINANCE_TESTNET_API_KEY=...
   BINANCE_TESTNET_API_SECRET=...
   ```
3. Fund the testnet account from the faucet on that site (free test USDT).

Re-run the dry-run — it now reads your real testnet balance and shows the correct delta.

## 3. Arm it (actually place testnet orders)

```bash
python scripts/run_live.py '$005-seykota' --arm --confirm I-CONFIRM-PAPER-ORDER
```

Places the delta order on the testnet, records it to `agents/$005-seykota/results/live_trades.csv`,
and updates `agents/$005-seykota/live_state.json`. Re-running on the **same bar does nothing**
(idempotent).

## 4. Keep it running

The strategies are **daily**, so the agent only needs to act once per day after the 00:00 UTC bar
closes. Two ways:

**A. Persistent loop** (leave it running):
```bash
python scripts/run_live.py '$005-seykota' --arm --confirm I-CONFIRM-PAPER-ORDER --loop
```
It steps, then sleeps until ~00:05 UTC the next day. Ctrl+C to stop.

**B. Windows Task Scheduler** (recommended — runs even after reboot). Create a daily task at 00:05 UTC:
```bat
schtasks /Create /TN "strategy-master-seykota" /SC DAILY /ST 00:05 ^
  /TR "python \"F:\my-agents\$trategy-master\scripts\run_live.py\" \"$005-seykota\" --arm --confirm I-CONFIRM-PAPER-ORDER"
```
(Adjust the Python path if needed; keep the quotes around the `$`-paths.)

## Notes

- **Long/flat only on spot.** Binance spot testnet can't short, so a `-1` target is treated as
  **flat** (with a warning). `$005-seykota` is long-only, so unaffected. Short-capable agents would
  need Binance **Futures** testnet (not wired yet).
- **Fidelity:** the engine acts on the last **fully-closed** bar (the forming candle is dropped), so
  live behavior matches the backtest.
- **Any agent:** swap `'$005-seykota'` for any id (e.g. `'$007-oneil'`). Add a `live:` block to that
  agent's `config.yaml` to override the default limits.
- Logs: `logs/live_<agent>.log`; fills: `agents/<agent>/results/live_trades.csv`.
```
