"""
FlyRank Internship · Backend Track · Week 5 · Assignment A9
The Polite Scraper — Python lane (Requests + BeautifulSoup + Pydantic)

Stage 4: Clean it, check it, store it
- BookRecord Pydantic schema: all required fields, types, and constraints
- price_text -> price_gbp (float); availability_text -> in_stock (bool);
  rating_text -> rating (int 1-5)
- Every record validated before storage; failures go to output/errors.json
- output/books.json: exactly 60 unique records, idempotent across reruns
  (merge by canonical product_url — rerun never duplicates)
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
REPO_URL = "https://github.com/your-username/FlyRank-Internship-AI-Backend-"
USER_AGENT = f"FlyRankInternship-A9/1.0 (+{REPO_URL})"

TIMEOUT = 10
DELAY   = 0.6

WORD_TO_INT = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}

CACHE_DIR  = Path(__file__).parent.parent / "cache"
OUTPUT_DIR = Path(__file__).parent.parent / "output"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────── Pydantic Schema  ─────────────────────────────── #

class BookRecord(BaseModel):
    """Validated, normalised book record — the single source of truth for shape."""
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float           # normalised from price_text
    availability_text: str
    in_stock: bool             # normalised from availability_text
    rating_text: str
    rating: Optional[int]      # 1-5 integer; null when not parseable
    description: Optional[str]
    source_page: HttpUrl
    fetched_at: str            # ISO-8601 UTC

    @field_validator("price_gbp")
    @classmethod
    def price_must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("price_gbp must be >= 0")
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
    """
    Normalise raw fields and validate with Pydantic.
    Returns (BookRecord, None) on success, or (None, reason) on failure.
    """
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


def store(valid_records: list[dict], error_records: list[dict]) -> None:
    """
    Idempotent write: merge new records into books.json by product_url.
    A rerun overwrites existing records for the same URL — never duplicates.
    """
    books_path = OUTPUT_DIR / "books.json"
    existing: dict[str, dict] = {}
    if books_path.exists():
        try:
            for r in json.loads(books_path.read_text(encoding="utf-8")):
                existing[r["product_url"]] = r
        except Exception:
            pass

    for r in valid_records:
        existing[r["product_url"]] = r     # fresh data wins

    books_path.write_text(
        json.dumps(list(existing.values()), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "errors.json").write_text(
        json.dumps(error_records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n  books.json  : {len(existing)} records")
    print(f"  errors.json : {len(error_records)} records")


# ──────────────────────────────── Entry point  ────────────────────────────── #

if __name__ == "__main__":
    book_urls, source_map = discover_book_urls()

    valid_records: list[dict] = []
    error_records: list[dict] = []

    for url in book_urls:
        src = source_map.get(url, BASE_URL)
        raw = extract_raw(url, src)
        record, err = normalise_and_validate(raw)
        if record:
            valid_records.append(json.loads(record.model_dump_json()))
        else:
            error_records.append({"product_url": url, "reason": err})

    store(valid_records, error_records)
    print("\nSample record:")
    if valid_records:
        print(json.dumps(valid_records[0], indent=2))
