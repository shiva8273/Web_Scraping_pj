import logging
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL      = "https://quotes.toscrape.com/"
REQUEST_DELAY = 1.0
MAX_RETRIES   = 3
RETRY_BACKOFF = 2.0



def _get_page(session: requests.Session, url: str) -> BeautifulSoup | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except requests.exceptions.HTTPError as exc:
            logger.warning("HTTP %s for %s (attempt %d/%d)",
                           exc.response.status_code, url, attempt, MAX_RETRIES)
            if exc.response.status_code in (404, 410):
                return None
        except requests.exceptions.ConnectionError:
            logger.warning("Connection error for %s (attempt %d/%d)",
                           url, attempt, MAX_RETRIES)
        except requests.exceptions.Timeout:
            logger.warning("Timeout for %s (attempt %d/%d)",
                           url, attempt, MAX_RETRIES)
        except requests.exceptions.RequestException as exc:
            logger.warning("Request error for %s: %s (attempt %d/%d)",
                           url, exc, attempt, MAX_RETRIES)

        if attempt < MAX_RETRIES:
            sleep_time = RETRY_BACKOFF * (2 ** (attempt - 1))
            logger.debug("Retrying in %.1f s …", sleep_time)
            time.sleep(sleep_time)

    logger.error("Giving up on %s after %d attempts.", url, MAX_RETRIES)
    return None


def _parse_quote_div(div, scraped_at: str) -> dict:
    record: dict = {
        "source":        "Quotes to Scrape",
        "source_url":    BASE_URL,
        "name_or_title": None,
        "category":      None,
        "price":         None,
        "availability":  None,
        "rating":        None,
        "author":        None,
        "tags":          None,
        "description":   None,
        "scraped_at":    scraped_at,
    }

    span_text = div.find("span", class_="text")
    if span_text:
        record["name_or_title"] = span_text.get_text(strip=True)

    small_author = div.find("small", class_="author")
    if small_author:
        record["author"] = small_author.get_text(strip=True)

    a_about = div.select_one("span > a[href]")
    if a_about:
        record["source_url"] = urljoin(BASE_URL, a_about["href"])

    tags_div = div.find("div", class_="tags")
    if tags_div:
        tag_texts = [
            a.get_text(strip=True)
            for a in tags_div.find_all("a", class_="tag")
        ]
        record["tags"] = ", ".join(tag_texts) if tag_texts else None

    return record


def _scrape_page(session: requests.Session, url: str,
                 scraped_at: str) -> tuple[list[dict], str | None]:

    soup = _get_page(session, url)
    if soup is None:
        return [], None

    records = []
    for div in soup.select("div.quote"):
        try:
            rec = _parse_quote_div(div, scraped_at)
            records.append(rec)
        except Exception as exc:
            logger.warning("Failed parsing quote on %s: %s", url, exc)

    next_btn = soup.select_one("li.next > a")
    next_url = None
    if next_btn:
        href = next_btn.get("href", "")
        next_url = urljoin(url, href)

    return records, next_url



def scrape_quotes() -> list[dict]:

    scraped_at = datetime.now(timezone.utc).isoformat()
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; scraping-assignment/1.0)"
    })

    logger.info("[Quotes] Starting scrape …")
    all_records: list[dict] = []
    current_url: str | None = BASE_URL
    page_num = 0

    while current_url:
        page_num += 1
        logger.info("[Quotes] Page %d: %s", page_num, current_url)
        try:
            records, next_url = _scrape_page(session, current_url, scraped_at)
            all_records.extend(records)
            logger.debug("[Quotes] %d records so far.", len(all_records))
            current_url = next_url
            if current_url:
                time.sleep(REQUEST_DELAY)
        except Exception as exc:
            logger.error("[Quotes] Unexpected error on page %d (%s): %s",
                         page_num, current_url, exc, exc_info=True)
            break

    logger.info("[Quotes] Finished. %d raw records collected.", len(all_records))
    return all_records
