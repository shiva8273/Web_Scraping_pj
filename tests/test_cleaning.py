import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from processing.cleaning import (
    clean_text, clean_price, clean_rating, clean_url,
    clean_availability, clean_tags, clean_record,
)



class TestCleanText:
    def test_strips_whitespace(self):
        assert clean_text("  hello world  ") == "hello world"

    def test_collapses_internal_spaces(self):
        assert clean_text("hello   world") == "hello world"

    def test_returns_none_for_blank(self):
        assert clean_text("   ") is None

    def test_returns_none_for_none(self):
        assert clean_text(None) is None

    def test_converts_non_string(self):
        assert clean_text(42) == "42"


class TestCleanPrice:
    def test_strips_currency_symbol(self):
        assert clean_price("£12.99") == 12.99

    def test_strips_garbled_currency(self):
        assert clean_price("Â£12.99") == 12.99

    def test_integer_price(self):
        assert clean_price("5") == 5.0

    def test_none_input(self):
        assert clean_price(None) is None

    def test_no_number_returns_none(self):
        assert clean_price("N/A") is None

    def test_already_float(self):
        assert clean_price("19.99") == 19.99



class TestCleanRating:
    def test_integer_in_range(self):
        assert clean_rating(3) == 3

    def test_word_rating(self):
        assert clean_rating("Three") == 3

    def test_word_rating_lowercase(self):
        assert clean_rating("five") == 5

    def test_string_digit(self):
        assert clean_rating("4") == 4

    def test_none_input(self):
        assert clean_rating(None) is None

    def test_out_of_range_returns_none(self):
        assert clean_rating(6) is None
        assert clean_rating(0) is None

    def test_unrecognised_word(self):
        assert clean_rating("excellent") is None



class TestCleanUrl:
    def test_valid_http(self):
        assert clean_url("http://example.com") == "http://example.com"

    def test_valid_https(self):
        assert clean_url("https://books.toscrape.com/catalogue/a-book/") == \
               "https://books.toscrape.com/catalogue/a-book/"

    def test_no_scheme_returns_none(self):
        assert clean_url("www.example.com") is None

    def test_none_returns_none(self):
        assert clean_url(None) is None

    def test_empty_string_returns_none(self):
        assert clean_url("") is None


class TestCleanAvailability:
    def test_in_stock(self):
        assert clean_availability("  In stock  ") == "In stock"

    def test_out_of_stock(self):
        assert clean_availability("Out of stock") == "Out of stock"

    def test_case_insensitive_in(self):
        assert clean_availability("IN STOCK") == "In stock"

    def test_none_returns_none(self):
        assert clean_availability(None) is None


class TestCleanTags:
    def test_normalises_and_sorts(self):
        assert clean_tags("Python, Data, python") == "data, python"

    def test_strips_individual_tags(self):
        assert clean_tags("  love , life  ") == "life, love"

    def test_none_returns_none(self):
        assert clean_tags(None) is None

    def test_empty_string_returns_none(self):
        assert clean_tags("") is None


class TestCleanRecord:
    def test_all_fields_present(self):
        raw = {
            "source":        "Books to Scrape",
            "source_url":    "https://books.toscrape.com/catalogue/a-book/",
            "name_or_title": "  A Book Title  ",
            "price":         "£9.99",
            "rating":        "Three",
            "availability":  " In stock ",
            "tags":          "fiction, Drama",
            "author":        None,
            "category":      "Mystery",
            "description":   None,
            "scraped_at":    "2026-01-01T00:00:00+00:00",
        }
        result = clean_record(raw)
        assert result["name_or_title"] == "A Book Title"
        assert result["price"] == 9.99
        assert result["rating"] == 3
        assert result["availability"] == "In stock"
        assert result["tags"] == "drama, fiction"
        assert result["author"] is None

    def test_returns_all_schema_keys(self):
        result = clean_record({})
        expected_keys = {
            "source", "source_url", "name_or_title", "category",
            "price", "availability", "rating", "author", "tags",
            "description", "scraped_at",
        }
        assert set(result.keys()) == expected_keys
