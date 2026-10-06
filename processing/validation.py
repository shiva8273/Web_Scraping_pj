
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

KNOWN_SOURCES = {"Books to Scrape", "Quotes to Scrape"}


def validate_record(record: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    source = record.get("source")
    if not source:
        reasons.append("missing source")
    elif source not in KNOWN_SOURCES:
        reasons.append(f"unrecognised source: {source!r}")

    url = record.get("source_url")
    if not url:
        reasons.append("missing source_url")
    else:
        try:
            parsed = urlparse(str(url))
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                reasons.append(f"invalid source_url: {url!r}")
        except Exception:
            reasons.append(f"unparseable source_url: {url!r}")

    if not record.get("name_or_title"):
        reasons.append("missing name_or_title")

    price = record.get("price")
    if price is not None:
        if not isinstance(price, (int, float)):
            reasons.append(f"price is not numeric: {price!r}")

    rating = record.get("rating")
    if rating is not None:
        if not isinstance(rating, int) or not (1 <= rating <= 5):
            reasons.append(f"rating out of range: {rating!r}")

    valid = len(reasons) == 0
    return valid, reasons


def validate_records(records: list[dict]) -> tuple[list[dict], list[dict]]:
   
    valid: list[dict] = []
    rejected: list[dict] = []

    for rec in records:
        ok, reasons = validate_record(rec)
        if ok:
            valid.append(rec)
        else:
            rejected_rec = dict(rec)
            rejected_rec["_validation_errors"] = reasons
            rejected.append(rejected_rec)
            logger.debug("Record rejected (%s): %s",
                         rec.get("name_or_title", "<no title>"), reasons)

    logger.info("Validation complete – valid: %d  rejected: %d",
                len(valid), len(rejected))
    return valid, rejected
