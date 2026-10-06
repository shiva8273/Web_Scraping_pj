import logging
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://books.toscrape.com/"
CATALOGUE_BASE = "https://books.toscrape.com/catalogue/"

WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
}

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


def _parse_rating(word: str) -> int | None:
    return WORD_TO_NUM.get(word.strip().lower())


def _resolve_book_url(href: str) -> str:
  
    clean = href.lstrip("./")
    if clean.startswith("catalogue/"):
        return urljoin(BASE_URL, clean)
    return urljoin(CATALOGUE_BASE, clean)


def _parse_book_card(article, category: str, scraped_at: str) -> dict:
    record: dict = {
        "source":        "Books to Scrape",
        "source_url":    None,
        "name_or_title": None,
        "category":      category,
        "price":         None,
        "availability":  None,
        "rating":        None,
        "author":        None,
        "tags":          None,
        "description":   None,
        "scraped_at":    scraped_at,
    }

    h3 = article.find("h3")
    if h3:
        a_tag = h3.find("a")
        if a_tag:
            record["name_or_title"] = (
                a_tag.get("title") or a_tag.get_text(strip=True) or None
            )
            href = a_tag.get("href", "")
            record["source_url"] = _resolve_book_url(href)

    p_price = article.find("p", class_="price_color")
    if p_price:
        record["price"] = p_price.get_text(strip=True)

    p_avail = article.find("p", class_="availability")
    if p_avail:
        record["availability"] = p_avail.get_text(strip=True)

    p_star = article.find("p", class_="star-rating")
    if p_star:
        classes = p_star.get("class", [])
        for cls in classes:
            if cls.lower() in WORD_TO_NUM:
                record["rating"] = _parse_rating(cls)
                break

    return record


def _scrape_category_page(session, url: str, category: str,
                           scraped_at: str) -> tuple[list[dict], str | None]:

    soup = _get_page(session, url)
    if soup is None:
        return [], None

    records = []
    for article in soup.select("article.product_pod"):
        try:
            rec = _parse_book_card(article, category, scraped_at)
            records.append(rec)
        except Exception as exc:
            logger.warning("Failed parsing book card on %s: %s", url, exc)

    next_btn = soup.select_one("li.next > a")
    next_url = None
    if next_btn:
        href = next_btn.get("href", "")
        next_url = urljoin(url, href)

    return records, next_url


def _scrape_category(session: requests.Session, cat_url: str,
                      cat_name: str, scraped_at: str) -> list[dict]:
    all_records: list[dict] = []
    current_url: str | None = cat_url
    page_num = 0

    while current_url:
        page_num += 1
        logger.info("[Books] Category '%s' – page %d: %s",
                    cat_name, page_num, current_url)
        records, next_url = _scrape_category_page(
            session, current_url, cat_name, scraped_at
        )
        all_records.extend(records)
        logger.debug("[Books] %d records so far in '%s'", len(all_records), cat_name)
        current_url = next_url
        if current_url:
            time.sleep(REQUEST_DELAY)

    return all_records


def _get_categories(session: requests.Session) -> list[tuple[str, str]]:
    soup = _get_page(session, BASE_URL)
    if soup is None:
        logger.error("[Books] Cannot load home page; returning empty category list.")
        return []

    cats: list[tuple[str, str]] = []
    nav = soup.select_one("ul.nav-list > li > ul")
    if nav:
        for li in nav.find_all("li"):
            a = li.find("a")
            if a:
                name = a.get_text(strip=True)
                href = a.get("href", "")
                url  = urljoin(BASE_URL, href)
                cats.append((name, url))
    return cats



def scrape_books() -> list[dict]:

    scraped_at = datetime.now(timezone.utc).isoformat()
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; scraping-assignment/1.0)"
    })

    logger.info("[Books] Starting scrape …")
    categories = _get_categories(session)
    logger.info("[Books] Found %d categories.", len(categories))

    all_records: list[dict] = []
    for cat_name, cat_url in categories:
        try:
            records = _scrape_category(session, cat_url, cat_name, scraped_at)
            all_records.extend(records)
            time.sleep(REQUEST_DELAY)
        except Exception as exc:
            logger.error("[Books] Unexpected error in category '%s': %s",
                         cat_name, exc, exc_info=True)

    logger.info("[Books] Finished. %d raw records collected.", len(all_records))
    return all_records
