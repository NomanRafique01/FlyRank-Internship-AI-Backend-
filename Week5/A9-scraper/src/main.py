"""
FlyRank Internship · Backend Track · Week 5 · Assignment A9
The Polite Scraper — Python lane (Requests + BeautifulSoup + Pydantic)

Stage 2: Find all three catalogue pages
- Parse saved HTML with BeautifulSoup
- Collect book links on each catalogue page
- Use urljoin() to turn relative hrefs into absolute URLs
- Follow the catalogue's own "next" link — stop at page 3
- Wait >= 500ms between real requests; cached pages need no delay
- Deduplicate before returning
"""

from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ─────────────────────────────  Constants  ────────────────────────────────── #

BASE_URL = "https://books.toscrape.com/"
REPO_URL = "https://github.com/your-username/FlyRank-Internship-AI-Backend-"
USER_AGENT = f"FlyRankInternship-A9/1.0 (+{REPO_URL})"

TIMEOUT = 10
DELAY   = 0.6

CACHE_DIR  = Path(__file__).parent.parent / "cache"
OUTPUT_DIR = Path(__file__).parent.parent / "output"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────── HTTP helpers  ───────────────────────────────── #

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})

_last_request_time: float = 0.0


def _cache_key(url: str) -> Path:
    slug = re.sub(r"[^\w]", "_", url)[:80]
    digest = hashlib.md5(url.encode()).hexdigest()[:8]
    return CACHE_DIR / f"{slug}_{digest}.html"


def fetch(url: str) -> tuple[str, bool]:
    """Return (html_text, from_cache). Raises HTTPError on non-200."""
    global _last_request_time

    cache_path = _cache_key(url)
    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        print(f"  CACHE HIT  {url}  ({len(html):,} bytes)")
        return html, True

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


# ─────────────────────────── Stage 2: Discover  ──────────────────────────── #

def discover_book_urls() -> list[str]:
    """
    Walk the first 3 catalogue pages, collect all book URLs, deduplicate.
    Returns a list of absolute URLs.
    """
    page_url: str | None = BASE_URL
    book_urls: list[str] = []
    pages_visited = 0

    while page_url and pages_visited < 3:
        html, _ = fetch(page_url)
        soup = BeautifulSoup(html, "html.parser")
        pages_visited += 1

        for article in soup.select("article.product_pod"):
            a_tag = article.select_one("h3 > a")
            if a_tag and a_tag.get("href"):
                # urljoin handles both home-page hrefs ("catalogue/book/index.html")
                # and inner-page hrefs ("book/index.html") correctly
                abs_url = urljoin(page_url, a_tag["href"])
                book_urls.append(abs_url)

        next_btn = soup.select_one("li.next > a")
        if next_btn and pages_visited < 3:
            page_url = urljoin(page_url, next_btn["href"])
        else:
            page_url = None

    unique_urls = list(dict.fromkeys(book_urls))   # deduplicate, preserve order
    print(f"\ncatalogue_pages={pages_visited}  discovered={len(book_urls)}  unique_urls={len(unique_urls)}")
    return unique_urls


# ──────────────────────────────── Entry point  ────────────────────────────── #

if __name__ == "__main__":
    urls = discover_book_urls()
    print(f"First URL: {urls[0]}")
    print(f"Last URL:  {urls[-1]}")
