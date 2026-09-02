"""
AI-generated version of the polite scraper (Bonus Stage B).
Isolated in ai-version/ — the hand-built version in src/main.py is untouched.

This file was produced by asking an AI to implement the full A9 spec,
then reviewed and diff'd against the hand-built version (see ai-vs-me.md).
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

BASE_URL = "https://books.toscrape.com/"
CATALOGUE_BASE = "https://books.toscrape.com/catalogue/"
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/your-username/repo)"
TIMEOUT = 10
DELAY = 0.6

CACHE_DIR = Path(__file__).parent.parent / "cache"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WORD_TO_INT = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}


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
    def positive_price(cls, v: float) -> float:
        if v < 0:
            raise ValueError("price_gbp must be >= 0")
        return v


class Scraper:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._last_req = 0.0

    def _cache_path(self, url: str) -> Path:
        slug = re.sub(r"[^\w]", "_", url)[:80]
        md5 = hashlib.md5(url.encode()).hexdigest()[:8]
        return CACHE_DIR / f"{slug}_{md5}.html"

    def fetch(self, url: str) -> tuple[str, bool]:
        cp = self._cache_path(url)
        if cp.exists():
            print(f"  CACHE HIT  {url}")
            return cp.read_text(encoding="utf-8"), True

        elapsed = time.monotonic() - self._last_req
        if elapsed < DELAY:
            time.sleep(DELAY - elapsed)

        resp = self.session.get(url, timeout=TIMEOUT)
        self._last_req = time.monotonic()

        if resp.status_code == 200:
            cp.write_text(resp.text, encoding="utf-8")
            print(f"  FETCH      {url}  ({len(resp.text):,} bytes)")
            return resp.text, False

        resp.raise_for_status()
        raise RuntimeError("unreachable")

    def discover(self) -> tuple[list[str], dict[str, str]]:
        """Return (book_urls, source_map)."""
        book_urls: list[str] = []
        source_map: dict[str, str] = {}
        page_url: Optional[str] = BASE_URL
        pages = 0

        while page_url and pages < 3:
            html, _ = self.fetch(page_url)
            soup = BeautifulSoup(html, "html.parser")
            pages += 1
            current = page_url

            for art in soup.select("article.product_pod"):
                a = art.select_one("h3 > a")
                if a and a.get("href"):
                    abs_url = urljoin(CATALOGUE_BASE, a["href"].replace("../", ""))
                    book_urls.append(abs_url)
                    source_map.setdefault(abs_url, current)

            nxt = soup.select_one("li.next > a")
            page_url = urljoin(page_url, nxt["href"]) if nxt and pages < 3 else None

        unique = list(dict.fromkeys(book_urls))
        print(f"\ncatalogue_pages={pages}  discovered={len(book_urls)}  unique_urls={len(unique)}")
        return unique, source_map

    def extract_raw(self, url: str, source_page: str) -> dict:
        html, _ = self.fetch(url)
        soup = BeautifulSoup(html, "html.parser")
        pm = soup.select_one("div.product_main") or soup

        title = (pm.select_one("h1") or soup).get_text(strip=True)
        price_text = (pm.select_one("p.price_color") or soup).get_text(strip=True)
        avail_text = (pm.select_one("p.availability") or soup).get_text(strip=True)

        rating_text = ""
        rt = pm.select_one("p.star-rating")
        if rt:
            for cls in rt.get("class", []):
                if cls.lower() in WORD_TO_INT:
                    rating_text = cls
                    break

        description = None
        dh = soup.find("div", id="product_description")
        if dh:
            dp = dh.find_next_sibling("p")
            if dp:
                description = dp.get_text(strip=True) or None

        return {
            "title": title,
            "product_url": url,
            "price_text": price_text,
            "availability_text": avail_text,
            "rating_text": rating_text,
            "description": description,
            "source_page": source_page,
            "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def normalise(self, raw: dict) -> tuple[Optional[BookRecord], Optional[str]]:
        m = re.search(r"[\d]+\.[\d]+", raw.get("price_text", ""))
        price_gbp = float(m.group()) if m else -1.0
        in_stock = "in stock" in raw.get("availability_text", "").lower()
        rating = WORD_TO_INT.get(raw.get("rating_text", "").lower())
        try:
            return BookRecord(
                price_gbp=price_gbp,
                in_stock=in_stock,
                rating=rating,
                **{k: raw[k] for k in ("title", "product_url", "price_text",
                                       "availability_text", "rating_text",
                                       "description", "source_page", "fetched_at")},
            ), None
        except ValidationError as e:
            return None, str(e)

    def run(self, extra_urls: list[str] | None = None) -> None:
        start = datetime.now(timezone.utc)
        t0 = time.monotonic()

        book_urls, source_map = self.discover()
        if extra_urls:
            book_urls += extra_urls

        valid, errors, failed = [], [], 0
        seen: set[str] = set()

        for url in book_urls:
            if url in seen:
                continue
            seen.add(url)
            src = source_map.get(url, BASE_URL)
            try:
                raw = self.extract_raw(url, src)
                record, err = self.normalise(raw)
                if record:
                    valid.append(json.loads(record.model_dump_json()))
                else:
                    errors.append({"product_url": url, "reason": err})
            except Exception as exc:
                print(f"  FAILED {url} — {exc}")
                failed += 1
                errors.append({"product_url": url, "reason": str(exc)})

        # Idempotent merge
        books_path = OUTPUT_DIR / "books.json"
        existing: dict[str, dict] = {}
        if books_path.exists():
            try:
                for r in json.loads(books_path.read_text()):
                    existing[r["product_url"]] = r
            except Exception:
                pass
        for r in valid:
            existing[r["product_url"]] = r

        books_path.write_text(json.dumps(list(existing.values()), indent=2, ensure_ascii=False))
        (OUTPUT_DIR / "errors.json").write_text(json.dumps(errors, indent=2, ensure_ascii=False))

        report = {
            "started_at": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration_seconds": round(time.monotonic() - t0, 2),
            "pages_processed": len(seen),
            "valid_records": len(valid),
            "total_stored": len(existing),
            "invalid_records": len(errors),
            "failed_pages": failed,
        }
        (OUTPUT_DIR / "run-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))

        print(f"\nDone: {len(existing)} stored, {failed} failed, {len(errors)} errors")


if __name__ == "__main__":
    import sys
    extra = ["https://books.toscrape.com/catalogue/fake-book/index.html"] if "--inject-fake" in sys.argv else None
    Scraper().run(extra_urls=extra)
