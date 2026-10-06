
import logging
import re

logger = logging.getLogger(__name__)


def _normalise(text) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text).strip().lower())


def _make_key(record: dict) -> tuple[str, str]:
    return (
        _normalise(record.get("source")),
        _normalise(record.get("name_or_title")),
    )


def deduplicate_records(
    records: list[dict],
) -> tuple[list[dict], list[dict], int]:
    seen: dict[tuple, int] = {}  
    unique:     list[dict] = []
    duplicates: list[dict] = []

    for idx, rec in enumerate(records):
        key = _make_key(rec)
        if key in seen:
            dup = dict(rec)
            dup["_is_duplicate"] = True
            duplicates.append(dup)
            logger.debug("Duplicate detected (key=%s) at record index %d "
                         "(first seen at index %d)", key, idx, seen[key])
        else:
            seen[key] = idx
            tagged = dict(rec)
            tagged["_is_duplicate"] = False
            unique.append(tagged)

    count = len(duplicates)
    logger.info("Deduplication complete – unique: %d  duplicates removed: %d",
                len(unique), count)
    return unique, duplicates, count
