"""Collect research material about a trader and (optionally) draft a dossier.

Pulls from the sources you point it at (search / wikipedia / url / youtube video),
saves the raw evidence under knowledge/strategies/<slug>.raw.md, and with --auto
asks the Anthropic pipeline to draft knowledge/strategies/<slug>.draft.md.

Examples:
    python scripts/research.py --trader "Nicolas Darvas" --market stocks \
        --wiki "Nicolas Darvas" --search "Darvas box trading rules"
    python scripts/research.py --trader "Larry Williams" --market crypto \
        --video https://www.youtube.com/watch?v=XXXXXXXXXXX --auto
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
sys.path.insert(0, str(HUB_ROOT))

from core.knowledge import STRATEGIES_DIR  # noqa: E402
from core.registry import slugify  # noqa: E402
from core.research import fetch_url, web_search, wikipedia, youtube_transcript  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Research a trader's strategy from multiple sources.")
    ap.add_argument("--trader", required=True)
    ap.add_argument("--market", default="crypto", choices=["crypto", "forex", "stocks"])
    ap.add_argument("--search", default=None, help="web search query (needs TAVILY/BRAVE key)")
    ap.add_argument("--wiki", default=None, help="Wikipedia article title")
    ap.add_argument("--url", action="append", default=[], help="article/PDF URL (repeatable)")
    ap.add_argument("--video", action="append", default=[], help="YouTube URL/id (repeatable)")
    ap.add_argument("--auto", action="store_true", help="draft a dossier via the Anthropic pipeline")
    args = ap.parse_args()

    slug = slugify(args.trader)
    material: list[dict] = []
    print(f"Researching {args.trader}  (slug={slug}, market={args.market})")

    if args.wiki:
        w = wikipedia(args.wiki, full=True)
        if w.get("summary"):
            material.append({"source": f"Wikipedia: {w.get('title')}", "text": w["summary"], "url": w.get("url", "")})
            print(f"  wiki: {len(w['summary'])} chars")
        else:
            print(f"  wiki: {w.get('error', 'no content')}")

    if args.search:
        s = web_search(args.search)
        if s.get("results"):
            for r in s["results"]:
                material.append({"source": f"search:{r['title']}", "text": r["snippet"], "url": r["url"]})
            print(f"  search ({s.get('provider')}): {len(s['results'])} results")
        else:
            print(f"  search: {s.get('error', 'no results')}")

    for u in args.url:
        f = fetch_url(u)
        if f.get("text"):
            material.append({"source": f"url:{u}", "text": f["text"], "url": u})
            print(f"  url {u}: {f['chars']} chars ({f['extractor']})")
        else:
            print(f"  url {u}: {f.get('error')}")

    for v in args.video:
        t = youtube_transcript(v)
        if t.get("text"):
            material.append({"source": f"youtube:{t['video_id']}", "text": t["text"], "url": v})
            print(f"  video {t['video_id']}: {len(t['text'])} chars, {t['segments']} segments")
        else:
            print(f"  video {v}: {t.get('error')}")

    if not material:
        print("\nNo material collected. Provide --wiki/--search/--url/--video, or set a search key.")
        return 1

    STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = STRATEGIES_DIR / f"{slug}.raw.md"
    raw_lines = [f"# Raw research — {args.trader} ({args.market})", ""]
    for i, m in enumerate(material, 1):
        raw_lines += [f"## [{i}] {m['source']}", f"<{m.get('url','')}>", "", m["text"], ""]
    raw_path.write_text("\n".join(raw_lines), encoding="utf-8")
    print(f"\nSaved raw evidence: {raw_path}  ({len(material)} sources)")

    if args.auto:
        from core.research.dossier_writer import draft_dossier
        print("Drafting dossier via Anthropic pipeline ...")
        res = draft_dossier(args.trader, args.market, material)
        if res.get("markdown"):
            draft_path = STRATEGIES_DIR / f"{slug}.draft.md"
            draft_path.write_text(res["markdown"], encoding="utf-8")
            print(f"Draft dossier: {draft_path}  (model={res.get('model')})")
            print("REVIEW IT — verify every rule against the raw evidence before trusting (R-E).")
        else:
            print(f"Auto-draft skipped: {res.get('error')}")
    else:
        print("Next: read the .raw.md and write knowledge/strategies/<slug>.md by hand,")
        print("      or re-run with --auto to draft it via the LLM pipeline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
