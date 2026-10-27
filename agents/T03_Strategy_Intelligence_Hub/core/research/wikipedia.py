"""Wikipedia article text via the public REST API (no key)."""
from __future__ import annotations

import urllib.parse

# Wikipedia's API policy requires a descriptive User-Agent; requests without one get 403.
_HEADERS = {"User-Agent": "strategy-master-research/1.0 (agent hub; contact: local user)"}


def wikipedia(title: str, lang: str = "en", full: bool = False) -> dict:
    """Return {'title','summary','url'} (or full plain-text extract if full=True)."""
    try:
        import requests
    except ImportError:
        return {"error": "requests not installed"}

    if not full:
        slug = urllib.parse.quote(title.replace(" ", "_"))
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{slug}"
        try:
            r = requests.get(url, headers=_HEADERS, timeout=20)
            r.raise_for_status()
            j = r.json()
        except Exception as exc:
            return {"title": title, "error": f"wikipedia failed: {exc}"}
        return {
            "title": j.get("title", title),
            "summary": j.get("extract", ""),
            "url": j.get("content_urls", {}).get("desktop", {}).get("page", ""),
        }

    # full plain-text extract
    api = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query", "prop": "extracts", "explaintext": 1,
        "redirects": 1, "format": "json", "titles": title,
    }
    try:
        r = requests.get(api, params=params, headers=_HEADERS, timeout=25)
        r.raise_for_status()
        pages = r.json()["query"]["pages"]
        page = next(iter(pages.values()))
    except Exception as exc:
        return {"title": title, "error": f"wikipedia failed: {exc}"}
    return {
        "title": page.get("title", title),
        "summary": page.get("extract", ""),
        "url": f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
    }
