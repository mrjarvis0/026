# Knowledge source

The hub's **research memory** — where each trader's *actual, cited* strategy is documented
*before* any code is written. This is the `/ghostresearch` role of the Constitution: no invented
rules, every claim tied to a real source (R-E.1 – R-E.4).

## How it works

```
knowledge/
├── TRADERS.md              # curated roster of top traders + signature strategies (the shortlist)
├── strategies/            # ONE research dossier per trader/strategy (cited rules)
│   ├── _TEMPLATE.md       #   copy this to start a new dossier
│   └── dennis-turtle.md   #   example (backs agent $001-dennis)
└── sources/
    └── SOURCES.md         # shared bibliography — every [TAG] used in dossiers resolves here
```

## Workflow: research → agent

1. Pick a trader from [`TRADERS.md`](TRADERS.md) (or one you name).
2. Copy `strategies/_TEMPLATE.md` → `strategies/<slug>.md` and fill it with the trader's **real,
   cited** rules. Add any new sources to [`sources/SOURCES.md`](sources/SOURCES.md).
3. Scaffold the agent: `python scripts/new_agent.py --owner <name> --market <m> --strategy "<desc>"`.
4. Copy the dossier's rules into the agent's `.agent.md` and implement `strategy.py`.
5. Backtest → train → review.

The dossier is the **evidence**; the agent is the **implementation**. Keeping them separate means a
strategy can be researched once and implemented for several markets/agents.

## Programmatic access

`core/knowledge.py` reads this folder so scripts/agents can query it:

```python
from core.knowledge import list_traders, load_dossier, list_sources
list_traders()                 # roster entries from TRADERS.md
load_dossier("dennis-turtle")  # frontmatter + body of one dossier
```
