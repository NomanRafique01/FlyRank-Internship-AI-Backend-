"""
FlyRank Internship · Backend Track · Week 5 · Assignment A9
The Polite Scraper — Python lane (Requests + BeautifulSoup + Pydantic)

Stages covered:
  0  Target classification (see README)
  1  Fetch once, cache once
  2  Find all three catalogue pages
  3  Extract raw book records
  4  Normalise, validate, store  → output/books.json
  5  Survive failures, report     → output/run-report.json
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, ValidationError, field_validator

# ─────────────────────────────  Constants  ────────────────────────────────── #

BASE_URL = "https://books.toscrape.com/"
CATALOGUE_BASE = "https://books.toscrape.com/catalogue/"
ROBOTS_URL = "https://books.toscrape.com/robots.txt"

REPO_URL = "https://github.com/your-username/FlyRank-Internship-AI-Backend-"
USER_AGENT = f"FlyRankInternship-A9/1.0 (+{REPO_URL})"

TIMEOUT = 10          # seconds per request
DELAY = 0.6           # seconds between real (non-cached) HTTP requests
MAX_RETRIES = 1       # one retry on 5xx only

CACHE_DIR = Path(__file__).parent.parent / "cache"
OUTPUT_DIR = Path(__file__).parent.parent / "output"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────── Pydantic Schema  ─────────────────────────────── #

WORD_TO_INT = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
}


class BookRecord(BaseModel):
    """Validated, normalised book record."""
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float
    availability_text: str
    in_stock: bool
    rating_text: str
    rating: Optional[int]
    description: Optional[str]
    source_page: HttpUrl
    fetched_at: str   # ISO-8601 UTC

    @field_validator("price_gbp")
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("price_gbp must be ≥ 0")
        return v

    @field_validator("product_url", "source_page", mode="before")
    @classmethod
    def url_must_be_https(cls, v: str) -> str:
        if not str(v).startswith("https://"):
            raise ValueError(f"URL must start with https://: {v}")
        return v


# ──────────────────────────── HTTP helpers  ───────────────────────────────── #

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})

_last_request_time: float = 0.0   # module-level throttle


def _cache_key(url: str) -> Path:
    """Return a deterministic cache-file path for a URL."""
    slug = re.sub(r"[^\w]", "_", url)[:80]
    digest = hashlib.md5(url.encode()).hexdigest()[:8]
    return CACHE_DIR / f"{slug}_{digest}.html"


def fetch(url: str) -> tuple[str, bool]:
    """
    Return (html_text, from_cache).
    Reads from disk cache if available; otherwise fetches with politeness.
    Raises requests.HTTPError on non-200, with one retry on 5xx.
    Does NOT retry on 404 or 403 (see Stage 5 rules).
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

    attempt = 0
    while True:
        try:
            resp = _session.get(url, timeout=TIMEOUT)
        except requests.Timeout:
            raise requests.Timeout(f"Timed out fetching {url}")

        _last_request_time = time.monotonic()

        if resp.status_code == 200:
            resp.encoding = resp.apparent_encoding or "utf-8"
            html = resp.text
            cache_path.write_text(html, encoding="utf-8")
            print(f"  FETCH      {url}  ({len(html):,} bytes)")
            return html, False

        # Retry once on 5xx
        if resp.status_code >= 500 and attempt < MAX_RETRIES:
            attempt += 1
            print(f"  RETRY ({attempt})  {url}  status={resp.status_code}")
            time.sleep(DELAY * 2)
            continue

        resp.raise_for_status()  # 4xx → HTTPError, no retry


# ─────────────────────────── Stage 0 helper  ─────────────────────────────── #

def check_robots() -> str:
    """Fetch robots.txt and return a summary string."""
    try:
        resp = _session.get(ROBOTS_URL, timeout=TIMEOUT)
        if resp.status_code == 200:
            return resp.text.strip()
        return f"robots.txt returned status {resp.status_code}"
    except Exception as exc:
        return f"no robots file found ({exc})"


# ─────────────────────────── Stage 2: Discover  ──────────────────────────── #

def discover_book_urls() -> list[str]:
    """
    Walk the first 3 catalogue pages, collect all book URLs, deduplicate.
    Returns a list of absolute URLs.
    """
    page_url = BASE_URL
    book_urls: list[str] = []
    pages_visited = 0

    while page_url and pages_visited < 3:
        html, _ = fetch(page_url)
        soup = BeautifulSoup(html, "html.parser")
        pages_visited += 1

        # Collect links on this catalogue page
        for article in soup.select("article.product_pod"):
            a_tag = article.select_one("h3 > a")
            if a_tag and a_tag.get("href"):
                # urljoin resolves relative hrefs correctly for both the home
                # page ("catalogue/book/index.html") and inner pages
                # ("book/index.html" relative to ".../catalogue/page-2.html")
                abs_url = urljoin(page_url, a_tag["href"])
                book_urls.append(abs_url)

        # Follow "next" link (up to page 3)
        next_btn = soup.select_one("li.next > a")
        if next_btn and pages_visited < 3:
            page_url = urljoin(page_url, next_btn["href"])
        else:
            page_url = None

    unique_urls = list(dict.fromkeys(book_urls))   # deduplicate, preserve order
    print(f"\ncatalogue_pages={pages_visited}  discovered={len(book_urls)}  unique_urls={len(unique_urls)}")
    return unique_urls


# ─────────────────────────── Stage 3: Extract  ───────────────────────────── #

def extract_raw(url: str, source_page: str) -> dict:
    """Scrape one book detail page and return a raw record dict."""
    html, _ = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    # Target the product content area only
    product_main = soup.select_one("div.product_main") or soup

    title_tag = product_main.select_one("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    price_tag = product_main.select_one("p.price_color")
    price_text = price_tag.get_text(strip=True) if price_tag else ""

    avail_tag = product_main.select_one("p.availability")
    availability_text = avail_tag.get_text(strip=True) if avail_tag else ""

    rating_tag = product_main.select_one("p.star-rating")
    rating_text = ""
    if rating_tag:
        classes = rating_tag.get("class", [])
        # e.g. ["star-rating", "Three"]
        for cls in classes:
            if cls.lower() in WORD_TO_INT:
                rating_text = cls
                break

    # Description is in the product description tab, outside product_main
    desc_header = soup.find("div", id="product_description")
    description = None
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
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ─────────────────────────── Stage 4: Normalise  ─────────────────────────── #

def normalise_and_validate(raw: dict) -> tuple[Optional[BookRecord], Optional[str]]:
    """
    Normalise raw fields and validate with Pydantic.
    Returns (BookRecord, None) on success or (None, error_reason) on failure.
    """
    # price_text  → price_gbp
    price_match = re.search(r"[\d]+\.[\d]+", raw.get("price_text", ""))
    price_gbp = float(price_match.group()) if price_match else -1.0

    # availability_text → in_stock
    avail_lower = raw.get("availability_text", "").lower()
    in_stock = "in stock" in avail_lower

    # rating_text → rating integer
    rating_text = raw.get("rating_text", "")
    rating = WORD_TO_INT.get(rating_text.lower())

    try:
        record = BookRecord(
            title=raw["title"],
            product_url=raw["product_url"],
            price_text=raw["price_text"],
            price_gbp=price_gbp,
            availability_text=raw["availability_text"],
            in_stock=in_stock,
            rating_text=rating_text,
            rating=rating,
            description=raw.get("description"),
            source_page=raw["source_page"],
            fetched_at=raw["fetched_at"],
        )
        return record, None
    except ValidationError as exc:
        return None, str(exc)


# ─────────────────────────── Stage 5: Run  ───────────────────────────────── #

def run(extra_urls: list[str] | None = None) -> None:
    """
    Full scraper pipeline.
    Pass extra_urls to inject deliberate failures for testing Stage 5.
    """
    start_time = datetime.now(timezone.utc)
    start_mono = time.monotonic()

    print("=" * 60)
    print("FlyRankInternship-A9  polite scraper  starting…")
    print(f"User-Agent: {USER_AGENT}")
    print("=" * 60)

    # ── Stage 0: robots check ──────────────────────────────────────────────
    print("\n[Stage 0] robots.txt check")
    robots = check_robots()
    print(robots[:300])

    # ── Stage 2: discover book URLs ────────────────────────────────────────
    print("\n[Stage 2] Discovering catalogue pages…")
    book_urls = discover_book_urls()

    if extra_urls:
        book_urls += extra_urls
        print(f"  + {len(extra_urls)} injected URL(s) for failure testing")

    # ── Stage 3 + 4 + 5: fetch, extract, validate ─────────────────────────
    print(f"\n[Stage 3–5] Processing {len(book_urls)} URLs…")

    valid_records: list[dict] = []
    error_records: list[dict] = []
    pages_fetched = 0
    cache_hits = 0
    failed_pages = 0
    seen_urls: set[str] = set()

    # Track which source page each book came from (for provenance)
    source_lookup: dict[str, str] = {}
    _build_source_map(book_urls, source_lookup)

    for url in book_urls:
        canonical = str(url)
        if canonical in seen_urls:
            continue   # idempotency: skip duplicate URLs
        seen_urls.add(canonical)

        source_page = source_lookup.get(canonical, BASE_URL)

        try:
            raw = extract_raw(canonical, source_page)
            # Track fetch stats
            cache_path = _cache_key(canonical)
            # cache_path exists before extract_raw → it was a cache hit during this call
            # We check by seeing if file existed before we called fetch
            # Simpler: fetch() already printed CACHE HIT or FETCH → track via a wrapper
            pages_fetched += 1

            record, error = normalise_and_validate(raw)
            if record:
                valid_records.append(
                    json.loads(record.model_dump_json())
                )
            else:
                error_records.append({
                    "product_url": canonical,
                    "raw": raw,
                    "reason": error,
                })
        except Exception as exc:
            print(f"  FAILED     {canonical}  — {exc}")
            failed_pages += 1
            error_records.append({
                "product_url": canonical,
                "reason": str(exc),
            })

    # ── Stage 4: idempotent write ──────────────────────────────────────────
    books_path = OUTPUT_DIR / "books.json"
    # Merge with any existing records (idempotency by canonical URL)
    existing: dict[str, dict] = {}
    if books_path.exists():
        try:
            for r in json.loads(books_path.read_text(encoding="utf-8")):
                existing[r["product_url"]] = r
        except Exception:
            pass

    for r in valid_records:
        existing[r["product_url"]] = r   # overwrite with fresh data

    final_records = list(existing.values())
    books_path.write_text(
        json.dumps(final_records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    errors_path = OUTPUT_DIR / "errors.json"
    errors_path.write_text(
        json.dumps(error_records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ── Stage 5: run report ────────────────────────────────────────────────
    duration_s = round(time.monotonic() - start_mono, 2)
    run_report = {
        "started_at": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": duration_s,
        "pages_processed": pages_fetched,
        "valid_records": len(valid_records),
        "total_stored": len(final_records),
        "invalid_records": len(error_records),
        "failed_pages": failed_pages,
        "robots_txt": robots[:200],
    }
    report_path = OUTPUT_DIR / "run-report.json"
    report_path.write_text(
        json.dumps(run_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print("Run complete.")
    print(f"  books.json      : {len(final_records)} records")
    print(f"  errors.json     : {len(error_records)} records")
    print(f"  failed_pages    : {failed_pages}")
    print(f"  duration        : {duration_s}s")
    print("=" * 60)
    if final_records:
        print("\nSample record:")
        print(json.dumps(final_records[0], indent=2))
    else:
        print("No records stored.")


# ──────────────── Source-page provenance helper  ──────────────────────────── #

def _build_source_map(book_urls: list[str], mapping: dict[str, str]) -> None:
    """
    Walk the three catalogue pages and map each book URL → the catalogue page
    it was discovered on, for provenance tracking.
    """
    page_url: Optional[str] = BASE_URL
    pages_visited = 0

    while page_url and pages_visited < 3:
        cache_path = _cache_key(page_url)
        if not cache_path.exists():
            break   # catalogue not yet cached — skip (will be set during discover)

        html = cache_path.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")
        pages_visited += 1
        current_page_url = page_url

        for article in soup.select("article.product_pod"):
            a_tag = article.select_one("h3 > a")
            if a_tag and a_tag.get("href"):
                abs_url = urljoin(page_url, a_tag["href"])
                if abs_url not in mapping:
                    mapping[abs_url] = current_page_url

        next_btn = soup.select_one("li.next > a")
        if next_btn and pages_visited < 3:
            page_url = urljoin(page_url, next_btn["href"])
        else:
            page_url = None


# ──────────────────────────────── Entry point  ────────────────────────────── #

if __name__ == "__main__":
    import sys

    # Stage 5 test: pass --inject-fake to add a bad URL
    fake_urls = []
    if "--inject-fake" in sys.argv:
        fake_urls = ["https://books.toscrape.com/catalogue/this-book-does-not-exist/index.html"]
        print("WARNING: Injecting one fake URL to test failure handling")

    run(extra_urls=fake_urls if fake_urls else None)
