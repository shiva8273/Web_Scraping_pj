import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from processing.deduplication import deduplicate_records, _normalise, _make_key


def _rec(source="Books to Scrape", title="A Book"):
    return {
        "source":        source,
        "name_or_title": title,
        "source_url":    "https://books.toscrape.com/catalogue/a-book/",
    }


class TestNormalise:
    def test_lowercases(self):
        assert _normalise("HELLO") == "hello"

    def test_strips_whitespace(self):
        assert _normalise("  hello  ") == "hello"

    def test_collapses_spaces(self):
        assert _normalise("hello   world") == "hello world"

    def test_none_returns_empty(self):
        assert _normalise(None) == ""


class TestMakeKey:
    def test_basic_key(self):
        key = _make_key(_rec("Books to Scrape", "A Book"))
        assert key == ("books to scrape", "a book")

    def test_keys_equal_despite_casing(self):
        k1 = _make_key(_rec("Books to Scrape", "A Book"))
        k2 = _make_key(_rec("BOOKS TO SCRAPE", "A BOOK"))
        assert k1 == k2


class TestDeduplicateRecords:
    def test_no_duplicates(self):
        records = [_rec(title="Book A"), _rec(title="Book B")]
        unique, dups, count = deduplicate_records(records)
        assert len(unique) == 2
        assert count == 0

    def test_exact_duplicate(self):
        records = [_rec(title="Book A"), _rec(title="Book A")]
        unique, dups, count = deduplicate_records(records)
        assert len(unique) == 1
        assert count == 1
        assert dups[0]["_is_duplicate"] is True

    def test_case_insensitive_duplicate(self):
        records = [_rec(title="A Great Book"), _rec(title="a great book")]
        unique, dups, count = deduplicate_records(records)
        assert len(unique) == 1
        assert count == 1

    def test_whitespace_duplicate(self):
        records = [_rec(title="A Book"), _rec(title="  A Book  ")]
        unique, dups, count = deduplicate_records(records)
        assert len(unique) == 1
        assert count == 1

    def test_same_title_different_sources_not_dup(self):
        r1 = _rec(source="Books to Scrape",  title="Life")
        r2 = _rec(source="Quotes to Scrape", title="Life")
        unique, dups, count = deduplicate_records([r1, r2])
        assert len(unique) == 2
        assert count == 0

    def test_first_occurrence_kept(self):
        r1 = _rec(title="A Book")
        r2 = _rec(title="A Book")
        r2["source_url"] = "https://different.url/"
        unique, dups, count = deduplicate_records([r1, r2])
        assert unique[0]["source_url"] == r1["source_url"]

    def test_unique_records_flagged_false(self):
        records = [_rec(title="Book A")]
        unique, _, _ = deduplicate_records(records)
        assert unique[0]["_is_duplicate"] is False

    def test_empty_input(self):
        unique, dups, count = deduplicate_records([])
        assert unique == []
        assert count == 0
