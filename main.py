import csv
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from scrapers.books_scraper   import scrape_books
from scrapers.quotes_scraper  import scrape_quotes
from processing.cleaning      import clean_records, SCHEMA_FIELDS
from processing.validation    import validate_records
from processing.deduplication import deduplicate_records

ROOT_DIR   = Path(__file__).parent
OUTPUT_DIR = ROOT_DIR / "output"
LOGS_DIR   = ROOT_DIR / "logs"

OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

LOG_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
LOG_FILE = LOGS_DIR / f"scrape_{LOG_TIMESTAMP}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)-8s] %(name)s – %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("main")


CSV_COLUMNS = [
    "source", "source_url", "name_or_title", "category",
    "price", "availability", "rating", "author", "tags",
    "description", "scraped_at",
]


def write_csv(records: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=CSV_COLUMNS, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(records)
    logger.info("CSV written to %s (%d records).", path, len(records))


def write_summary(summary: dict, path: Path) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)
    logger.info("Summary written to %s.", path)



def run_pipeline() -> None:
    pipeline_start = time.perf_counter()
    logger.info("=" * 60)
    logger.info("Pipeline started at %s",
                datetime.now(timezone.utc).isoformat())
    logger.info("=" * 60)

    summary: dict = {
        "pipeline_started_at": datetime.now(timezone.utc).isoformat(),
        "sources": {},
        "totals": {},
        "pipeline_finished_at": None,
        "execution_time_seconds": None,
    }

    logger.info("STEP 1 – Scraping …")

    books_raw: list[dict] = []
    quotes_raw: list[dict] = []

    try:
        books_raw = scrape_books()
        logger.info("Books raw records: %d", len(books_raw))
    except Exception as exc:
        logger.error("Books scraper failed: %s", exc, exc_info=True)

    try:
        quotes_raw = scrape_quotes()
        logger.info("Quotes raw records: %d", len(quotes_raw))
    except Exception as exc:
        logger.error("Quotes scraper failed: %s", exc, exc_info=True)

    all_raw = books_raw + quotes_raw
    logger.info("Total raw records: %d", len(all_raw))

    summary["sources"]["books_to_scrape"] = {
        "raw_records_collected": len(books_raw)
    }
    summary["sources"]["quotes_to_scrape"] = {
        "raw_records_collected": len(quotes_raw)
    }

    logger.info("STEP 2 – Cleaning …")
    cleaned = clean_records(all_raw)
    logger.info("Records after cleaning: %d", len(cleaned))

    books_cleaned  = sum(1 for r in cleaned if r.get("source") == "Books to Scrape")
    quotes_cleaned = sum(1 for r in cleaned if r.get("source") == "Quotes to Scrape")
    summary["sources"]["books_to_scrape"]["records_after_cleaning"] = books_cleaned
    summary["sources"]["quotes_to_scrape"]["records_after_cleaning"] = quotes_cleaned

    logger.info("STEP 3 – Validating …")
    valid, rejected = validate_records(cleaned)
    logger.info("Valid: %d  Rejected: %d", len(valid), len(rejected))

    books_rejected  = sum(1 for r in rejected if r.get("source") == "Books to Scrape")
    quotes_rejected = sum(1 for r in rejected if r.get("source") == "Quotes to Scrape")
    summary["sources"]["books_to_scrape"]["records_rejected_validation"] = books_rejected
    summary["sources"]["quotes_to_scrape"]["records_rejected_validation"] = quotes_rejected

    logger.info("STEP 4 – Deduplicating …")
    unique, duplicates, dup_count = deduplicate_records(valid)
    logger.info("Unique: %d  Duplicates removed: %d", len(unique), dup_count)

    logger.info("STEP 5 – Writing outputs …")

    final_records = [
        {k: v for k, v in rec.items() if not k.startswith("_")}
        for rec in unique
    ]

    csv_path     = OUTPUT_DIR / "final_dataset.csv"
    summary_path = OUTPUT_DIR / "summary_report.json"

    write_csv(final_records, csv_path)

    pipeline_end  = time.perf_counter()
    elapsed       = round(pipeline_end - pipeline_start, 2)

    summary["totals"] = {
        "total_raw_records":          len(all_raw),
        "total_after_cleaning":       len(cleaned),
        "total_rejected_validation":  len(rejected),
        "total_duplicates_removed":   dup_count,
        "total_final_records":        len(final_records),
    }
    summary["pipeline_finished_at"]   = datetime.now(timezone.utc).isoformat()
    summary["execution_time_seconds"] = elapsed

    write_summary(summary, summary_path)

    logger.info("=" * 60)
    logger.info("Pipeline complete in %.2f s.", elapsed)
    logger.info("Final records:        %d", len(final_records))
    logger.info("Duplicates removed:   %d", dup_count)
    logger.info("Rejected (invalid):   %d", len(rejected))
    logger.info("Output CSV:           %s", csv_path)
    logger.info("Summary report:       %s", summary_path)
    logger.info("Log file:             %s", LOG_FILE)
    logger.info("=" * 60)


if __name__ == "__main__":
    run_pipeline()
