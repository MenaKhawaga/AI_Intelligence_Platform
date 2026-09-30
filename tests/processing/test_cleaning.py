"""Tests for app.processing.cleaning."""

from __future__ import annotations

from app.processing.cleaning import clean_items, is_valid_url, strip_boilerplate, strip_html
from app.processing.normalization import ProcessedItem


def _item(**overrides) -> ProcessedItem:
    defaults = dict(
        source_type="rss",
        source="Some Feed",
        title="A valid title",
        url="https://example.com/a",
        summary="",
        raw_text="",
        score=0.0,
    )
    defaults.update(overrides)
    return ProcessedItem(**defaults)


def test_strip_html_removes_tags():
    # strip_html inserts a separating space at each tag boundary; the extra
    # whitespace this can leave between adjacent tags (e.g. "Hello  world")
    # is collapsed downstream by normalize_whitespace, not by strip_html
    # itself -- clean_text() (tested below) is the one that guarantees
    # single-spaced output.
    assert strip_html("<p>Hello <b>world</b></p>").split() == ["Hello", "world"]


def test_strip_html_leaves_plain_text_untouched():
    assert strip_html("no tags here") == "no tags here"


def test_strip_html_empty():
    assert strip_html("") == ""
    assert strip_html(None) == ""


def test_strip_boilerplate_removes_trailing_phrases():
    assert strip_boilerplate("Big AI news happened. Read more") == "Big AI news happened."
    assert (
        strip_boilerplate("The post AI Weekly appeared first on Blog.")
        == ""
    )


def test_is_valid_url():
    assert is_valid_url("https://example.com/a") is True
    assert is_valid_url("http://example.com") is True
    assert is_valid_url("not a url") is False
    assert is_valid_url("ftp://example.com/a") is False
    assert is_valid_url("") is False


def test_clean_items_strips_html_and_boilerplate_from_text_fields():
    item = _item(summary="<p>Big news. <b>Read more</b></p>", raw_text="<div>Body text</div>")
    [cleaned] = clean_items([item])
    assert cleaned.summary == "Big news."
    assert cleaned.raw_text == "Body text"


def test_clean_items_drops_items_with_empty_title():
    item = _item(title="")
    assert clean_items([item]) == []


def test_clean_items_drops_items_with_short_title():
    item = _item(title="Hi")
    assert clean_items([item]) == []


def test_clean_items_drops_items_with_invalid_url():
    item = _item(url="not-a-url")
    assert clean_items([item]) == []


def test_clean_items_keeps_valid_items():
    item = _item()
    result = clean_items([item])
    assert len(result) == 1
