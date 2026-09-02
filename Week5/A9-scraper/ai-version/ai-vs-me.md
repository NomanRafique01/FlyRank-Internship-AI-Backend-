# Bonus Stage B — AI vs Me

## The prompt I gave the AI

> Build a Python web scraper for Books to Scrape (https://books.toscrape.com).
>
> Requirements:
> - Target: exactly the first 3 catalogue pages, then follow each of the 60 book detail pages
> - HTTP library: `requests`; HTML parser: `beautifulsoup4`; schema validator: `pydantic`
> - User-Agent header: `FlyRankInternship-A9/1.0 (+https://github.com/your-username/repo)`
> - Timeout: 10 seconds per request
> - Delay: at least 500 ms between every real (non-cached) HTTP request
> - Cache: save each fetched HTML to `cache/<slug>_<md5>.html`; on second run read from cache (print `CACHE HIT`) instead of fetching (print `FETCH`)
> - Status check: only HTTP 200 is valid; anything else is a failed fetch
> - Raw record fields (8): title, product_url, price_text, availability_text, rating_text, description (null if missing), source_page, fetched_at (ISO-8601 UTC)
> - Normalisation: add price_gbp (float, strip £), in_stock (bool), rating (int 1–5)
> - Pydantic model: validate every record; failures go to output/errors.json with a reason; successes go to output/books.json
> - Idempotency: running twice must produce exactly 60 records, not 120
> - Failure handling: catch per-page exceptions, log and skip; one retry on 5xx only (no retry on 404/403); one fake URL can be injected via --inject-fake flag
> - Run report: write output/run-report.json with started_at, duration_seconds, pages_processed, valid_records, total_stored, invalid_records, failed_pages
> - No browser needed (data is server-rendered HTML)

---

## Checkpoint results

| Checkpoint | My version | AI version |
|-----------|-----------|-----------|
| `catalogue_pages=3 discovered=60 unique_urls=60` | ✅ | ✅ |
| Second run reads from cache, same 60 records | ✅ | ✅ |
| `books.json` has exactly 60 records | ✅ | ✅ |
| Fake URL logs failure, run still finishes | ✅ | ✅ |
| `run-report.json` has all required fields | ✅ | ✅ |
| `price_gbp` is a float, URLs start with `https://` | ✅ | ✅ |

---

## What the AI did better — and do I understand it?

1. **Cleaner session reuse** — the AI immediately wrapped the `requests.Session` inside a context manager class, making teardown explicit. I used a module-level `_session` which works but is less clean for testing. Yes, I understand it — it's standard Python context protocol.

2. **More Pythonic URL joining** — the AI used `urllib.parse.urljoin` throughout without the `replace("../", "")` workaround I needed for some relative paths. Understanding the difference pointed me to a subtle bug in my own link resolution.

3. **Typed return values on helpers** — the AI typed every helper with full `-> tuple[str, bool]` annotations from the start. My version added them after the fact.

---

## What the AI got wrong or silently skipped

1. **No idempotency on re-run** — the AI wrote `books.json` by simply overwriting with the current run's records. On a partial run (e.g. network drops at book 40) a rerun would produce 40 records, not 60. My version merges with any existing records keyed by `product_url`.

2. **No per-page retry on 5xx** — the AI's version raised immediately on any non-200 status. My version retries once on 5xx and only skips on 4xx.

3. **Provenance `source_page` was always `BASE_URL`** — the AI set `source_page` to the base URL instead of mapping each book back to the catalogue page it was discovered on. Minor but it breaks the provenance requirement.

4. **Description selector was too broad** — the AI used `soup.find("p")` after the `#product_description` header, which on some pages returned an empty paragraph instead of `null`. My version guards with `or None`.

---

## What my prompt forgot to say

1. I didn't specify that `source_page` must be the specific catalogue page URL (page-1, page-2, page-3), not just the base URL — the AI defaulted to the base URL.
2. I didn't mention the `--inject-fake` CLI flag explicitly — the AI added a hardcoded test URL instead.
3. I didn't say "merge with existing `books.json` on re-run" — the AI overwrote it each time.

---

## One rematch — what changed after an improved prompt

Added to the prompt:
> - `source_page` must be the specific catalogue page URL the book was discovered on (e.g. `https://books.toscrape.com/catalogue/page-2.html`), not the home page
> - Idempotency: merge new records into `books.json` by `product_url` key so a rerun never duplicates
> - Accept `--inject-fake` as a CLI flag to add one broken URL for testing

**Result:** All three issues were fixed in the second generation. The AI also picked up the `lxml` parser hint without being told, which was a nice bonus.

---

## Conclusion

The AI's output was a solid 80% solution in ~30 seconds. The missing 20% — idempotency, correct provenance, careful retry logic — required understanding the problem deeply enough to spot what was missing. That understanding only came from building it by hand first. Both halves of the assignment are necessary.
