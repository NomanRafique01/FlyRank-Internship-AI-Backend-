"""
FlyRank Internship · Backend Track · Week 5 · Assignment A9
The Polite Scraper — Python lane (Requests + BeautifulSoup + Pydantic)

Stage 1: Fetch once, cache once
- Send an honest User-Agent header
- Set a request timeout
- Check status code before parsing
- Save HTML to cache/; print FETCH on first run, CACHE HIT on subsequent runs
"""

from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path

import requests

# ─────────────────────────────  Constants  ────────────────────────────────── #

BASE_URL = "https://books.toscrape.com/"
REPO_URL = "https://github.com/your-username/FlyRank-Internship-AI-Backend-"
USER_AGENT = f"FlyRankInternship-A9/1.0 (+{REPO_URL})"

TIMEOUT = 10    # seconds per request
DELAY   = 0.6   # seconds between real (non-cached) HTTP requests

CACHE_DIR  = Path(__file__).parent.parent / "cache"
OUTPUT_DIR = Path(__file__).parent.parent / "output"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────── HTTP helpers  ───────────────────────────────── #

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})

_last_request_time: float = 0.0


def _cache_key(url: str) -> Path:
    """Return a deterministic cache-file path for a URL."""
    slug = re.sub(r"[^\w]", "_", url)[:80]
    digest = hashlib.md5(url.encode()).hexdigest()[:8]
    return CACHE_DIR / f"{slug}_{digest}.html"


def fetch(url: str) -> tuple[str, bool]:
    """
    Return (html_text, from_cache).
    Reads from disk cache if available; otherwise fetches with politeness.
    Raises requests.HTTPError on non-200.
    """
    global _last_request_time

    cache_path = _cache_key(url)
    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        print(f"  CACHE HIT  {url}  ({len(html):,} bytes)")
        return html, True

    # Polite delay between real requests
    elapsed = time.monotonic() - _last_request_time
    if elapsed < DELAY:
        time.sleep(DELAY - elapsed)

    resp = _session.get(url, timeout=TIMEOUT)
    _last_request_time = time.monotonic()

    if resp.status_code != 200:
        resp.raise_for_status()

    resp.encoding = resp.apparent_encoding or "utf-8"
    html = resp.text
    cache_path.write_text(html, encoding="utf-8")
    print(f"  FETCH      {url}  ({len(html):,} bytes)")
    return html, False


# ──────────────────────────────── Entry point  ────────────────────────────── #

if __name__ == "__main__":
    print(f"User-Agent: {USER_AGENT}")
    html, from_cache = fetch(BASE_URL)
    print(f"  Response size: {len(html):,} bytes  (from_cache={from_cache})")
