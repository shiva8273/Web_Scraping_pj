import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from processing.validation import validate_record, validate_records


def _good_book():
    return {
        "source":        "Books to Scrape",
        "source_url":    "https://books.toscrape.com/catalogue/a-book/",
        "name_or_title": "A Good Book",
        "price":         9.99,
        "availability":  "In stock",
        "rating":        3,
        "author":        None,
        "tags":          None,
        "category":      "Mystery",
        "description":   None,
        "scraped_at":    "2026-01-01T00:00:00+00:00",
    }


def _good_quote():
    return {
        "source":        "Quotes to Scrape",
        "source_url":    "https://quotes.toscrape.com/author/albert-einstein/",
        "name_or_title": "\u201cLife is beautiful.\u201d",
        "price":         None,
        "availability":  None,
        "rating":        None,
        "author":        "Albert Einstein",
        "tags":          "life, love",
        "category":      None,
        "description":   None,
        "scraped_at":    "2026-01-01T00:00:00+00:00",
    }


class TestValidateRecord:
    def test_valid_book(self):
        ok, reasons = validate_record(_good_book())
        assert ok is True
        assert reasons == []

    def test_valid_quote(self):
        ok, reasons = validate_record(_good_quote())
        assert ok is True
        assert reasons == []

    def test_missing_source(self):
        rec = _good_book()
        rec["source"] = None
        ok, reasons = validate_record(rec)
        assert ok is False
        assert any("source" in r for r in reasons)

    def test_unknown_source(self):
        rec = _good_book()
        rec["source"] = "Unknown Site"
        ok, reasons = validate_record(rec)
        assert ok is False
        assert any("unrecognised source" in r for r in reasons)

    def test_missing_url(self):
        rec = _good_book()
        rec["source_url"] = None
        ok, reasons = validate_record(rec)
        assert ok is False
        assert any("source_url" in r for r in reasons)

    def test_invalid_url_scheme(self):
        rec = _good_book()
        rec["source_url"] = "ftp://books.toscrape.com/catalogue/a-book/"
        ok, reasons = validate_record(rec)
        assert ok is False
        assert any("source_url" in r for r in reasons)

    def test_missing_title(self):
        rec = _good_book()
        rec["name_or_title"] = None
        ok, reasons = validate_record(rec)
        assert ok is False
        assert any("name_or_title" in r for r in reasons)

    def test_non_numeric_price(self):
        rec = _good_book()
        rec["price"] = "not_a_number"
        ok, reasons = validate_record(rec)
        assert ok is False
        assert any("price" in r for r in reasons)

    def test_none_price_is_ok(self):
        rec = _good_book()
        rec["price"] = None
        ok, reasons = validate_record(rec)
        assert ok is True

    def test_rating_out_of_range(self):
        rec = _good_book()
        rec["rating"] = 6
        ok, reasons = validate_record(rec)
        assert ok is False
        assert any("rating" in r for r in reasons)

    def test_none_rating_is_ok(self):
        rec = _good_quote()
        ok, reasons = validate_record(rec)
        assert ok is True  


class TestValidateRecords:
    def test_splits_valid_and_invalid(self):
        bad = _good_book()
        bad["source"] = None
        valid, rejected = validate_records([_good_book(), _good_quote(), bad])
        assert len(valid) == 2
        assert len(rejected) == 1
        assert "_validation_errors" in rejected[0]
