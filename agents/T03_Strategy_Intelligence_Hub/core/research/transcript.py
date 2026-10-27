"""YouTube transcript -> text (youtube-transcript-api; no API key).

Pulls existing captions/subtitles. Videos WITHOUT captions need audio download +
speech-to-text (e.g. Whisper) — heavier, intentionally out of scope here.
Install: `pip install youtube-transcript-api`.
"""
from __future__ import annotations

import re

_ID_PATTERNS = [
    r"(?:v=|/embed/|/shorts/|youtu\.be/)([A-Za-z0-9_-]{11})",
    r"^([A-Za-z0-9_-]{11})$",
]


def video_id(url_or_id: str) -> str | None:
    """Extract an 11-char YouTube id from a URL or accept a bare id."""
    for pat in _ID_PATTERNS:
        m = re.search(pat, url_or_id.strip())
        if m:
            return m.group(1)
    return None


def youtube_transcript(url_or_id: str, languages: tuple[str, ...] = ("en", "en-US", "hi")) -> dict:
    """Return {'video_id','text','segments','languages'} or an 'error' key.

    Never raises on caption problems — returns an informative error so a research
    run can continue with other sources.
    """
    vid = video_id(url_or_id)
    if not vid:
        return {"input": url_or_id, "error": "Could not parse a YouTube video id."}

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return {"video_id": vid, "error": "youtube-transcript-api not installed "
                                          "(`pip install youtube-transcript-api`)."}

    try:
        # classmethod API (youtube-transcript-api <= 0.6.x)
        segments = YouTubeTranscriptApi.get_transcript(vid, languages=list(languages))
    except AttributeError:
        # newer instance API fallback
        try:
            api = YouTubeTranscriptApi()
            fetched = api.fetch(vid, languages=list(languages))
            segments = [{"text": s.text, "start": s.start, "duration": s.duration} for s in fetched]
        except Exception as exc:
            return {"video_id": vid, "error": f"transcript failed: {exc}"}
    except Exception as exc:
        return {"video_id": vid, "error": f"transcript failed (no captions / unavailable?): {exc}"}

    text = " ".join(seg["text"] for seg in segments).strip()
    text = re.sub(r"\s+", " ", text)
    return {"video_id": vid, "text": text, "segments": len(segments), "languages": list(languages)}
