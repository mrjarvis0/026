"""Announcement feeds — the earliest-detection layer (README §4.3).

An exchange usually *announces* a listing hours-to-days before the symbol actually
appears in `fetch_markets()`, and per README §3 the price effect lands around the
announcement. So this layer answers "what has been announced but hasn't listed yet?".

Free/keyless sources, best-effort and **resilient**: each source is independent and
a blocked/failing one is skipped (returns []), never fabricated. Binance's CMS is
bot-protected and often 400/403s from datacenter IPs (README §Sources) — OKX's
public announcements API is the reliable one.
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timezone

_UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

# Words that are never a token ticker (venue names, quote assets, product nouns).
_STOPWORDS = {
    "OKX", "BINANCE", "COINBASE", "BYBIT", "KRAKEN", "GATE",
    "TO", "LIST", "LISTING", "LISTS", "WILL", "THE", "AND", "FOR", "OF", "ON", "IN", "A",
    "USD", "USDT", "USDC", "EUR", "BTC", "ETH",
    "SPOT", "TRADING", "TRADE", "PAIR", "PAIRS", "MARGIN", "PERP", "PERPS", "PERPETUAL",
    "FUTURES", "FUTURE", "EQUITY", "TOKENIZED", "STOCK", "STOCKS", "CRYPTO", "ADD", "ADDS",
    "NEW", "LAUNCHPOOL", "LAUNCHPAD", "SEED", "HODLER", "AIRDROP", "PRE", "MARKET", "OPTIONS",
    "X", "USDM", "SWAP",
    # non-ticker product/service words seen in "Will Add X on ..." announcements
    "VIP", "LOAN", "LOANS", "EARN", "BUY", "SELL", "CONVERT", "SIMPLE", "FLEXIBLE", "LOCKED",
    "STAKING", "STAKE", "SAVINGS", "DUAL", "INVESTMENT", "AUTO", "INVEST", "REWARDS", "BONUS",
    "SUPPORT", "SUPPORTS", "DELIST", "DELISTS", "DELISTING", "REMOVE", "REMOVES", "OR", "WITH",
}


def _http_json(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def _ms_to_iso(ms) -> str | None:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


def extract_tokens(title: str) -> list[str]:
    """Best-effort ticker extraction from an announcement title.

    Prefers explicit parenthesised tickers ("Will List Foobar (FOO)"), else takes
    upper-case words and strips a USD/USDT/USDC quote suffix. Heuristic — flagged as
    such in the report's confidence.
    """
    title = title or ""
    parens = [t for t in re.findall(r"\(([A-Z0-9]{2,10})\)", title) if t not in _STOPWORDS]
    if parens:
        return list(dict.fromkeys(parens))
    # No parenthesised ticker: only guess a bare ticker from a genuine *listing*
    # announcement ("... to list ..."), never from "Will Add X on Earn / VIP Loan"
    # style titles — that's where false positives like "VIP" came from.
    if "list" not in title.lower():
        return []
    tokens: list[str] = []
    for word in re.findall(r"\b([A-Z][A-Z0-9]{1,9})\b", title):
        base = word
        for suffix in ("USDT", "USDC", "USD"):
            if base.endswith(suffix) and len(base) > len(suffix):
                base = base[: -len(suffix)]
                break
        if len(base) >= 2 and base not in _STOPWORDS:
            tokens.append(base)
    return list(dict.fromkeys(tokens))


def _normalise(exchange: str, title: str, url: str | None, announced_ms) -> dict:
    return {
        "exchange": exchange,
        "title": title,
        "url": url,
        "announced_at": _ms_to_iso(announced_ms),
        "tokens": extract_tokens(title),
    }


def fetch_okx() -> list[dict]:
    try:
        data = _http_json("https://www.okx.com/api/v5/support/announcements"
                          "?annType=announcements-new-listings")
    except Exception as exc:  # noqa: BLE001
        print(f"[A015] okx announcements unavailable: {type(exc).__name__}")
        return []
    out = []
    for group in data.get("data", []):
        for item in group.get("details", []):
            out.append(_normalise("okx", item.get("title"), item.get("url"), item.get("pTime")))
    return out


def fetch_binance() -> list[dict]:
    try:
        data = _http_json("https://www.binance.com/bapi/apex/v1/public/apex/cms/article/list/query"
                          "?type=1&catalogId=48&pageNo=1&pageSize=20")
    except Exception as exc:  # noqa: BLE001
        print(f"[A015] binance announcements unavailable (bot-protection): {type(exc).__name__}")
        return []
    out = []
    for catalog in (data.get("data") or {}).get("catalogs", []):
        for art in catalog.get("articles") or []:
            code = art.get("code")
            url = f"https://www.binance.com/en/support/announcement/{code}" if code else None
            out.append(_normalise("binance", art.get("title"), url, art.get("releaseDate")))
    return out


_SOURCES = {"okx": fetch_okx, "binance": fetch_binance}


def fetch_all(sources: list[str] | None = None) -> list[dict]:
    """Fetch announcements from all (or the named) sources; failures are skipped."""
    out: list[dict] = []
    for name in (sources or list(_SOURCES)):
        fetcher = _SOURCES.get(name)
        if fetcher:
            out.extend(fetcher())
    return out
