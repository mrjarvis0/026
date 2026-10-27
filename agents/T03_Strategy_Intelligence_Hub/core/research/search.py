"""Web search via Tavily (TAVILY_API_KEY) or Brave (BRAVE_API_KEY).

Both have free tiers. Returns a list of {title, url, snippet}. If no key is set,
returns an informative 'error' rather than raising — research can continue with
fetch_url / wikipedia / transcripts.
"""
from __future__ import annotations

from ..config import get_secret, load_env


def web_search(query: str, max_results: int = 5) -> dict:
    load_env()
    try:
        import requests
    except ImportError:
        return {"query": query, "error": "requests not installed"}

    tavily = get_secret("TAVILY_API_KEY")
    brave = get_secret("BRAVE_API_KEY")

    if tavily:
        try:
            r = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": tavily, "query": query, "max_results": max_results},
                timeout=25,
            )
            r.raise_for_status()
            results = [
                {"title": x.get("title", ""), "url": x.get("url", ""), "snippet": x.get("content", "")}
                for x in r.json().get("results", [])
            ]
            return {"query": query, "provider": "tavily", "results": results}
        except Exception as exc:
            return {"query": query, "error": f"tavily failed: {exc}"}

    if brave:
        try:
            r = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": brave, "Accept": "application/json"},
                params={"q": query, "count": max_results},
                timeout=25,
            )
            r.raise_for_status()
            web = r.json().get("web", {}).get("results", [])
            results = [
                {"title": x.get("title", ""), "url": x.get("url", ""), "snippet": x.get("description", "")}
                for x in web
            ]
            return {"query": query, "provider": "brave", "results": results}
        except Exception as exc:
            return {"query": query, "error": f"brave failed: {exc}"}

    return {
        "query": query,
        "error": "No search key. Set TAVILY_API_KEY (free at tavily.com) or BRAVE_API_KEY in .env, "
                 "or research via fetch_url / wikipedia / youtube_transcript instead.",
    }
