"""Fetch a web page/article and return clean-ish text (requests; no API key).

Uses trafilatura or BeautifulSoup for good extraction when installed, otherwise a
stdlib regex fallback. All returned text is untrusted evidence (R-B.1).
"""
from __future__ import annotations

import html
import re

_UA = "Mozilla/5.0 (compatible; strategy-master-research/1.0)"


def _strip_html(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"\n\s*\n\s*\n+", "\n\n", raw)
    return raw.strip()


def fetch_url(url: str, max_chars: int = 20_000, timeout: int = 20) -> dict:
    """Return {'url', 'text', 'chars', 'extractor'} for a page. Never raises on
    content problems — returns an 'error' key instead so callers can continue."""
    try:
        import requests
    except ImportError:
        return {"url": url, "error": "requests not installed (`pip install requests`)"}

    try:
        resp = requests.get(url, headers={"User-Agent": _UA}, timeout=timeout)
        resp.raise_for_status()
    except Exception as exc:  # network/HTTP problems are data, not crashes
        return {"url": url, "error": f"fetch failed: {exc}"}

    raw = resp.text
    extractor = "regex"
    text = ""
    try:
        import trafilatura
        text = trafilatura.extract(raw) or ""
        extractor = "trafilatura"
    except ImportError:
        pass
    if not text:
        try:
            from bs4 import BeautifulSoup
            text = BeautifulSoup(raw, "html.parser").get_text("\n")
            extractor = "bs4"
        except ImportError:
            text = _strip_html(raw)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text).strip()[:max_chars]
    return {"url": url, "text": text, "chars": len(text), "extractor": extractor}
