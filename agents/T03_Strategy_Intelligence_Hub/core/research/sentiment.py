"""Sentiment adapters — SCALPER.md component #6.

Free, keyless data sources:
    - Fear & Greed Index   (alternative.me API, 24h cache)
    - CoinGecko market metrics (global market cap, BTC dominance, 24h change)
    - Optional RSS news sentiment (A002-style, keyword-based positivity/negativity)

All calls are:
    - Read-only (external market data, never instructions — R-B.1)
    - Best-effort: failure returns SentimentResult with `available=False`
    - Cached to a local JSON file to avoid hammering free APIs

The signal produced is deliberately small-weighted in SignalFuser (0.05) because
news/sentiment has very little edge on short timeframes — SCALPER.md §6 honesty.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import DATA_DIR


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class SentimentResult:
    """Fused sentiment score and supporting data."""
    score: float            # -1.0 (extreme fear) .. +1.0 (extreme greed)
    fng_value: int          # Fear & Greed raw value 0–100 (or -1 if unavailable)
    fng_label: str          # e.g. "Fear", "Extreme Greed"
    btc_dominance: float    # 0–100 from CoinGecko (or -1 if unavailable)
    market_cap_change_24h: float  # % 24h global market cap change
    available: bool         # False if all sources failed
    sources: list[str]      # which sources contributed

    def summary(self) -> str:
        if not self.available:
            return "sentiment unavailable (all sources failed)"
        return (f"sentiment score={self.score:+.2f}  "
                f"F&G={self.fng_value}({self.fng_label})  "
                f"BTC_dom={self.btc_dominance:.1f}%  "
                f"mktcap_24h={self.market_cap_change_24h:+.2f}%  "
                f"[{', '.join(self.sources)}]")


_UNAVAILABLE = SentimentResult(
    score=0.0, fng_value=-1, fng_label="unavailable",
    btc_dominance=-1.0, market_cap_change_24h=0.0,
    available=False, sources=[],
)


# ---------------------------------------------------------------------------
# Cache helper
# ---------------------------------------------------------------------------

_CACHE_FILE = DATA_DIR / "sentiment_cache.json"
_CACHE_TTL_SECS = 3600   # 1-hour cache for free APIs


def _load_cache() -> dict:
    if _CACHE_FILE.exists():
        try:
            return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_cache(data: dict) -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    except Exception:
        pass


def _cache_get(key: str) -> Any | None:
    c = _load_cache()
    entry = c.get(key)
    if entry and (time.time() - float(entry.get("ts", 0))) < _CACHE_TTL_SECS:
        return entry.get("value")
    return None


def _cache_set(key: str, value: Any) -> None:
    c = _load_cache()
    c[key] = {"ts": time.time(), "value": value}
    _save_cache(c)


# ---------------------------------------------------------------------------
# Fear & Greed Index (alternative.me — free, no key needed)
# ---------------------------------------------------------------------------

def fetch_fear_and_greed() -> tuple[int, str]:
    """Fetch the current Fear & Greed Index value (0–100) and label.

    Returns (-1, "unavailable") on failure.
    Cached for 1 hour.
    """
    cached = _cache_get("fng")
    if cached is not None:
        return int(cached["value"]), str(cached["label"])

    try:
        import urllib.request
        url = "https://api.alternative.me/fng/?limit=1"
        with urllib.request.urlopen(url, timeout=5) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        data = raw["data"][0]
        val = int(data["value"])
        label = str(data["value_classification"])
        _cache_set("fng", {"value": val, "label": label})
        return val, label
    except Exception:
        return -1, "unavailable"


def fng_to_score(fng_value: int) -> float:
    """Convert Fear & Greed 0–100 to sentiment score -1..+1.

    0 = extreme fear → -1.0
    50 = neutral → 0.0
    100 = extreme greed → +1.0
    """
    if fng_value < 0:
        return 0.0
    return round((fng_value - 50.0) / 50.0, 3)


# ---------------------------------------------------------------------------
# CoinGecko global market data (free, no key needed)
# ---------------------------------------------------------------------------

def fetch_coingecko_globals() -> dict:
    """Fetch global market data: total market cap, BTC dominance, 24h change.

    Returns empty dict on failure. Cached for 1 hour.
    """
    cached = _cache_get("cg_global")
    if cached is not None:
        return cached

    try:
        import urllib.request
        url = "https://api.coingecko.com/api/v3/global"
        req = urllib.request.Request(url, headers={"User-Agent": "T03-StrategyHub/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        d = raw.get("data", {})
        result = {
            "btc_dominance": round(float(d.get("market_cap_percentage", {}).get("btc", -1)), 2),
            "total_market_cap_usd": float(d.get("total_market_cap", {}).get("usd", 0)),
            "market_cap_change_pct_24h": round(float(d.get("market_cap_change_percentage_24h_usd", 0)), 3),
        }
        _cache_set("cg_global", result)
        return result
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Combined sentiment
# ---------------------------------------------------------------------------

def get_sentiment() -> SentimentResult:
    """Fetch all available sentiment signals and return a combined SentimentResult.

    Failures are handled gracefully: missing sources contribute 0 to the score.
    This function should never raise.
    """
    sources: list[str] = []
    score_parts: list[float] = []

    # Fear & Greed
    fng_val, fng_label = fetch_fear_and_greed()
    fng_score = fng_to_score(fng_val)
    if fng_val >= 0:
        score_parts.append(fng_score * 0.7)    # 70% weight within sentiment
        sources.append("F&G")

    # CoinGecko
    cg = fetch_coingecko_globals()
    btc_dom = float(cg.get("btc_dominance", -1))
    mktcap_chg = float(cg.get("market_cap_change_pct_24h", 0.0))

    cg_score = 0.0
    if cg:
        # Rising market cap + falling BTC dominance → altcoin season (bullish overall)
        # Falling market cap → bearish
        cg_score = float(mktcap_chg / 10.0)    # normalise roughly to -1..+1 range
        cg_score = max(min(cg_score, 1.0), -1.0)
        score_parts.append(cg_score * 0.3)      # 30% weight
        sources.append("CoinGecko")

    if not sources:
        return _UNAVAILABLE

    total_score = round(sum(score_parts), 3)
    total_score = max(min(total_score, 1.0), -1.0)

    return SentimentResult(
        score=total_score,
        fng_value=fng_val,
        fng_label=fng_label,
        btc_dominance=btc_dom,
        market_cap_change_24h=mktcap_chg,
        available=True,
        sources=sources,
    )
