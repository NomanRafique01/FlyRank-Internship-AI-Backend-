# FlyRank Internship · Week 5 · A9 — The Polite Scraper

A small, polite scraping pipeline that downloads the first three catalogue pages of
[Books to Scrape](https://books.toscrape.com), visits all 60 book pages, turns messy HTML
into clean, Pydantic-validated JSON, survives a broken page without crashing, and ends every
run with an honest run report.

**Lane:** Python — `requests` · `beautifulsoup4` · `pydantic`

---

## Quick start (copy-pasteable)

```bash
# 1. Clone and enter the folder
git clone https://github.com/your-username/FlyRank-Internship-AI-Backend-
cd FlyRank-Internship-AI-Backend-/Week5/A9-scraper

# 2. Create a virtual environment and install dependencies
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt

# 3. Run the scraper
python src/main.py

# 4. Test failure handling (Stage 5)
python src/main.py --inject-fake
```

A clean run produces `output/books.json` (60 records) and `output/run-report.json` in **under 5 minutes**.
A second run reads mostly from `cache/` and produces the same 60 records — no duplicates.

---

## Target classification (Stage 0)

| Item | Detail |
|------|--------|
| **Target site** | [Books to Scrape](https://books.toscrape.com) |
| **Site type** | Public practice sandbox — _"A Fictional Bookshop Designed to Help People Learn Web Scraping"_ (stated on [toscrape.com](https://toscrape.com)) |
| **Scope** | First 3 catalogue pages only → 60 book detail pages |
| **Data collected** | Title, price, availability, star rating, description, source page, fetch timestamp |
| **Why appropriate** | The site was built explicitly for scraping practice. We stay within the 3-page scope and follow all politeness rules. |

### robots.txt result

Fetched `https://books.toscrape.com/robots.txt` — the file returned **HTTP 404** (not found).
A missing `robots.txt` is **not permission** — it simply means no machine-readable rules exist.
The permission here comes from the site's own stated purpose: it is a sandbox built for scraping practice.

> **"I will not reuse this code on another site without checking its rules and terms first."**

---

## Record schema (Stage 4)

Validated by `BookRecord` (Pydantic model in `src/main.py`):

| Field | Type | Notes |
|-------|------|-------|
| `title` | `str` | Required |
| `product_url` | `HttpUrl` | Must start with `https://` |
| `price_text` | `str` | Raw value, e.g. `£51.77` |
| `price_gbp` | `float` | Normalised number ≥ 0 |
| `availability_text` | `str` | Raw value |
| `in_stock` | `bool` | Normalised from availability text |
| `rating_text` | `str` | Word form, e.g. `Three` |
| `rating` | `int \| null` | 1–5 integer |
| `description` | `str \| null` | `null` when not present on page |
| `source_page` | `HttpUrl` | Catalogue page it was discovered on |
| `fetched_at` | `str` | ISO-8601 UTC timestamp |

Records that fail validation are written to `output/errors.json` with a `reason` field —
they never appear in `books.json`.

---

## Politeness rules (Stage 1 & 2)

| Rule | Implementation |
|------|---------------|
| **User-Agent** | `FlyRankInternship-A9/1.0 (+<repo-url>)` on every request |
| **Delay** | ≥ 600 ms between each real HTTP request |
| **Timeout** | 10 s — a request is abandoned after this |
| **Status check** | Only HTTP 200 is treated as valid HTML |
| **Cache** | HTML saved to `cache/`; development reads from disk, never re-fetches |
| **Retry policy** | One retry on 5xx; no retry on 404 or 403 |

---

## Output files

| File | Contents |
|------|----------|
| `output/books.json` | 60 unique, validated book records |
| `output/errors.json` | Records that failed validation, with reason |
| `output/run-report.json` | Start time, duration, counts, failure summary |
| `cache/` | Raw HTML (git-ignored) |

---

## Sample `run-report.json`

```json
{
  "started_at": "2026-09-02T20:39:24Z",
  "duration_seconds": 54.68,
  "pages_processed": 60,
  "valid_records": 60,
  "total_stored": 60,
  "invalid_records": 0,
  "failed_pages": 0,
  "robots_txt": "robots.txt returned status 404"
}
```

---

## Why this assignment needed no browser

The data is already in the HTML the server returns in the initial GET response.
`requests` + `BeautifulSoup` retrieves and parses that HTML directly.
A headless browser (Playwright, Puppeteer) would launch a full rendering engine, execute
JavaScript, and wait for the DOM — adding ~300 MB of RAM and 2–5× the latency for
exactly the same bytes. A browser is only needed when content is injected by
client-side JavaScript _after_ the page loads; Books to Scrape is server-rendered, so a
browser would only add cost.

---

## Ethics note

- Use an official API when one exists — it is more stable, faster, and expressly permitted.
- Never bypass logins, paywalls, CAPTCHA, or explicit `Disallow` rules in `robots.txt`.
- Collect only what you need; don't mirror or republish entire sites.
- Identify yourself with an honest User-Agent that includes a contact link.
- Respect `Retry-After` headers and exponential backoff if a server asks you to slow down.

---

## Commits

```
Stage 0: classify scraping target
Stage 1: fetch and cache HTML
Stage 2: discover three catalogue pages
Stage 3: extract book details
Stage 4: validate normalized records
Stage 5: survive failures, report the run
Stage 6: publish scraper evidence
```

---

## Limitations

- The scraper processes pages sequentially (single-threaded) to keep politeness simple.
  A queued-job approach (A7 pattern) would be needed for larger targets.
- Cache files are keyed by URL hash; if a cached page is stale you must delete `cache/`
  manually to force a re-fetch.
- The scraper targets only the first 3 catalogue pages as required; it does not auto-paginate
  beyond page 3.
