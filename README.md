# Web Scraping Assignment – Multi-Source Scraping & Data Consolidation

## Project Overview

A Python-based web scraping and data-processing pipeline that:

1. Scrapes **Books to Scrape** and **Quotes to Scrape** across all available pages.
2. Cleans and standardises both datasets into a single common schema.
3. Validates each record against a set of defined rules.
4. Detects and removes duplicates using a normalised composite key.
5. Writes a consolidated CSV (`output/final_dataset.csv`) and a JSON summary report (`output/summary_report.json`).

---

## Python Version

Developed and tested with **Python 3.13.2**.  
Python 3.10+ is required (uses `X | Y` union type hints).

---

## Installation & Setup

```bash
# 1. Clone / unzip the project folder
cd Web_Scrapping

# 2. (Recommended) Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Dependencies

| Package         | Purpose                         |
|-----------------|---------------------------------|
| `requests`      | HTTP requests with retry logic  |
| `beautifulsoup4`| HTML parsing                    |
| `lxml`          | Fast HTML parser backend for BS4|

All pinned versions are in `requirements.txt`.

---

## How to Run the Scraper

```bash
python main.py
```

This runs the full pipeline and writes:
- `output/final_dataset.csv`
- `output/summary_report.json`
- `logs/scrape_<timestamp>.log`

### Running the Unit Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## How Pagination Works

### Books to Scrape

1. The scraper loads the **home page** and reads the sidebar category list.
2. For each category it fetches the first page of that category.
3. After parsing the books on that page it looks for a `<li class="next"> <a>` element.
4. If found, the `href` is resolved relative to the current URL and requested next.
5. This continues until no next-page link is present.

No page URLs are hard-coded; the scraper follows links automatically.

### Quotes to Scrape

1. The scraper begins at `https://quotes.toscrape.com/`.
2. After parsing each page's quotes it looks for a `<li class="next"> <a>` element.
3. The `href` is resolved and requested next.
4. Pagination ends when no next-page link exists.

---

## Project Structure

```
Web_Scrapping/
├── scrapers/
│   ├── __init__.py
│   ├── books_scraper.py    # Books to Scrape – all selectors isolated here
│   └── quotes_scraper.py   # Quotes to Scrape – all selectors isolated here
├── processing/
│   ├── __init__.py
│   ├── cleaning.py         # Pure transformation functions
│   ├── validation.py       # Per-record validation rules
│   └── deduplication.py    # Duplicate detection & removal
├── tests/
│   ├── __init__.py
│   ├── test_cleaning.py
│   ├── test_validation.py
│   └── test_deduplication.py
├── output/                 # Generated at runtime
│   ├── final_dataset.csv
│   └── summary_report.json
├── logs/                   # Generated at runtime
│   └── scrape_<timestamp>.log
├── main.py                 # Pipeline orchestrator
├── requirements.txt
├── README.md
└── AI_USAGE.md
```

---

## Data Model

All records share this common schema regardless of source:

| Field          | Type          | Books to Scrape | Quotes to Scrape |
|----------------|---------------|-----------------|------------------|
| `source`       | string        | "Books to Scrape" | "Quotes to Scrape" |
| `source_url`   | string (URL)  | Individual book product page URL | Author detail page URL |
| `name_or_title`| string        | Book title      | Full quote text  |
| `category`     | string        | Category name   | `null`           |
| `price`        | float         | Price in GBP (numeric) | `null`   |
| `availability` | string        | "In stock" / "Out of stock" | `null` |
| `rating`       | integer (1–5) | Star rating     | `null`           |
| `author`       | string        | `null`          | Author name      |
| `tags`         | string        | `null`          | Comma-separated tags |
| `description`  | string        | `null`          | `null` (not available on listing pages) |
| `scraped_at`   | ISO-8601 UTC  | Timestamp       | Timestamp        |

Fields that do not apply for a source are stored as empty (blank) in CSV, which reads as `null`/`NaN` in pandas.

---

## Cleaning Approach

All cleaning logic is in `processing/cleaning.py`. Functions are pure (no I/O):

| Step | Function | What it does |
|------|----------|--------------|
| Whitespace | `clean_text()` | Strips leading/trailing spaces; collapses internal runs to a single space; returns `None` for blank strings |
| Price | `clean_price()` | Extracts the numeric portion from strings like `"£12.99"` or `"Â£12.99"` using regex; returns `float` or `None` |
| Rating | `clean_rating()` | Accepts an integer, digit string, or word (`"Three"`) and returns an `int` in [1, 5] or `None` |
| URL | `clean_url()` | Validates scheme (http/https) and presence of a host; returns `None` for invalid URLs |
| Availability | `clean_availability()` | Normalises to `"In stock"` / `"Out of stock"` by substring match; otherwise returns cleaned text |
| Tags | `clean_tags()` | Splits on comma, strips each tag, lower-cases, deduplicates, sorts; returns `None` for empty |

---

## Validation Approach

Logic is in `processing/validation.py`. Each record is checked against five rules:

1. **source** must be non-empty and one of the known source names.
2. **source_url** must be present and have an http/https scheme with a non-empty host.
3. **name_or_title** must be non-empty (this is the primary identifier of a record).
4. **price**, when present, must be a `float` or `int` (the cleaning step converts it; a non-numeric value that survived cleaning is a data problem).
5. **rating**, when present, must be an integer in [1, 5].

Records that fail any rule are collected separately; they do **not** appear in the final dataset. Each rejected record retains a `_validation_errors` list explaining why it failed.

---

## Deduplication Approach

Logic is in `processing/deduplication.py`.

**Key used:**

```
(normalise(source), normalise(name_or_title))
```

**Normalisation** means: lower-case, strip leading/trailing whitespace, collapse internal whitespace runs to a single space.

**Why this key:**
- A composite key avoids false positives when the same title appears on different sources.
- Whitespace and casing normalisation catches variants like `"A Book"`, `" A Book "`, and `"A BOOK"` as the same record.

**Outcome:**
- The **first occurrence** of each key is kept (`_is_duplicate = False`).
- Subsequent occurrences are **removed** from the final dataset (`_is_duplicate = True`).
- The duplicate count is reported in the summary.

Duplicates are removed rather than flagged in the CSV because Books to Scrape returns the same book on every category page it belongs to; keeping flagged duplicates would inflate the dataset without adding value.

---

## Error Handling Approach

Both scrapers share the same request pattern:

- Up to **3 retries** per page with **exponential back-off** (2 s, 4 s).
- `ConnectionError`, `Timeout`, and `HTTPError` are each caught and logged individually.
- HTTP 404/410 responses do not trigger retries (the page does not exist).
- If a single **book card** or **quote div** raises an exception during parsing, that card is skipped and a warning is logged; the rest of the page continues.
- If an **entire page** fetch fails after all retries, the scraper logs an error and moves to the next page (or next category for books).
- If an entire **category** (books) fails, the error is caught in the main loop and the next category continues.
- Scraper failures do not crash the pipeline; the other source continues independently.
- A **1-second delay** between requests is applied throughout to avoid aggressive traffic.

---

## Output Description

### `output/final_dataset.csv`

UTF-8 CSV. Columns: `source`, `source_url`, `name_or_title`, `category`, `price`, `availability`, `rating`, `author`, `tags`, `description`, `scraped_at`.

### `output/summary_report.json`

```json
{
  "pipeline_started_at": "...",
  "sources": {
    "books_to_scrape": {
      "raw_records_collected": ...,
      "records_after_cleaning": ...,
      "records_rejected_validation": ...
    },
    "quotes_to_scrape": { ... }
  },
  "totals": {
    "total_raw_records": ...,
    "total_after_cleaning": ...,
    "total_rejected_validation": ...,
    "total_duplicates_removed": ...,
    "total_final_records": ...
  },
  "pipeline_finished_at": "...",
  "execution_time_seconds": ...
}
```

### `logs/scrape_<timestamp>.log`

Full `DEBUG`-level log written to file. `INFO`-level also streams to stdout.

---

## Assumptions

1. The structure of both practice sites remains consistent with what was observed during development.
2. Both sites are publicly accessible without authentication or CAPTCHA.
3. The `<li class="next">` pattern reliably signals the presence of a next page on both sites.
4. Book descriptions are only available on individual product pages; scraping them would require one HTTP request per book (1000+ requests). They are left `null` on listing-page scrapes to avoid unnecessary traffic.
5. Quotes do not have prices, categories, availability, or ratings; these fields are stored as `null`.
6. Books do not have authors or tags on listing pages; these fields are stored as `null`.

---

## Known Limitations

1. **Book descriptions** are not scraped. They require fetching each individual product page. This would multiply HTTP requests by ~20× and was excluded per the principle of avoiding aggressive traffic.
2. **Author bio details** for quotes (birth date, location) are not scraped. The author detail page URL is captured as `source_url`; fetching each would add many requests.
3. The scraper is single-threaded. A full run of all ~1000 books with 1-second delays takes approximately 20–30 minutes. This is intentional to respect rate limits.
4. If either site changes its HTML structure, the CSS selectors in the respective scraper module will need to be updated.
