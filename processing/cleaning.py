import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def clean_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text if text else None


def normalize_text_lower(value) -> str | None:
    cleaned = clean_text(value)
    return cleaned.lower() if cleaned is not None else None


_PRICE_RE = re.compile(r"[\d]+\.[\d]+|[\d]+")


def clean_price(value) -> float | None:
    if value is None:
        return None
    text = str(value)
    match = _PRICE_RE.search(text)
    if match:
        try:
            return float(match.group())
        except ValueError:
            pass
    logger.debug("Could not parse price from %r", value)
    return None



def clean_rating(value) -> int | None:
    WORD_TO_NUM = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    }
    if value is None:
        return None
    if isinstance(value, int):
        return value if 1 <= value <= 5 else None
    s = str(value).strip().lower()
    if s in WORD_TO_NUM:
        return WORD_TO_NUM[s]
    try:
        num = int(s)
        return num if 1 <= num <= 5 else None
    except ValueError:
        return None



def clean_url(value) -> str | None:
    
    if value is None:
        return None
    text = str(value).strip()
    try:
        parsed = urlparse(text)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return text
    except Exception:
        pass
    logger.debug("Invalid URL discarded: %r", value)
    return None



def clean_availability(value) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    lower = text.lower()
    if "in stock" in lower:
        return "In stock"
    if "out of stock" in lower:
        return "Out of stock"
    return text      



def clean_tags(value) -> str | None:

    if value is None:
        return None
    raw = str(value)
    tags = [t.strip().lower() for t in raw.split(",") if t.strip()]
    unique = sorted(set(tags))
    return ", ".join(unique) if unique else None



SCHEMA_FIELDS = [
    "source", "source_url", "name_or_title", "category",
    "price", "availability", "rating", "author", "tags",
    "description", "scraped_at",
]


def clean_record(record: dict) -> dict:

    cleaned = {}

    cleaned["source"]        = clean_text(record.get("source"))
    cleaned["source_url"]    = clean_url(record.get("source_url"))
    cleaned["name_or_title"] = clean_text(record.get("name_or_title"))
    cleaned["category"]      = clean_text(record.get("category"))
    cleaned["price"]         = clean_price(record.get("price"))
    cleaned["availability"]  = clean_availability(record.get("availability"))
    cleaned["rating"]        = clean_rating(record.get("rating"))
    cleaned["author"]        = clean_text(record.get("author"))
    cleaned["tags"]          = clean_tags(record.get("tags"))
    cleaned["description"]   = clean_text(record.get("description"))
    cleaned["scraped_at"]    = clean_text(record.get("scraped_at"))

    return cleaned


def clean_records(records: list[dict]) -> list[dict]:
    cleaned = []
    for rec in records:
        try:
            cleaned.append(clean_record(rec))
        except Exception as exc:
            logger.warning("Skipping record during cleaning due to error: %s", exc)
    return cleaned
