"""Tests for the single localization resource (LANG-3, LANG-4)."""

from __future__ import annotations

import pytest

from src.features.web import locale

TURKISH_LETTERS = ("\u00e7", "\u011f", "\u0131", "\u0130", "\u00f6",
                   "\u015f", "\u00fc")


def test_labels_are_ascii_and_never_empty():
    labels = locale.labels()
    assert labels
    for key, value in labels.items():
        assert value.strip(), key
        assert value.isascii(), key
        for letter in TURKISH_LETTERS:
            assert letter not in value, key


@pytest.mark.parametrize("key", ["app.title", "price.close", "cot.week"])
def test_text_returns_the_english_value(key):
    assert locale.text(key) == locale.labels()[key]


def test_an_unknown_locale_falls_back_to_english():
    assert locale.labels("tr") == locale.labels("en")


def test_text_reports_an_unknown_key_instead_of_failing():
    assert locale.text("nope") == "nope"


def test_labels_are_a_copy_so_callers_cannot_change_the_resource():
    first = locale.labels()
    first["app.title"] = "changed"
    assert locale.labels()["app.title"] == "Gold Market Data Dashboard"
