# MCP setup guide

This hub ships a project-scoped [`.mcp.json`](.mcp.json) so that when you open the folder in **Claude
Code**, the assistant gets research tools (web fetch, etc.). MCP is used by *Claude* while helping you
research/build agents — the Python scripts (`backtest.py`, etc.) do **not** need MCP to run.

## Reality check on your machine

- ✅ **Python** is installed.
- ❌ **Node / npx / uvx** are **not** installed — most MCP servers need one of them.

The lowest-friction fix: install **uv** (gives you `uvx`) with pip. That unlocks the Python-based
servers already wired in `.mcp.json` **without needing Node**:

```bash
pip install uv
```

Then restart Claude Code in this folder. `uvx` will auto-download the servers on first use.

## What's wired now (Python, no API key)

| Server | Command | What it does |
|---|---|---|
| `fetch` | `uvx mcp-server-fetch` | fetch a web page/PDF → text (research articles, rule pages) |
| `time` | `uvx mcp-server-time` | current time / timezone helper |

## Optional servers (need Node, or an API key)

Install Node first (https://nodejs.org) to use `npx`-based servers, then add any of these to the
`mcpServers` object in `.mcp.json`. **Verify the exact package name/version when you add it** (they
change — Constitution R-E.6):

```jsonc
// web search (pick ONE; put the key in .env):
"brave-search": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-brave-search"],
  "env": { "BRAVE_API_KEY": "${BRAVE_API_KEY}" }
},
// let Claude read this hub's files (knowledge/, agents/):
"filesystem": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
}
```

## Don't have Node/uv and don't want to install?

You lose nothing critical. Research still works two other ways:
1. **This Claude Code tool's own** WebSearch/WebFetch — just ask me to research a trader.
2. **The hub's Python research layer** — `python scripts/research.py ...` (see below) uses `requests`
   (already installed) for web fetch, Wikipedia, search (with a key), and YouTube transcripts.

## The Python research layer (works without MCP)

```bash
# needs a search key only for --search; --wiki/--url/--video work keyless
pip install -r requirements-research.txt   # youtube-transcript-api, anthropic, etc.

python scripts/research.py --trader "Nicolas Darvas" --market stocks \
    --wiki "Nicolas Darvas" --search "Darvas box trading rules"

# from a video's captions:
python scripts/research.py --trader "Larry Williams" --market crypto \
    --video https://www.youtube.com/watch?v=XXXXXXXXXXX --auto
```

Keys go in `.env` (see [`.env.example`](.env.example)): `TAVILY_API_KEY` **or** `BRAVE_API_KEY` for
search, `ANTHROPIC_API_KEY` for the `--auto` dossier drafter. Fetch, Wikipedia, and YouTube
transcripts need **no key**.
