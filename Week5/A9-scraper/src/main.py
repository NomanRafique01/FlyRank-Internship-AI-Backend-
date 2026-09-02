"""
FlyRank Internship · Backend Track · Week 5 · Assignment A9
The Polite Scraper — Python lane (Requests + BeautifulSoup + Pydantic)

Stage 5: Survive failures, report the run
- Per-page exception handling: one broken page is logged and skipped
- One retry on 5xx (server error); no retry on 404/403 (asking again is a pest)
- output/run-report.json: started_at, duration, pages_processed, valid_records,
  total_stored, invalid_records, failed_pages, robots_txt
- Pass --inject-fake to add a deliberate bad URL for testing (never hammer real site)
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, ValidationError, field_validator

# ─────────────────────────────  Constants  ────────────────────────────────── #

BASE_URL   = "https://books.toscrape.com/"
ROBOTS_URL = "https://books.toscrape.com/robots.txt"
REPO_URL   = "https://github.com/your-username/FlyRank-Internship-AI-Backend-"
USER_AGENT = f"FlyRankInternship-A9/1.0 (+{REPO_URL})"

TIMEOUT     = 10    # seconds per request
DELAY       = 0.6   # seconds between real HTTP requests
MAX_RETRIES = 1     # one retry on 5xx only

WORD_TO_INT = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}

CACHE_DIR  = Path(__file__).parent.parent / "cache"
OUTPUT_DIR = Path(__file__).parent.parent / "output"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────── Pydantic Schema  ─────────────────────────────── #

class BookRecord(BaseModel):
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
    fetched_at: str

    @field_validator("price_gbp")
    @classmethod
    def price_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("price_gbp must be >= 0")
        return v

    @field_validator("product_url", "source_page", mode="before")
    @classmethod
    def must_be_https(cls, v: str) -> str:
        if not str(v).startswith("https://"):
            raise ValueError(f"URL must start with https://: {v}")
        return v

# ──────────────────────────── HTTP helpers  ───────────────────────────────── #

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})
_last_request_time: float = 0.0


def _cache_key(url: str) -> Path:
    slug = re.sub(r"[^\w]", "_", url)[:80]
    digest = hashlib.md5(url.encode()).hexdigest()[:8]
    return CACHE_DIR / f"{slug}_{digest}.html"


def fetch(url: str) -> tuple[str, bool]:
    """
    Return (html_text, from_cache).
    One retry on 5xx. No retry on 4xx — 404 won't appear; 403 means stop asking.
    """
    global _last_request_time

    cache_path = _cache_key(url)
    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        print(f"  CACHE HIT  {url}  ({len(html):,} bytes)")
        return html, True

    elapsed = time.monotonic() - _last_request_time
    if elapsed < DELAY:
        time.sleep(DELAY - elapsed)

    attempt = 0
    while True:
        resp = _session.get(url, timeout=TIMEOUT)
        _last_request_time = time.monotonic()

        if resp.status_code == 200:
            resp.encoding = resp.apparent_encoding or "utf-8"
            html = resp.text
            cache_path.write_text(html, encoding="utf-8")
            print(f"  FETCH      {url}  ({len(html):,} bytes)")
            return html, False

        # Retry once on 5xx (server error — might be transient)
        if resp.status_code >= 500 and attempt < MAX_RETRIES:
            attempt += 1
            print(f"  RETRY ({attempt})  {url}  status={resp.status_code}")
            time.sleep(DELAY * 2)
            continue

        # 4xx (including 404, 403) — raise immediately, no retry
        resp.raise_for_status()


def check_robots() -> str:
    """Fetch robots.txt; return its content or a 'not found' note."""
    try:
        resp = _session.get(ROBOTS_URL, timeout=TIMEOUT)
        if resp.status_code == 200:
            return resp.text.strip()
        return f"robots.txt returned status {resp.status_code}"
    except Exception as exc:
        return f"no robots file found ({exc})"


# ─────────────────────────── Stage 2: Discover  ──────────────────────────── #

def discover_book_urls() -> tuple[list[str], dict[str, str]]:
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
                source_map.setdefault(abs_url, current)

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
    html, _ = fetch(url)
    soup = BeautifulSoup(html, "html.parser")
    product_main = soup.select_one("div.product_main") or soup

    title_tag = product_main.select_one("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    price_tag = product_main.select_one("p.price_color")
    price_text = price_tag.get_text(strip=True) if price_tag else ""

    avail_tag = product_main.select_one("p.availability")
    availability_text = avail_tag.get_text(strip=True) if avail_tag else ""

    rating_text = ""
    rating_tag = product_main.select_one("p.star-rating")
    if rating_tag:
        for cls in rating_tag.get("class", []):
            if cls.lower() in WORD_TO_INT:
                rating_text = cls
                break

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
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ─────────────────────────── Stage 4: Normalise & Validate  ──────────────── #

def normalise_and_validate(raw: dict) -> tuple[Optional[BookRecord], Optional[str]]:
    price_match = re.search(r"[\d]+\.[\d]+", raw.get("price_text", ""))
    price_gbp = float(price_match.group()) if price_match else -1.0
    in_stock = "in stock" in raw.get("availability_text", "").lower()
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
    Full pipeline with per-page failure handling and a run report.
    Pass extra_urls to inject deliberate 404s — test failure without touching the site.
    """
    start_time = datetime.now(timezone.utc)
    t0 = time.monotonic()

    print("=" * 60)
    print("FlyRankInternship-A9  polite scraper  starting")
    print(f"User-Agent: {USER_AGENT}")
    print("=" * 60)

    print("\n[Stage 0] Checking robots.txt...")
    robots = check_robots()
    print(f"  {robots[:120]}")

    print("\n[Stage 2] Discovering catalogue pages...")
    book_urls, source_map = discover_book_urls()

    if extra_urls:
        book_urls = book_urls + extra_urls
        print(f"  + {len(extra_urls)} injected URL(s) for failure testing")

    print(f"\n[Stage 3-5] Processing {len(book_urls)} URLs...")

    valid_records: list[dict] = []
    error_records: list[dict] = []
    pages_processed = 0
    failed_pages = 0
    seen: set[str] = set()

    for url in book_urls:
        if url in seen:
            continue
        seen.add(url)

        src = source_map.get(url, BASE_URL)
        try:
            raw = extract_raw(url, src)
            pages_processed += 1
            record, err = normalise_and_validate(raw)
            if record:
                valid_records.append(json.loads(record.model_dump_json()))
            else:
                error_records.append({"product_url": url, "raw": raw, "reason": err})
        except Exception as exc:
            print(f"  FAILED     {url}  -- {exc}")
            failed_pages += 1
            error_records.append({"product_url": url, "reason": str(exc)})

    # Idempotent write (Stage 4)
    books_path = OUTPUT_DIR / "books.json"
    existing: dict[str, dict] = {}
    if books_path.exists():
        try:
            for r in json.loads(books_path.read_text(encoding="utf-8")):
                existing[r["product_url"]] = r
        except Exception:
            pass
    for r in valid_records:
        existing[r["product_url"]] = r
    final_records = list(existing.values())

    books_path.write_text(
        json.dumps(final_records, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUTPUT_DIR / "errors.json").write_text(
        json.dumps(error_records, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Run report
    duration_s = round(time.monotonic() - t0, 2)
    run_report = {
        "started_at": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": duration_s,
        "pages_processed": pages_processed,
        "valid_records": len(valid_records),
        "total_stored": len(final_records),
        "invalid_records": len(error_records),
        "failed_pages": failed_pages,
        "robots_txt": robots[:200],
    }
    (OUTPUT_DIR / "run-report.json").write_text(
        json.dumps(run_report, indent=2, ensure_ascii=False), encoding="utf-8"
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


# ──────────────────────────────── Entry point  ────────────────────────────── #

if __name__ == "__main__":
    extra: list[str] = []
    if "--inject-fake" in sys.argv:
        extra = ["https://books.toscrape.com/catalogue/this-book-does-not-exist/index.html"]
        print("WARNING: Injecting one fake URL to test failure handling")
    run(extra_urls=extra or None)
