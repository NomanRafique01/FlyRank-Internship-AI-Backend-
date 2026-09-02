"""
FlyRank Internship · Backend Track · Week 5 · Assignment A9
The Polite Scraper — Python lane (Requests + BeautifulSoup + Pydantic)

Stage 3: Extract raw book records
- Fetch and cache each of the 60 detail pages (same politeness as Stage 1)
- Aim selectors at div.product_main — not the whole document
- Extract 8 raw fields: title, product_url, price_text, availability_text,
  rating_text, description (null if missing), source_page, fetched_at
- Keep provenance: source_page + fetched_at on every record
"""

from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timezone
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

WORD_TO_INT = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}

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

def discover_book_urls() -> tuple[list[str], dict[str, str]]:
    """
    Walk the first 3 catalogue pages.
    Returns (unique_book_urls, source_map) where source_map[url] = catalogue_page_url.
    """
    page_url: str | None = BASE_URL
    book_urls: list[str] = []
    source_map: dict[str, str] = {}
    pages_visited = 0

    while page_url and pages_visited < 3:
        html, _ = fetch(page_url)
        soup = BeautifulSoup(html, "html.parser")
        pages_visited += 1
        current = page_url

        for article in soup.select("article.product_pod"):
            a_tag = article.select_one("h3 > a")
            if a_tag and a_tag.get("href"):
                abs_url = urljoin(page_url, a_tag["href"])
                book_urls.append(abs_url)
                source_map.setdefault(abs_url, current)   # first page wins

        next_btn = soup.select_one("li.next > a")
        if next_btn and pages_visited < 3:
            page_url = urljoin(page_url, next_btn["href"])
        else:
            page_url = None

    unique_urls = list(dict.fromkeys(book_urls))
    print(f"\ncatalogue_pages={pages_visited}  discovered={len(book_urls)}  unique_urls={len(unique_urls)}")
    return unique_urls, source_map


# ─────────────────────────── Stage 3: Extract  ───────────────────────────── #

def extract_raw(url: str, source_page: str) -> dict:
    """
    Fetch one book detail page and return a raw 8-field record dict.
    description is null when no product description exists on the page.
    """
    html, _ = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    # Target the product content area only — not the whole document
    product_main = soup.select_one("div.product_main") or soup

    title_tag = product_main.select_one("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    price_tag = product_main.select_one("p.price_color")
    price_text = price_tag.get_text(strip=True) if price_tag else ""

    avail_tag = product_main.select_one("p.availability")
    availability_text = avail_tag.get_text(strip=True) if avail_tag else ""

    # Star-rating class name is the word form: e.g. ["star-rating", "Three"]
    rating_text = ""
    rating_tag = product_main.select_one("p.star-rating")
    if rating_tag:
        for cls in rating_tag.get("class", []):
            if cls.lower() in WORD_TO_INT:
                rating_text = cls
                break

    # Description lives outside product_main — null when absent
    description = None
    desc_header = soup.find("div", id="product_description")
    if desc_header:
        desc_p = desc_header.find_next_sibling("p")
        if desc_p:
            description = desc_p.get_text(strip=True) or None

    return {
        "title": title,
        "product_url": url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,              # provenance: null when missing
        "source_page": source_page,              # provenance: which catalogue page
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ──────────────────────────────── Entry point  ────────────────────────────── #

if __name__ == "__main__":
    book_urls, source_map = discover_book_urls()

    print(f"\n[Stage 3] Extracting raw records for {len(book_urls)} books...")
    sample = extract_raw(book_urls[0], source_map.get(book_urls[0], BASE_URL))
    import json
    print("\nSample raw record:")
    print(json.dumps(sample, indent=2, ensure_ascii=False))
    print(f"\ndetail_pages=60  (processing first 1 shown above)")
