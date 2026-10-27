# `$trategy-master`

A **multi-agent hub** that turns the world's top traders' strategies (crypto / forex / stocks) into
backtestable, trainable, reviewable algorithms. Each trader's strategy = **one agent** in `agents/`.

> Governed by [`../AGENT_CONSTITUTION.md`](../AGENT_CONSTITUTION.md). Hub spec: [`$trategy-master.agent.md`](./%24trategy-master.agent.md).

## What it does

For each strategy-agent: **research → build algo → backtest → train on real data → review** (and,
only with explicit human approval, **paper-trade** on a demo/testnet). No real-money trading.

## Layout

```
$trategy-master/
├── $trategy-master.agent.md   # hub spec / mandate
├── README.md                  # this file
├── AGENTS_INDEX.md            # serial registry ($NNN → owner → market → status)
├── requirements.txt           # pinned shared deps
├── .env.example               # required secret NAMES only (copy to .env, fill locally)
├── .gitignore
├── core/                      # SHARED library every agent reuses
│   ├── config.py  registry.py  strategy_base.py
│   ├── data/     # crypto_binance.py, forex_oanda.py, stocks_yf.py, base.py
│   ├── backtest/ # runner.py, metrics.py
│   ├── train/    # optimizer.py
│   ├── review/   # report.py
│   └── paper/    # binance_testnet.py, oanda_practice.py, alpaca_paper.py
├── agents/                    # ONE folder per strategy-agent
│   └── $001-dennis/           #   Turtle Trading (Richard Dennis), crypto
├── scripts/                   # CLI: new_agent, backtest, train, review, papertrade
├── templates/                 # scaffolding for new agents
├── data/                      # cached market data (git-ignored)
└── logs/                      # run logs (git-ignored)
```

**Why the shared `core/`:** with hundreds of agents planned, no agent re-implements data loading,
backtesting, metrics, or reporting. An agent folder holds *only* its strategy logic, config, cited
spec, and results.

## Setup

Requires **Python 3.11+**.

```bash
cd "F:/my-agents/\$trategy-master"
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# Git Bash:            source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in any keys you actually use (paper/live only)
```

> **Windows `$` paths:** this folder starts with `$`. In **PowerShell always single-quote** the path
> (`'F:\my-agents\$trategy-master'`) so `$` isn't read as a variable. Python and the file tools use
> literal paths and are unaffected. Crypto **backtesting needs no keys** (public Binance data).

## Usage

```bash
# 1. Backtest an existing agent on real data
python scripts/backtest.py '$001-dennis'

# 2. Train / optimize it (walk-forward, out-of-sample)
python scripts/train.py '$001-dennis'

# 3. Generate the performance review (REVIEW.md + equity curve)
python scripts/review.py '$001-dennis'

# 4. Scaffold a NEW agent (serial auto-allocated in order)
python scripts/new_agent.py --owner livermore --market crypto --strategy "Trend / pyramiding"

# 5. Paper-trade (DRY-RUN by default — prints intended orders, sends nothing)
python scripts/papertrade.py '$001-dennis'
```

## Adding a new trader's strategy

1. `python scripts/new_agent.py --owner <name> --market <crypto|forex|stocks> --strategy "<desc>"`
   — this allocates the next `$NNN`, creates `agents/$NNN-<name>/` from templates, and appends a row
   to `AGENTS_INDEX.md`.
2. Fill in `agents/$NNN-<name>/$NNN-<name>.agent.md` with the trader's **real, cited** rules.
3. Implement the signal logic in `agents/$NNN-<name>/strategy.py` (subclass `StrategySpec`).
4. Set symbols / timeframe / params in `config.yaml`.
5. Run backtest → train → review.

## Safety

Paper/testnet only. `papertrade.py` never sends a live order; real-money trading requires a separate,
explicit human step (Constitution R-B.4). Secrets live in `.env`, never committed. Backtests are
historical simulations — **not financial advice**, past performance ≠ future results.
